"""
SQLAlchemy async database connection management.

Provides:
- Async engine with connection pooling
- Session factory
- Database health check
- Lifespan management for FastAPI
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__, component="database")

# Singleton engine instance
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def get_engine() -> AsyncEngine:
    """Return the singleton async engine, creating it if necessary."""
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the singleton session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _session_factory


def AsyncSessionFactory() -> AsyncSession:
    """
    Create a new async session from the session factory.

    Intended for use as an async context manager:

        async with AsyncSessionFactory() as session:
            result = await session.execute(...)
    """
    factory = get_session_factory()
    return factory()


def _create_engine(use_null_pool: bool = False) -> AsyncEngine:
    """
    Create the async SQLAlchemy engine.

    Args:
        use_null_pool: If True, uses NullPool (for tests).
    """
    settings = get_settings()
    db = settings.database

    engine_kwargs: dict = {
        "echo": db.echo,
        "future": True,
    }

    if use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = db.pool_size
        engine_kwargs["max_overflow"] = db.max_overflow
        engine_kwargs["pool_pre_ping"] = True
        engine_kwargs["pool_recycle"] = 3600

    logger.info(
        "creating_database_engine",
        host=db.host,
        port=db.port,
        database=db.db,
        pool_size=db.pool_size,
    )

    return create_async_engine(db.async_url, **engine_kwargs)


def create_test_engine() -> AsyncEngine:
    """Create a NullPool engine for tests (no connection pooling)."""
    return _create_engine(use_null_pool=True)


async def create_all_tables() -> None:
    """Create all tables defined in ORM models (for testing/dev)."""
    engine = get_engine()
    async with engine.begin() as conn:
        from app.infrastructure.database import models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_tables_created")


async def drop_all_tables() -> None:
    """Drop all tables (for testing cleanup)."""
    engine = get_engine()
    async with engine.begin() as conn:
        from app.infrastructure.database import models  # noqa: F401
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("database_tables_dropped")


async def check_database_health() -> bool:
    """
    Perform a lightweight health check against the database.

    Returns:
        True if database is reachable and responsive.
    """
    try:
        from sqlalchemy import text
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("database_health_check_failed", error=str(exc))
        return False


async def close_engine() -> None:
    """Dispose the engine and close all connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("database_engine_closed")
