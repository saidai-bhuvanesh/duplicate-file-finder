"""
Pytest configuration and shared fixtures.
"""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings


# ── Event Loop ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default asyncio event loop policy."""
    return asyncio.DefaultEventLoopPolicy()


# ── Settings Override ─────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Clear settings cache between tests."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_settings(monkeypatch):
    """Override settings for tests."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_DB", "enterpriseit_rag_test")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    get_settings.cache_clear()
    return get_settings()


# ── FastAPI Test Client ───────────────────────────────────────────────────────


@pytest.fixture
def app():
    """Create FastAPI test app."""
    from app.main import create_app
    return create_app()


@pytest.fixture
def client(app):
    """Sync test client (does not start lifespan)."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── Mock Repositories ─────────────────────────────────────────────────────────


@pytest.fixture
def mock_document_repo():
    """Mock DocumentRepository."""
    mock = AsyncMock()
    mock.create = AsyncMock()
    mock.get_by_id = AsyncMock(return_value=None)
    mock.get_by_content_hash = AsyncMock(return_value=None)
    mock.update = AsyncMock()
    mock.delete = AsyncMock(return_value=True)
    mock.list = AsyncMock(return_value=([], 0))
    mock.count = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_chunk_repo():
    """Mock ChunkRepository."""
    mock = AsyncMock()
    mock.create_many = AsyncMock(return_value=[])
    mock.get_by_id = AsyncMock(return_value=None)
    mock.get_by_document_id = AsyncMock(return_value=[])
    mock.delete_by_document_id = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_cache():
    """Mock RedisClient."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=False)
    mock.invalidate_prefix = AsyncMock(return_value=0)
    return mock
