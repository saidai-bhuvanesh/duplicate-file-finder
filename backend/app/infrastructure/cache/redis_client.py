"""
Redis cache client.

Provides async Redis operations with:
- Connection pool management
- JSON serialization/deserialization
- TTL-based key management
- Health check
"""

from __future__ import annotations

import json
from typing import Any, TypeVar

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.exceptions import CacheError
from app.core.logging import get_logger

logger = get_logger(__name__, component="cache")

T = TypeVar("T")

_instance: "RedisClient | None" = None


class RedisClient:
    """
    Async Redis client with connection pool.

    Uses singleton pattern — call RedisClient.get_instance() to get the shared client.
    """

    def __init__(self, pool: aioredis.ConnectionPool) -> None:
        self._pool = pool
        self._client = aioredis.Redis(connection_pool=pool)

    @classmethod
    def get_instance(cls) -> "RedisClient":
        """Return or create the singleton Redis client."""
        global _instance
        if _instance is None:
            _instance = cls._create()
        return _instance

    @classmethod
    def _create(cls) -> "RedisClient":
        """Create a new Redis client with connection pool."""
        settings = get_settings()
        redis_cfg = settings.redis

        pool = aioredis.ConnectionPool.from_url(
            redis_cfg.url,
            max_connections=redis_cfg.max_connections,
            decode_responses=False,  # We handle encoding ourselves
        )
        logger.info(
            "redis_client_created",
            host=redis_cfg.host,
            port=redis_cfg.port,
            db=redis_cfg.db,
        )
        return cls(pool)

    async def ping(self) -> bool:
        """Check Redis connectivity."""
        import os
        import asyncio

        if os.environ.get("SKIP_DB_PING"):
            return False
        try:
            result = await asyncio.wait_for(self._client.ping(), timeout=0.4)
            return bool(result)
        except Exception as exc:
            logger.warning("redis_health_check_failed", error=str(exc))
            return False

    async def get(self, key: str) -> Any | None:
        """Get a JSON-deserialized value from cache."""
        try:
            raw = await self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning("redis_json_decode_error", key=key, error=str(exc))
            return None
        except Exception as exc:
            raise CacheError(f"Redis GET failed for key '{key}': {exc}") from exc

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set a JSON-serialized value in cache with optional TTL."""
        try:
            settings = get_settings()
            effective_ttl = ttl or settings.redis.cache_ttl
            serialized = json.dumps(value, default=str)
            result = await self._client.setex(key, effective_ttl, serialized)
            return bool(result)
        except Exception as exc:
            raise CacheError(f"Redis SET failed for key '{key}': {exc}") from exc

    async def delete(self, *keys: str) -> int:
        """Delete one or more keys. Returns count deleted."""
        try:
            return await self._client.delete(*keys)
        except Exception as exc:
            raise CacheError(f"Redis DELETE failed: {exc}") from exc

    async def exists(self, key: str) -> bool:
        """Return True if key exists in cache."""
        try:
            return bool(await self._client.exists(key))
        except Exception as exc:
            raise CacheError(f"Redis EXISTS failed for key '{key}': {exc}") from exc

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiry on an existing key."""
        try:
            return bool(await self._client.expire(key, ttl))
        except Exception as exc:
            raise CacheError(f"Redis EXPIRE failed for key '{key}': {exc}") from exc

    async def get_or_set(
        self,
        key: str,
        factory: Any,
        ttl: int | None = None,
    ) -> Any:
        """
        Get value from cache, or compute and cache it.

        Args:
            key: Cache key.
            factory: Async callable that produces the value if not cached.
            ttl: Cache TTL in seconds.

        Returns:
            Cached or freshly computed value.
        """
        cached = await self.get(key)
        if cached is not None:
            logger.debug("cache_hit", key=key)
            return cached

        logger.debug("cache_miss", key=key)
        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value

    async def invalidate_prefix(self, prefix: str) -> int:
        """Delete all keys matching a prefix pattern."""
        try:
            keys = []
            async for key in self._client.scan_iter(f"{prefix}*"):
                keys.append(key)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as exc:
            raise CacheError(f"Redis prefix invalidation failed: {exc}") from exc

    async def get_info(self) -> dict[str, Any]:
        """Return Redis server info."""
        try:
            info = await self._client.info()
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_commands_processed": info.get("total_commands_processed"),
            }
        except Exception as exc:
            logger.error("redis_info_failed", error=str(exc))
            return {}

    async def close(self) -> None:
        """Close the connection pool."""
        await self._pool.disconnect()
        logger.info("redis_client_closed")

    # ── Cache Key Helpers ────────────────────────────────────────────────────

    @staticmethod
    def query_cache_key(query_text: str, strategy: str, filters: dict) -> str:
        """Generate a deterministic cache key for a query."""
        import hashlib
        payload = f"{query_text}|{strategy}|{sorted(filters.items())}"
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return f"rag:query:{digest}"

    @staticmethod
    def document_cache_key(document_id: str) -> str:
        return f"rag:doc:{document_id}"

    @staticmethod
    def embedding_cache_key(text_hash: str, model: str) -> str:
        return f"rag:emb:{model}:{text_hash}"
