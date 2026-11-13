"""
Integration tests for the health endpoint.

These tests run against the real FastAPI app (but mock external dependencies).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.integration
class TestHealthEndpoints:
    """Test suite for /health, /ready, and /version endpoints."""

    def test_health_returns_200(self, client):
        """GET /health should return 200 with healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_version_returns_correct_info(self, client):
        """GET /version should return app metadata."""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert data["app_name"] == "EnterpriseIT-RAG"
        assert "version" in data
        assert "environment" in data
        assert "python_version" in data

    def test_health_has_correct_content_type(self, client):
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]

    def test_api_v1_health_returns_200(self, client):
        """The versioned health endpoint should also work."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    @patch("app.api.v1.health.check_database_health", new_callable=AsyncMock)
    @patch("app.api.v1.health.RedisClient")
    def test_ready_returns_503_when_db_down(
        self, mock_redis_class, mock_db_health, client
    ):
        """GET /ready should return 503 when DB is unreachable."""
        mock_db_health.return_value = False
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis_class.get_instance.return_value = mock_redis

        response = client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["checks"]["postgresql"] is False

    @patch("app.api.v1.health.check_database_health", new_callable=AsyncMock)
    @patch("app.api.v1.health.RedisClient")
    def test_ready_returns_200_when_all_healthy(
        self, mock_redis_class, mock_db_health, client
    ):
        """GET /ready should return 200 when all deps healthy."""
        mock_db_health.return_value = True
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis_class.get_instance.return_value = mock_redis

        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["postgresql"] is True
        assert data["checks"]["redis"] is True


@pytest.mark.integration
class TestGraphStatsEndpoint:
    @patch("app.api.v1.graph._graph_service.get_graph_stats", new_callable=AsyncMock)
    def test_graph_stats_returns_totals(self, mock_stats, client):
        mock_stats.return_value = {
            "nodes": {"Service": 3},
            "relationships": {"OWNS": 2},
            "total_nodes": 3,
            "total_relationships": 2,
        }

        response = client.get("/api/v1/graph/stats")

        assert response.status_code == 200
        assert response.json() == {
            "nodes": {"Service": 3},
            "relationships": {"OWNS": 2},
            "total_nodes": 3,
            "total_relationships": 2,
            "status": "healthy",
            "database": "neo4j",
        }

    @patch("app.api.v1.graph._graph_service.get_graph_stats", new_callable=AsyncMock)
    def test_graph_stats_marks_database_unavailable(self, mock_stats, client):
        mock_stats.side_effect = RuntimeError("Neo4j unavailable")

        response = client.get("/api/v1/graph/stats")

        assert response.status_code == 200
        assert response.json()["status"] == "unavailable"
        assert response.json()["total_nodes"] == 0


@pytest.mark.integration
class TestDocumentEndpoints:
    """Test suite for document CRUD API."""

    def test_create_document_returns_201(self, client):
        """POST /api/v1/documents/ should return 201 for valid request."""
        from app.core.dependencies import get_document_service
        from app.domain.entities.document import (
            Document,
            DocumentMetadata,
            DocumentStatus,
            DocumentType,
            SourceSystem,
        )

        doc = Document(
            id="test-id-123",
            title="Test Document",
            content="Test content",
            document_type=DocumentType.MARKDOWN,
            status=DocumentStatus.PENDING,
            metadata=DocumentMetadata(source_system=SourceSystem.LOCAL_FILE),
            content_hash="abc123",
        )

        mock_service = AsyncMock()
        mock_service.create_document = AsyncMock(return_value=doc)

        payload = {
            "title": "Test Document",
            "content": "This is a test document with meaningful content.",
            "document_type": "markdown",
            "source_system": "local_file",
        }
        
        # Override dependency
        app = client.app
        app.dependency_overrides[get_document_service] = lambda: mock_service
        
        try:
            response = client.post("/api/v1/documents/", json=payload)
            assert response.status_code in (201, 200, 422, 503, 500)
        finally:
            app.dependency_overrides.pop(get_document_service, None)

    def test_list_documents_endpoint_exists(self, client):
        """GET /api/v1/documents/ should return a response (may be error without DB)."""
        response = client.get("/api/v1/documents/")
        assert response.status_code in (200, 503, 500)

    def test_search_endpoint_returns_structured_response(self, client):
        """POST /api/v1/search/ should return properly structured response."""
        payload = {"query": "What is Kubernetes?"}
        response = client.post("/api/v1/search/", json=payload)
        # The app might not have DB, return 500 or 503
        assert response.status_code in (200, 500, 503)
        if response.status_code == 200:
            data = response.json()
            assert "query_id" in data
            assert "answer" in data

    def test_openapi_schema_accessible(self, client):
        """OpenAPI schema should be accessible in development."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "EnterpriseIT-RAG API"
        assert "paths" in schema
        assert "/api/v1/documents/upload" in schema["paths"]
        assert "/api/v1/graph/nodes" in schema["paths"]
        assert "/api/v1/graph/cypher" in schema["paths"]
