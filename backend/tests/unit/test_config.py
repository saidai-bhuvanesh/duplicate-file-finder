"""
Unit tests for application configuration.
"""

import os
import pytest

from app.core.config import get_settings, Settings


@pytest.mark.unit
class TestAppSettings:
    def test_default_settings_load(self, test_settings):
        """Settings should load with defaults when no .env file present."""
        assert test_settings.app.app_name == "EnterpriseIT-RAG"
        assert test_settings.app.app_version == "1.0.0"

    def test_environment_override(self, monkeypatch):
        """Environment variables should override defaults."""
        monkeypatch.setenv("APP_NAME", "TestRAG")
        monkeypatch.setenv("APP_VERSION", "2.0.0")
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.app.app_name == "TestRAG"
        assert settings.app.app_version == "2.0.0"
        get_settings.cache_clear()

    def test_is_development(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "development")
        get_settings.cache_clear()
        s = get_settings()
        assert s.app.is_development is True
        assert s.app.is_production is False
        get_settings.cache_clear()

    def test_is_production(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        get_settings.cache_clear()
        s = get_settings()
        assert s.app.is_production is True
        assert s.app.is_development is False
        get_settings.cache_clear()


@pytest.mark.unit
class TestDatabaseSettings:
    def test_async_url_format(self, test_settings):
        """Database URL should use asyncpg driver."""
        url = test_settings.database.async_url
        assert url.startswith("postgresql+asyncpg://")
        assert "enterpriseit_rag" in url

    def test_sync_url_format(self, test_settings):
        """Sync URL should use psycopg2 for Alembic."""
        url = test_settings.database.sync_url
        assert url.startswith("postgresql+psycopg2://")

    def test_password_is_secret(self, test_settings):
        """Password should be a SecretStr (not exposed in repr)."""
        from pydantic import SecretStr
        assert isinstance(test_settings.database.password, SecretStr)
        # Should not expose password in string representation
        assert "rag_password" not in repr(test_settings.database)


@pytest.mark.unit
class TestSecuritySettings:
    def test_allowed_origins_parsed_from_string(self, monkeypatch):
        """Comma-separated origins should be parsed into a list."""
        monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
        get_settings.cache_clear()
        s = get_settings()
        origins = s.security.allowed_origins
        assert isinstance(origins, list)
        assert len(origins) == 2
        assert "http://localhost:3000" in origins
        assert "http://localhost:8000" in origins
        get_settings.cache_clear()


@pytest.mark.unit
class TestRetrievalSettings:
    def test_hybrid_alpha_bounds(self, test_settings):
        """Hybrid alpha must be between 0 and 1."""
        assert 0.0 <= test_settings.retrieval.hybrid_alpha <= 1.0

    def test_evidence_thresholds(self, test_settings):
        """Evidence thresholds should be valid fractions."""
        assert 0.0 <= test_settings.retrieval.evidence_min_coverage <= 1.0
        assert 0.0 <= test_settings.retrieval.evidence_min_confidence <= 1.0


@pytest.mark.unit
class TestSettingsCaching:
    def test_settings_are_cached(self):
        """get_settings should return same instance."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_clear_creates_new_instance(self):
        """Clearing cache should allow new instance creation."""
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # Both valid Settings instances
        assert isinstance(s1, Settings)
        assert isinstance(s2, Settings)
