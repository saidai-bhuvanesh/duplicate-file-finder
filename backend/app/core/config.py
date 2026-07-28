"""
Application configuration using Pydantic Settings.

All configuration is loaded from environment variables (or .env file).
This module is the single source of truth for all configuration values.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL database settings."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", env_file=".env", extra="ignore")

    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    db: str = Field(default="enterpriseit_rag")
    user: str = Field(default="rag_user")
    password: SecretStr = Field(default=SecretStr("rag_password"))
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    echo: bool = Field(default=False)

    @property
    def async_url(self) -> str:
        """Async SQLAlchemy connection URL."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.db}"
        )

    @property
    def sync_url(self) -> str:
        """Sync SQLAlchemy connection URL (for Alembic)."""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class RedisSettings(BaseSettings):
    """Redis settings."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", env_file=".env", extra="ignore")

    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: SecretStr | None = Field(default=None)
    max_connections: int = Field(default=20)
    cache_ttl: int = Field(default=3600, description="Default cache TTL in seconds")

    @property
    def url(self) -> str:
        """Redis connection URL."""
        if self.password:
            return f"redis://:{self.password.get_secret_value()}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


class CelerySettings(BaseSettings):
    """Celery task queue settings."""

    model_config = SettingsConfigDict(env_prefix="CELERY_", env_file=".env", extra="ignore")

    broker_url: str = Field(default="redis://localhost:6379/1")
    result_backend: str = Field(default="redis://localhost:6379/2")
    task_serializer: str = Field(default="json")
    result_serializer: str = Field(default="json")
    task_time_limit: int = Field(default=3600)
    task_soft_time_limit: int = Field(default=3300)


class Neo4jSettings(BaseSettings):
    """Neo4j graph database settings."""

    model_config = SettingsConfigDict(env_prefix="NEO4J_", env_file=".env", extra="ignore")

    uri: str = Field(default="bolt://localhost:7687")
    user: str = Field(default="neo4j")
    password: SecretStr = Field(default=SecretStr("neo4j_password"))
    database: str = Field(default="neo4j")
    max_connection_pool_size: int = Field(default=50)


class LLMSettings(BaseSettings):
    """LLM provider settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Provider selection
    primary_llm_provider: Literal["groq", "openai"] = Field(default="groq")

    # Groq
    groq_api_key: SecretStr | None = Field(default=None)
    groq_model_name: str = Field(default="llama-3.3-70b-versatile")
    groq_max_tokens: int = Field(default=4096)
    groq_temperature: float = Field(default=0.1, ge=0.0, le=2.0)

    # OpenAI
    openai_api_key: SecretStr | None = Field(default=None)
    openai_model_name: str = Field(default="gpt-4o-mini")
    openai_max_tokens: int = Field(default=4096)
    openai_temperature: float = Field(default=0.1, ge=0.0, le=2.0)


class EmbeddingSettings(BaseSettings):
    """Embedding model settings."""

    model_config = SettingsConfigDict(env_prefix="EMBEDDING_", env_file=".env", extra="ignore")

    model: str = Field(default="all-mpnet-base-v2")
    device: str = Field(default="cpu")
    batch_size: int = Field(default=64)
    dimension: int = Field(default=768)


class RetrievalSettings(BaseSettings):
    """Retrieval engine settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    retrieval_top_k: int = Field(default=20)
    reranking_top_k: int = Field(default=5)
    hybrid_alpha: float = Field(default=0.5, ge=0.0, le=1.0, description="0=BM25, 1=dense")
    cross_encoder_model: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    cross_encoder_max_length: int = Field(default=512)
    faiss_index_path: str = Field(default="./data/faiss_index")
    faiss_index_type: str = Field(default="IndexFlatIP")
    bm25_index_path: str = Field(default="./data/bm25_index")
    bm25_k1: float = Field(default=1.5)
    bm25_b: float = Field(default=0.75)

    # Evidence Sufficiency Gate
    evidence_min_coverage: float = Field(default=0.6, ge=0.0, le=1.0)
    evidence_min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence_min_sources: int = Field(default=2)
    evidence_max_retries: int = Field(default=2)


class ChunkingSettings(BaseSettings):
    """Document chunking settings."""

    model_config = SettingsConfigDict(env_prefix="CHUNK_", env_file=".env", extra="ignore")

    size: int = Field(default=512)
    overlap: int = Field(default=50)
    parent_chunk_size: int = Field(default=2048)


class SecuritySettings(BaseSettings):
    """Security settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: SecretStr = Field(default=SecretStr("change-me-to-random-64-char-string"))
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)
    jwt_refresh_token_expire_days: int = Field(default=7)
    # Stored as a raw string; parsed into a list via the property below
    allowed_origins_str: str = Field(
        default="http://localhost:3000",
        alias="ALLOWED_ORIGINS",
        validation_alias="ALLOWED_ORIGINS",
    )
    rate_limit_per_minute: int = Field(default=60)
    rate_limit_burst: int = Field(default=100)

    @property
    def allowed_origins(self) -> list[str]:
        """Parse comma-separated or JSON-array allowed origins string."""
        v = self.allowed_origins_str.strip()
        if v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                pass
        return [origin.strip() for origin in v.split(",") if origin.strip()]


class ObservabilitySettings(BaseSettings):
    """Observability settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    otel_exporter_otlp_endpoint: str = Field(default="http://localhost:4317")
    otel_service_name: str = Field(default="enterpriseit-rag-backend")
    prometheus_port: int = Field(default=9090)


class AppSettings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "staging", "production"] = Field(default="development")
    app_name: str = Field(default="EnterpriseIT-RAG")
    app_version: str = Field(default="1.0.0")
    app_debug: bool = Field(default=True)
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="DEBUG"
    )

    # Upload
    upload_dir: str = Field(default="./data/uploads")
    max_upload_size_mb: int = Field(default=100)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


class Settings:
    """
    Aggregated settings container.

    Usage:
        from app.core.config import get_settings
        settings = get_settings()
        print(settings.app.app_name)
        print(settings.database.async_url)
    """

    def __init__(self) -> None:
        self.app = AppSettings()
        self.database = DatabaseSettings()
        self.redis = RedisSettings()
        self.celery = CelerySettings()
        self.neo4j = Neo4jSettings()
        self.llm = LLMSettings()
        self.embedding = EmbeddingSettings()
        self.retrieval = RetrievalSettings()
        self.chunking = ChunkingSettings()
        self.security = SecuritySettings()
        self.observability = ObservabilitySettings()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached settings instance.

    The @lru_cache ensures settings are only loaded once per process lifetime.
    In tests, call get_settings.cache_clear() to reset between test cases.
    """
    return Settings()
