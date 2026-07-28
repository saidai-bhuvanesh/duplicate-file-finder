"""
FastAPI dependency injection providers.

Provides typed, reusable dependencies for:
- Database sessions
- Cache clients
- Repository instances
- Service instances
"""

from __future__ import annotations

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.infrastructure.cache.redis_client import RedisClient
from app.infrastructure.database.connection import AsyncSessionFactory


# ── Settings ──────────────────────────────────────────────────────────────────


def settings_dependency() -> Settings:
    """Provide application settings."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(settings_dependency)]


# ── Database ──────────────────────────────────────────────────────────────────


async def get_db_session() -> AsyncGenerator[AsyncSession | None, None]:
    """
    Provide an async database session with automatic commit/rollback.
    Yields None if database is not reachable.
    """
    try:
        async with AsyncSessionFactory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    except Exception:
        yield None


DatabaseSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# ── Cache ─────────────────────────────────────────────────────────────────────


async def get_redis_client() -> AsyncGenerator[RedisClient, None]:
    """Provide a Redis client from the connection pool."""
    client = RedisClient.get_instance()
    try:
        yield client
    finally:
        pass  # Connection returned to pool automatically


RedisClientDep = Annotated[RedisClient, Depends(get_redis_client)]


# ── Repository Dependencies ───────────────────────────────────────────────────
# These are imported lazily to avoid circular imports at module load time.
# They are constructed in the route handlers that need them.


def get_document_repository(
    session: DatabaseSessionDep,
) -> "DocumentRepository":  # noqa: F821
    """Provide a document repository backed by the current DB session."""
    from app.infrastructure.repositories.document_repository import (
        PostgresDocumentRepository,
    )

    return PostgresDocumentRepository(session)


def get_chunk_repository(
    session: DatabaseSessionDep,
) -> "ChunkRepository":  # noqa: F821
    """Provide a chunk repository backed by the current DB session."""
    from app.infrastructure.repositories.chunk_repository import (
        PostgresChunkRepository,
    )

    return PostgresChunkRepository(session)


# ── Service Dependencies ──────────────────────────────────────────────────────


def get_document_service(
    session: DatabaseSessionDep,
    redis: RedisClientDep,
    settings: SettingsDep,
) -> "DocumentService":  # noqa: F821
    """Provide the document service with all its dependencies."""
    from app.application.services.document_service import DocumentService
    from app.infrastructure.repositories.chunk_repository import PostgresChunkRepository
    from app.infrastructure.repositories.document_repository import (
        PostgresDocumentRepository,
    )

    return DocumentService(
        document_repo=PostgresDocumentRepository(session),
        chunk_repo=PostgresChunkRepository(session),
        cache=redis,
        settings=settings,
    )


DocumentServiceDep = Annotated["DocumentService", Depends(get_document_service)]
