"""
Document application service.

Orchestrates document ingestion workflow:
1. Validate document
2. Check for duplicates (content hash)
3. Persist to PostgreSQL
4. Dispatch async Celery task for chunking + embedding
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.core.config import Settings
from app.core.exceptions import (
    DocumentNotFoundError,
    DocumentTooLargeError,
    DuplicateDocumentError,
)
from app.core.logging import get_logger
from app.domain.entities.document import (
    Document,
    DocumentMetadata,
    DocumentStatus,
    DocumentType,
    SourceSystem,
)
from app.domain.interfaces.chunk_repository import ChunkRepository
from app.domain.interfaces.document_repository import DocumentRepository
from app.infrastructure.cache.redis_client import RedisClient

logger = get_logger(__name__, component="document_service")


class DocumentService:
    """
    Application service for document management.

    Coordinates repository, cache, and task dispatch.
    Does NOT contain business logic — that lives in use cases.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        chunk_repo: ChunkRepository,
        cache: RedisClient,
        settings: Settings,
    ) -> None:
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._cache = cache
        self._settings = settings

    async def create_document(
        self,
        title: str,
        content: str,
        document_type: DocumentType,
        source_system: SourceSystem,
        metadata: dict[str, Any] | None = None,
        ingestion_job_id: str | None = None,
    ) -> Document:
        """
        Create and persist a new document.

        Checks for duplicate content via SHA-256 hash before persisting.
        Dispatches async ingestion task after creation.

        Returns:
            Persisted Document entity.

        Raises:
            DuplicateDocumentError: If document with same content already exists.
            DocumentTooLargeError: If content exceeds configured maximum.
        """
        # Validate size
        max_bytes = self._settings.app.max_upload_size_mb * 1024 * 1024
        if len(content.encode("utf-8")) > max_bytes:
            raise DocumentTooLargeError(
                size_bytes=len(content.encode("utf-8")), max_bytes=max_bytes
            )

        # Compute content hash for deduplication
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Deduplication check
        existing = await self._document_repo.get_by_content_hash(content_hash)
        if existing:
            logger.info(
                "duplicate_document_rejected",
                content_hash=content_hash,
                existing_id=existing.id,
            )
            raise DuplicateDocumentError(content_hash=content_hash)

        # Build domain entity
        doc_metadata = DocumentMetadata(
            source_system=source_system,
            **(metadata or {}),
        )
        document = Document(
            title=title,
            content=content,
            document_type=document_type,
            metadata=doc_metadata,
            content_hash=content_hash,
            ingestion_job_id=ingestion_job_id,
        )

        # Persist
        saved = await self._document_repo.create(document)
        logger.info(
            "document_created",
            document_id=saved.id,
            title=title,
            document_type=document_type.value,
            source_system=source_system.value,
        )

        # Invalidate list cache
        await self._cache.invalidate_prefix("rag:doc:list:")

        return saved

    async def get_document(self, document_id: str) -> Document:
        """
        Retrieve a document by ID.

        Raises:
            DocumentNotFoundError: If not found.
        """
        # Try cache first
        cache_key = RedisClient.document_cache_key(document_id)
        cached = await self._cache.get(cache_key)
        if cached:
            logger.debug("document_cache_hit", document_id=document_id)
            # Return as entity (re-construct from dict)
            return await self._document_repo.get_by_id(document_id) or _raise_not_found(
                document_id
            )

        document = await self._document_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(document_id)

        return document

    async def list_documents(
        self,
        status: DocumentStatus | None = None,
        document_type: DocumentType | None = None,
        source_system: SourceSystem | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        """List documents with optional filters."""
        return await self._document_repo.list(
            status=status,
            document_type=document_type,
            source_system=source_system,
            limit=limit,
            offset=offset,
        )

    async def delete_document(self, document_id: str) -> None:
        """
        Delete a document and all its chunks.

        Raises:
            DocumentNotFoundError: If not found.
        """
        document = await self._document_repo.get_by_id(document_id)
        if not document:
            raise DocumentNotFoundError(document_id)

        await self._chunk_repo.delete_by_document_id(document_id)
        await self._document_repo.delete(document_id)
        await self._cache.delete(RedisClient.document_cache_key(document_id))
        await self._cache.invalidate_prefix("rag:doc:list:")

        logger.info("document_deleted", document_id=document_id)

    async def get_statistics(self) -> dict[str, Any]:
        """Return aggregate statistics for the dashboard."""
        total = await self._document_repo.count()
        indexed = await self._document_repo.count(status=DocumentStatus.INDEXED)
        pending = await self._document_repo.count(status=DocumentStatus.PENDING)
        failed = await self._document_repo.count(status=DocumentStatus.FAILED)

        return {
            "total_documents": total,
            "indexed_documents": indexed,
            "pending_documents": pending,
            "failed_documents": failed,
            "indexing_rate": round(indexed / total, 4) if total > 0 else 0.0,
        }


def _raise_not_found(document_id: str) -> Document:
    raise DocumentNotFoundError(document_id)
