"""
Abstract vector store interface.

Defines the contract for vector index operations.
Infrastructure implementations may use FAISS, Qdrant, Pinecone, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class VectorSearchResult:
    """A single result from a vector similarity search."""

    chunk_id: str
    document_id: str
    score: float
    content: str
    metadata: dict[str, Any]


class VectorStore(ABC):
    """Abstract vector store for dense embedding retrieval."""

    @abstractmethod
    async def add_embeddings(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        document_ids: list[str],
        contents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> int:
        """
        Add embeddings to the index.

        Returns:
            Number of embeddings added.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        """
        Perform ANN similarity search.

        Args:
            query_embedding: Query dense vector.
            top_k: Number of results to return.
            filters: Optional metadata filters.

        Returns:
            List of VectorSearchResult, sorted by score descending.
        """
        ...

    @abstractmethod
    async def delete_by_document_id(self, document_id: str) -> int:
        """Remove all embeddings for a document. Returns count removed."""
        ...

    @abstractmethod
    async def delete_by_chunk_ids(self, chunk_ids: list[str]) -> int:
        """Remove specific embeddings by chunk ID."""
        ...

    @abstractmethod
    async def get_index_stats(self) -> dict[str, Any]:
        """Return index statistics (size, dimension, etc.)."""
        ...

    @abstractmethod
    async def save(self) -> None:
        """Persist the index to disk (for FAISS)."""
        ...

    @abstractmethod
    async def load(self) -> None:
        """Load the index from disk (for FAISS)."""
        ...
