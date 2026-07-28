"""
Abstract chunk repository interface.

Defines the contract for chunk (document segment) persistence.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.chunk import Chunk, ChunkType


class ChunkRepository(ABC):
    """Abstract repository for Chunk persistence."""

    @abstractmethod
    async def create_many(self, chunks: list[Chunk]) -> list[Chunk]:
        """Bulk insert chunks. More efficient than creating one-by-one."""
        ...

    @abstractmethod
    async def get_by_id(self, chunk_id: str) -> Chunk | None:
        """Return a chunk by ID."""
        ...

    @abstractmethod
    async def get_by_document_id(self, document_id: str) -> list[Chunk]:
        """Return all chunks belonging to a document, ordered by chunk_index."""
        ...

    @abstractmethod
    async def get_parent_chunk(self, chunk_id: str) -> Chunk | None:
        """
        Return the parent chunk for a given child chunk.

        Used by the Parent Document Retrieval strategy —
        retrieve small chunks for matching, then return larger parent context.
        """
        ...

    @abstractmethod
    async def get_surrounding_chunks(
        self, chunk_id: str, window: int = 1
    ) -> list[Chunk]:
        """
        Return chunks surrounding the given chunk (for context expansion).

        Args:
            chunk_id: Target chunk ID.
            window: Number of chunks before/after to include.
        """
        ...

    @abstractmethod
    async def delete_by_document_id(self, document_id: str) -> int:
        """Delete all chunks for a document. Returns count deleted."""
        ...

    @abstractmethod
    async def count_by_document_id(self, document_id: str) -> int:
        """Count chunks for a document."""
        ...

    @abstractmethod
    async def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        """Batch fetch chunks by ID list (for citation resolution)."""
        ...
