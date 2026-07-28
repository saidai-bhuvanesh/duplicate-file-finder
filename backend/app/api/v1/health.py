"""
Health, readiness, and version API endpoints.

These endpoints are used by:
- Kubernetes liveness probes (/health)
- Kubernetes readiness probes (/ready)
- CI/CD version verification (/version)
- Monitoring dashboards
"""

from __future__ import annotations

import platform
import time
from datetime import datetime

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.logging import get_logger
from app.infrastructure.cache.redis_client import RedisClient
from app.infrastructure.database.connection import check_database_health

router = APIRouter(tags=["System"])
logger = get_logger(__name__, component="health")

# Track startup time
_startup_time = time.time()


@router.get(
    "/health",
    summary="Liveness check",
    description="Returns 200 if the application process is alive.",
    response_model=dict,
)
async def health_check() -> dict:
    """
    Kubernetes liveness probe endpoint.

    Returns 200 if the application is running.
    Does NOT check dependencies (use /ready for that).
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(time.time() - _startup_time, 2),
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description="Returns 200 if all dependencies are available.",
    response_model=dict,
)
async def readiness_check() -> dict:
    """
    Kubernetes readiness probe endpoint.

    Checks PostgreSQL and Redis connectivity.
    Returns 503 if any critical dependency is unavailable.
    """
    from fastapi import HTTPException

    checks: dict[str, bool] = {}
    start = time.perf_counter()

    # Check PostgreSQL
    checks["postgresql"] = await check_database_health()

    # Check Redis
    redis = RedisClient.get_instance()
    checks["redis"] = await redis.ping()

    # All must pass for readiness
    all_healthy = all(checks.values())
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    response = {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
        "check_latency_ms": latency_ms,
    }

    if not all_healthy:
        logger.warning("readiness_check_failed", checks=checks)
        raise HTTPException(status_code=503, detail=response)

    return response


@router.get(
    "/version",
    summary="Version information",
    description="Returns application version and environment info.",
    response_model=dict,
)
async def version_info() -> dict:
    """Return application version, build info, and environment details."""
    settings = get_settings()
    return {
        "app_name": settings.app.app_name,
        "version": settings.app.app_version,
        "environment": settings.app.app_env,
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "build_time": datetime.utcnow().isoformat(),
    }
