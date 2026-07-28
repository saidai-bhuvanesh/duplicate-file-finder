"""
Base Document Loader interface and helper utilities.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, BinaryIO

from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem


class BaseLoader(ABC):
    """
    Abstract Base Class for all document loaders.

    Loaders take raw input (files, bytes, streams, API responses) and parse them
    into one or more Document entities with rich metadata.
    """

    @abstractmethod
    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        """Check if this loader supports the given file extension or MIME type."""
        ...

    @abstractmethod
    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> list[Document]:
        """
        Parse source content into Document domain entities.

        Args:
            source: File path, raw bytes, or stream.
            title: Fallback document title.
            metadata: Additional metadata to attach.
            source_system: Source system designation.

        Returns:
            List of parsed Document entities.
        """
        ...
