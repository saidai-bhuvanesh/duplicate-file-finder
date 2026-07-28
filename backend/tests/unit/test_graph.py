"""
Unit tests for Phase 4 Enterprise Knowledge Graph (GraphRAG), Entity Extractor, and Graph Service.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
from app.graph.extractor import EntityExtractor
from app.graph.graph_rag import GraphRAGEngine
from app.graph.graph_service import GraphService


@pytest.mark.unit
class TestEntityExtractor:
    def test_extract_author_and_team(self):
        extractor = EntityExtractor()
        doc = Document(
            title="Service Architecture",
            content="The auth-service handles JWT token verification. POST /api/v1/auth/login endpoint is exposed.",
            metadata=DocumentMetadata(
                source_system=SourceSystem.GITHUB,
                author="Alice Smith",
                team="Core Security Team",
                repository="org/auth-service",
            ),
        )
        nodes, rels = extractor.extract_from_document(doc)

        labels = {n.label for n in nodes}
        assert "Employee" in labels
        assert "Team" in labels
        assert "Repository" in labels
        assert "APIEndpoint" in labels

        rel_types = {r.rel_type for r in rels}
        assert "MEMBER_OF" in rel_types
        assert "OWNS" in rel_types

    def test_extract_s3_and_tickets(self):
        extractor = EntityExtractor()
        doc = Document(
            title="Runbook",
            content="Logs are backed up to s3://company-prod-logs bucket. Related ticket PROJ-8821.",
            metadata=DocumentMetadata(source_system=SourceSystem.LOCAL_FILE),
        )
        nodes, rels = extractor.extract_from_document(doc)

        ids = {n.id for n in nodes}
        assert "s3://company-prod-logs" in ids
        assert "PROJ-8821" in ids


@pytest.mark.unit
class TestGraphService:
    @pytest.mark.asyncio
    async def test_sync_document_to_graph(self):
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(return_value=[])

        service = GraphService(neo4j_client=mock_neo4j)
        doc = Document(
            title="Service Arch",
            content="auth-service deployment guide",
            metadata=DocumentMetadata(source_system=SourceSystem.LOCAL_FILE, team="Security"),
        )
        result = await service.sync_document_to_graph(doc)

        assert "nodes_synced" in result
        assert "relationships_synced" in result
        assert mock_neo4j.execute_query.called


@pytest.mark.unit
class TestGraphRAGEngine:
    @pytest.mark.asyncio
    async def test_retrieve_graph_context(self):
        mock_neo4j = AsyncMock()
        mock_neo4j.execute_query = AsyncMock(
            return_value=[
                {
                    "entity_id": "auth-service",
                    "entity_label": "Service",
                    "entity_name": "auth-service",
                    "connected_id": "user-db",
                    "connected_label": "Database",
                    "doc_id": "doc-1",
                    "doc_title": "Auth Architecture",
                    "hop_distance": 1,
                }
            ]
        )

        engine = GraphRAGEngine(neo4j_client=mock_neo4j)
        chunks = await engine.retrieve_graph_context("Which database does auth-service use?", top_k=3)

        assert len(chunks) == 1
        assert "auth-service" in chunks[0].content
        assert chunks[0].metadata["source_system"] == "neo4j_graph"
