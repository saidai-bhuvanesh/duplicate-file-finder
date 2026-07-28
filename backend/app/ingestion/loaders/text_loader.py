"""
Text, Markdown, HTML, CSV, JSON, and OpenAPI document loaders.
"""

from __future__ import annotations

import csv
import hashlib
import json
import io
from typing import Any, BinaryIO

from bs4 import BeautifulSoup

from app.core.exceptions import IngestionError
from app.core.logging import get_logger
from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
from app.ingestion.loaders.base import BaseLoader

logger = get_logger(__name__, component="text_loader")


class TextLoader(BaseLoader):
    """Loader for plain text and Markdown documents."""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".rst"}

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        ext = file_extension.lower() if file_extension.startswith(".") else f".{file_extension.lower()}"
        return ext in self.SUPPORTED_EXTENSIONS or (mime_type is not None and "text/" in mime_type)

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> list[Document]:
        content_text = _read_content_as_str(source)
        doc_type = DocumentType.MARKDOWN if (metadata and metadata.get("file_extension", "").endswith((".md", ".markdown"))) else DocumentType.TEXT
        
        doc_title = title or (metadata.get("filename") if metadata else None) or "Text Document"
        content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()

        doc_meta = DocumentMetadata.from_dict(metadata, source_system=source_system)

        doc = Document(
            title=doc_title,
            content=content_text,
            document_type=doc_type,
            metadata=doc_meta,
            content_hash=content_hash,
            token_count=len(content_text.split()),
        )
        return [doc]


class HTMLLoader(BaseLoader):
    """Loader for HTML files using BeautifulSoup to clean DOM trees."""

    SUPPORTED_EXTENSIONS = {".html", ".htm", ".xhtml"}

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        ext = file_extension.lower() if file_extension.startswith(".") else f".{file_extension.lower()}"
        return ext in self.SUPPORTED_EXTENSIONS or (mime_type is not None and "html" in mime_type)

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> list[Document]:
        raw_html = _read_content_as_str(source)
        soup = BeautifulSoup(raw_html, "lxml")

        # Strip scripts, styles, and navigation elements
        for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            element.decompose()

        page_title = soup.title.string.strip() if soup.title and soup.title.string else None
        doc_title = title or page_title or (metadata.get("filename", "HTML Document") if metadata else "HTML Document")

        clean_text = soup.get_text(separator="\n\n").strip()
        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

        doc_meta = DocumentMetadata.from_dict(metadata, source_system=source_system)

        doc = Document(
            title=doc_title,
            content=clean_text,
            document_type=DocumentType.HTML,
            metadata=doc_meta,
            content_hash=content_hash,
            token_count=len(clean_text.split()),
        )
        return [doc]


class StructuredDataLoader(BaseLoader):
    """Loader for CSV, JSON, and OpenAPI specification documents."""

    SUPPORTED_EXTENSIONS = {".csv", ".json", ".yaml", ".yml"}

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        ext = file_extension.lower() if file_extension.startswith(".") else f".{file_extension.lower()}"
        return ext in self.SUPPORTED_EXTENSIONS

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> list[Document]:
        raw_text = _read_content_as_str(source)
        ext = metadata.get("file_extension", "").lower() if metadata else ""
        filename = metadata.get("filename", "Data Document") if metadata else "Data Document"

        if ext in (".json", ".yaml", ".yml"):
            return self._load_json_or_yaml(raw_text, title or filename, metadata, source_system, ext)
        elif ext == ".csv":
            return self._load_csv(raw_text, title or filename, metadata, source_system)
        else:
            doc_meta = DocumentMetadata.from_dict(metadata, source_system=source_system)
            return [
                Document(
                    title=title or filename,
                    content=raw_text,
                    document_type=DocumentType.TEXT,
                    metadata=doc_meta,
                    content_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
                    token_count=len(raw_text.split()),
                )
            ]

    def _load_json_or_yaml(
        self,
        raw_text: str,
        title: str,
        metadata: dict[str, Any] | None,
        source_system: SourceSystem,
        ext: str,
    ) -> list[Document]:
        doc_type = DocumentType.JSON
        try:
            data = json.loads(raw_text)
            # Detect OpenAPI specification
            if isinstance(data, dict) and ("openapi" in data or "swagger" in data):
                doc_type = DocumentType.OPENAPI
                title = f"OpenAPI Spec: {data.get('info', {}).get('title', title)}"
            formatted_content = json.dumps(data, indent=2)
        except Exception:
            formatted_content = raw_text

        content_hash = hashlib.sha256(formatted_content.encode("utf-8")).hexdigest()
        doc_meta = DocumentMetadata.from_dict(metadata, source_system=source_system)

        return [
            Document(
                title=title,
                content=formatted_content,
                document_type=doc_type,
                metadata=doc_meta,
                content_hash=content_hash,
                token_count=len(formatted_content.split()),
            )
        ]

    def _load_csv(
        self,
        raw_text: str,
        title: str,
        metadata: dict[str, Any] | None,
        source_system: SourceSystem,
    ) -> list[Document]:
        reader = csv.reader(io.StringIO(raw_text))
        rows = list(reader)
        if not rows:
            formatted_content = raw_text
        else:
            headers = rows[0]
            formatted_rows = []
            for row in rows[1:]:
                row_str = ", ".join(f"{h}: {v}" for h, v in zip(headers, row))
                formatted_rows.append(row_str)
            formatted_content = "\n".join(formatted_rows)

        content_hash = hashlib.sha256(formatted_content.encode("utf-8")).hexdigest()
        doc_meta = DocumentMetadata.from_dict(metadata, source_system=source_system)

        return [
            Document(
                title=title,
                content=formatted_content,
                document_type=DocumentType.CSV,
                metadata=doc_meta,
                content_hash=content_hash,
                token_count=len(formatted_content.split()),
            )
        ]


def _read_content_as_str(source: str | bytes | BinaryIO) -> str:
    """Helper to safely read source as UTF-8 string."""
    if isinstance(source, str):
        # Check if source is a file path
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
    raise IngestionError(f"Unsupported source type: {type(source)}")
