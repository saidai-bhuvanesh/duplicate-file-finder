"""
Notion pages and Notion export document loader.
"""

from __future__ import annotations

import hashlib
from typing import Any, BinaryIO

from app.core.logging import get_logger
from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
from app.ingestion.loaders.base import BaseLoader

logger = get_logger(__name__, component="notion_loader")


class NotionLoader(BaseLoader):
    """Loader for Notion pages or Notion Markdown/HTML exports."""

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        return False

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.NOTION,
    ) -> list[Document]:
        meta = metadata or {}
        raw_text = _read_text(source)
        doc_title = title or meta.get("title") or meta.get("filename", "Notion Page")

        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        doc_meta = DocumentMetadata.from_dict(meta, source_system=SourceSystem.NOTION)

        return [
            Document(
                title=doc_title,
                content=raw_text,
                document_type=DocumentType.NOTION,
                metadata=doc_meta,
                content_hash=content_hash,
                token_count=len(raw_text.split()),
            )
        ]


def _read_text(source: str | bytes | BinaryIO) -> str:
    if isinstance(source, str):
        import os
        if os.path.exists(source) and os.path.isfile(source):
            with open(source, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        return source
    elif isinstance(source, bytes):
        return source.decode("utf-8", errors="replace")
    elif hasattr(source, "read"):
        content = source.read()
        if isinstance(content, bytes):
            return content.decode("utf-8", errors="replace")
        return str(content)
    return str(source)
