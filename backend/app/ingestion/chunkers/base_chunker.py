"""
Base Chunker interface for document segmentation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.entities.document import Document


class BaseChunker(ABC):
    """
    Abstract Base Class for document chunkers.

    Chunkers split Document entities into retrievable Chunk domain entities.
    """

    @abstractmethod
    def chunk_document(self, document: Document) -> list[Chunk]:
        """
        Split a Document entity into a list of Chunk domain entities.

        Args:
            document: Document domain entity.

        Returns:
            List of Chunk entities with character boundaries, index, and metadata.
        """
        ...
