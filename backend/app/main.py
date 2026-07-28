"""
FastAPI Application Entry Point.

Assembles the full FastAPI application with:
- Lifespan context manager (startup / shutdown)
- Middleware stack
- Exception handlers
- API routers
- OpenAPI metadata
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.middleware import configure_cors, register_exception_handlers, RequestLoggingMiddleware

logger = get_logger(__name__, component="app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager.

    Startup:  Initialize database, Redis, and load ML models.
    Shutdown: Gracefully close all connections.
    """
    settings = get_settings()

    # ── Startup ───────────────────────────────────────────────────────────────
    configure_logging(
        log_level=settings.app.app_log_level,
        is_production=settings.app.is_production,
    )
    logger.info(
        "application_starting",
        name=settings.app.app_name,
        version=settings.app.app_version,
        environment=settings.app.app_env,
    )

    # Initialize database engine
    from app.infrastructure.database.connection import get_engine, check_database_health
    get_engine()

    db_healthy = await check_database_health()
    if db_healthy:
        logger.info("database_connected")
    else:
        logger.warning("database_not_ready_at_startup")

    # Initialize Redis
    from app.infrastructure.cache.redis_client import RedisClient
    redis = RedisClient.get_instance()
    redis_healthy = await redis.ping()
    if redis_healthy:
        logger.info("redis_connected")
    else:
        logger.warning("redis_not_ready_at_startup")

    logger.info("application_ready")

    yield  # ── Application Running ────────────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("application_shutting_down")

    from app.infrastructure.database.connection import close_engine
    await close_engine()

    await redis.close()

    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI app."""
    settings = get_settings()

    app = FastAPI(
        title="EnterpriseIT-RAG API",
        description=(
            "Adaptive Multi-Agent Enterprise Knowledge Assistant for IT Teams.\n\n"
            "A production-grade RAG platform with:\n"
            "- Hybrid retrieval (BM25 + FAISS + CrossEncoder)\n"
            "- Multi-agent verification pipeline\n"
            "- Enterprise Knowledge Graph\n"
            "- Evidence Sufficiency Gate\n"
            "- Explainable retrieval\n"
        ),
        version=settings.app.app_version,
        docs_url="/docs" if not settings.app.is_production else None,
        redoc_url="/redoc" if not settings.app.is_production else None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={
            "name": "EnterpriseIT-RAG Team",
        },
        license_info={
            "name": "MIT",
        },
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    configure_cors(app)
    app.add_middleware(RequestLoggingMiddleware)

    # ── Exception Handlers ────────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── API Routers ───────────────────────────────────────────────────────────
    from app.api.v1.health import router as health_router
    from app.api.v1.documents import router as documents_router
    from app.api.v1.search import router as search_router
    from app.api.v1.ingestion import router as ingestion_router
    from app.api.v1.graph import router as graph_router
    from app.api.v1.evaluation import router as evaluation_router
    from app.api.v1.arie import router as arie_router

    # System routes (no version prefix for k8s probes)
    app.include_router(health_router)

    # Versioned API routes
    API_V1_PREFIX = "/api/v1"
    app.include_router(health_router, prefix=API_V1_PREFIX)
    app.include_router(documents_router, prefix=API_V1_PREFIX)
    app.include_router(search_router, prefix=API_V1_PREFIX)
    app.include_router(ingestion_router, prefix=API_V1_PREFIX)
    app.include_router(graph_router, prefix=API_V1_PREFIX)
    app.include_router(evaluation_router, prefix=API_V1_PREFIX)
    app.include_router(arie_router, prefix=API_V1_PREFIX)

    return app


# Application instance
app = create_app()


def run() -> None:
    """Entry point for the `enterpriseit-rag` CLI command."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app.app_host,
        port=settings.app.app_port,
        reload=settings.app.is_development,
        log_level=settings.app.app_log_level.lower(),
        access_log=False,  # Handled by our middleware
    )


if __name__ == "__main__":
    run()
