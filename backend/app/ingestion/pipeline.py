"""
Unified Ingestion Pipeline Orchestrator.

Orchestrates: Document Loading → Metadata Enrichment → Adaptive Chunking → Deduplication → DB & Index Persistence.
"""

from __future__ import annotations

import hashlib
from typing import Any, BinaryIO

from app.core.config import get_settings
from app.core.exceptions import DuplicateDocumentError, IngestionError
from app.core.logging import get_logger
from app.domain.entities.chunk import Chunk
from app.domain.entities.document import Document, DocumentStatus, DocumentType, SourceSystem
from app.domain.interfaces.chunk_repository import ChunkRepository
from app.domain.interfaces.document_repository import DocumentRepository
from app.ingestion.chunkers.base_chunker import BaseChunker
from app.ingestion.chunkers.code_chunker import CodeChunker
from app.ingestion.chunkers.parent_child_chunker import ParentChildChunker
from app.ingestion.chunkers.recursive_chunker import RecursiveChunker
from app.ingestion.chunkers.semantic_chunker import SemanticChunker
from app.ingestion.loaders.loader_registry import get_loader_registry

logger = get_logger(__name__, component="ingestion_pipeline")


class IngestionPipeline:
    """
    Core pipeline orchestrator for document ingestion.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        use_parent_child: bool = True,
    ) -> None:
        self._doc_repo = document_repo
        self._chunk_repo = chunk_repo
        self.use_parent_child = use_parent_child
        self.registry = get_loader_registry()

    def select_chunker(self, document: Document) -> BaseChunker:
        """Adaptive chunker selection based on document type and settings."""
        if self.use_parent_child:
            return ParentChildChunker()

        doc_type = document.document_type
        if doc_type in (
            DocumentType.CODE,
            DocumentType.TERRAFORM,
            DocumentType.KUBERNETES,
            DocumentType.DOCKER,
        ):
            return CodeChunker()
        elif doc_type in (
            DocumentType.MARKDOWN,
            DocumentType.HTML,
            DocumentType.CONFLUENCE,
            DocumentType.NOTION,
        ):
            return SemanticChunker()
        else:
            return RecursiveChunker()

    async def run(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
        job_id: str | None = None,
    ) -> tuple[Document, list[Chunk]]:
        """
        Run the complete ingestion pipeline for a source item.

        Returns:
            Tuple of (Persisted Document, List of Persisted Chunks)
        """
        logger.info("starting_ingestion_pipeline", title=title, source_system=source_system.value)

        # 1. Load document(s)
        docs = await self.registry.load_document(
            source=source,
            title=title,
            metadata=metadata,
            source_system=source_system,
        )
        if not docs:
            raise IngestionError("Loader produced no document entities")

        doc = docs[0]
        if job_id:
            doc.ingestion_job_id = job_id

        # 2. Check content hash for deduplication
        existing = await self._doc_repo.get_by_content_hash(doc.content_hash)
        if existing:
            logger.info("duplicate_document_skipped", document_id=existing.id, content_hash=doc.content_hash)
            raise DuplicateDocumentError(content_hash=doc.content_hash)

        # 3. Mark processing & Persist Document
        doc.mark_processing()
        saved_doc = await self._doc_repo.create(doc)

        try:
            # 4. Select adaptive chunker & generate chunks
            chunker = self.select_chunker(saved_doc)
            logger.info("chunker_selected", chunker_type=type(chunker).__name__, doc_id=saved_doc.id)
            chunks = chunker.chunk_document(saved_doc)

            # 5. Persist Chunks to PostgreSQL
            saved_chunks = []
            if chunks:
                saved_chunks = await self._chunk_repo.create_many(chunks)

            # 6. Update Document status to INDEXED
            saved_doc.mark_indexed(chunk_count=len(saved_chunks))
            await self._doc_repo.update(saved_doc)

            # 7. Sync extracted entities to Neo4j Knowledge Graph (best effort)
            try:
                from app.graph.graph_service import GraphService
                graph_svc = GraphService()
                await graph_svc.sync_document_to_graph(saved_doc, saved_chunks)
            except Exception as graph_err:
                logger.warning("graph_sync_deferred", doc_id=saved_doc.id, error=str(graph_err))

            logger.info(
                "ingestion_pipeline_completed",
                doc_id=saved_doc.id,
                chunk_count=len(saved_chunks),
            )
            return saved_doc, saved_chunks

        except Exception as exc:
            logger.error("ingestion_pipeline_failed", doc_id=saved_doc.id, error=str(exc))
            saved_doc.mark_failed(str(exc))
            await self._doc_repo.update(saved_doc)
            raise IngestionError(f"Ingestion pipeline failed: {exc}") from exc
