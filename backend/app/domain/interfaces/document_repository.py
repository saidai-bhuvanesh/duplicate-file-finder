"""
Abstract document repository interface.

Defines the contract for document persistence.
Infrastructure implementations must satisfy this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.entities.document import Document, DocumentStatus, DocumentType, SourceSystem


class DocumentRepository(ABC):
    """
    Abstract repository for Document persistence.

    Follows the Repository Pattern — callers work with domain entities,
    not ORM models or raw SQL.
    """

    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Persist a new document and return it with any DB-generated fields."""
        ...

    @abstractmethod
    async def get_by_id(self, document_id: str) -> Document | None:
        """Return a document by its ID, or None if not found."""
        ...

    @abstractmethod
    async def get_by_content_hash(self, content_hash: str) -> Document | None:
        """Return a document matching the content hash (deduplication check)."""
        ...

    @abstractmethod
    async def update(self, document: Document) -> Document:
        """Update an existing document and return the updated entity."""
        ...

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        """Delete a document by ID. Returns True if deleted, False if not found."""
        ...

    @abstractmethod
    async def list(
        self,
        status: DocumentStatus | None = None,
        document_type: DocumentType | None = None,
        source_system: SourceSystem | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        """
        List documents with optional filters.

        Returns:
            Tuple of (documents, total_count).
        """
        ...

    @abstractmethod
    async def count(
        self,
        status: DocumentStatus | None = None,
        source_system: SourceSystem | None = None,
    ) -> int:
        """Count documents matching optional filters."""
        ...

    @abstractmethod
    async def search_by_title(self, query: str, limit: int = 10) -> list[Document]:
        """Full-text search on document titles."""
        ...

    @abstractmethod
    async def get_stale_documents(self, max_age_days: int) -> list[Document]:
        """Return documents not updated within max_age_days (for re-ingestion)."""
        ...

    @abstractmethod
    async def bulk_update_status(
        self, document_ids: list[str], status: DocumentStatus
    ) -> int:
        """Update status for multiple documents. Returns count of updated records."""
        ...
