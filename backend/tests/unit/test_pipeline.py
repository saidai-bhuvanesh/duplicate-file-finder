"""
Unit tests for IngestionPipeline.
"""

import pytest
from unittest.mock import AsyncMock

from app.core.exceptions import DuplicateDocumentError
from app.domain.entities.document import Document, DocumentStatus, DocumentType, SourceSystem
from app.domain.entities.chunk import Chunk
from app.ingestion.pipeline import IngestionPipeline


@pytest.mark.unit
@pytest.mark.asyncio
class TestIngestionPipeline:
    async def test_pipeline_execution_success(self, mock_document_repo, mock_chunk_repo):
        mock_doc = Document(
            id="doc-123",
            title="Test Doc",
            content="Sample document content for ingestion pipeline test.",
            content_hash="hash123",
        )
        mock_document_repo.get_by_content_hash = AsyncMock(return_value=None)
        mock_document_repo.create = AsyncMock(return_value=mock_doc)
        mock_document_repo.update = AsyncMock(return_value=mock_doc)
        mock_chunk_repo.create_many = AsyncMock(return_value=[Chunk(document_id="doc-123", content="Sample")])

        from unittest.mock import patch
        with patch("app.graph.graph_service.GraphService"):
            pipeline = IngestionPipeline(mock_document_repo, mock_chunk_repo, use_parent_child=False)
            doc, chunks = await pipeline.run(
                source="Sample document content for ingestion pipeline test.",
                title="Test Doc",
                source_system=SourceSystem.LOCAL_FILE,
            )

        assert doc.id == "doc-123"
        assert len(chunks) > 0
        assert mock_document_repo.create.called
        assert mock_chunk_repo.create_many.called

    async def test_pipeline_deduplication(self, mock_document_repo, mock_chunk_repo):
        existing_doc = Document(id="existing-123", content_hash="hash123")
        mock_document_repo.get_by_content_hash = AsyncMock(return_value=existing_doc)

        pipeline = IngestionPipeline(mock_document_repo, mock_chunk_repo)

        with pytest.raises(DuplicateDocumentError):
            await pipeline.run(source="Duplicate text content")
