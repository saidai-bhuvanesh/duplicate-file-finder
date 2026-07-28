"""
PDF and DOCX document loaders.
"""

from __future__ import annotations

import hashlib
import io
from typing import Any, BinaryIO

import pypdf
import docx

from app.core.exceptions import IngestionError
from app.core.logging import get_logger
from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
from app.ingestion.loaders.base import BaseLoader

logger = get_logger(__name__, component="pdf_docx_loader")


class PDFLoader(BaseLoader):
    """Loader for PDF documents extracting text page-by-page."""

    SUPPORTED_EXTENSIONS = {".pdf"}

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        ext = file_extension.lower() if file_extension.startswith(".") else f".{file_extension.lower()}"
        return ext in self.SUPPORTED_EXTENSIONS or (mime_type is not None and "pdf" in mime_type)

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> list[Document]:
        stream = _get_bytes_stream(source)
        try:
            reader = pypdf.PdfReader(stream)
            pages_text = []
            for i, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(f"--- [Page {i}] ---\n{text.strip()}")

            full_text = "\n\n".join(pages_text)
            if not full_text.strip():
                logger.warning("empty_pdf_extracted", title=title)
                full_text = "[Empty or Scanned PDF with no selectable text]"

            doc_title = title or (metadata.get("filename", "PDF Document") if metadata else "PDF Document")
            content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

            doc_meta = DocumentMetadata.from_dict(
                {"page_count": len(reader.pages), **(metadata or {})},
                source_system=source_system,
            )

            doc = Document(
                title=doc_title,
                content=full_text,
                document_type=DocumentType.PDF,
                metadata=doc_meta,
                content_hash=content_hash,
                token_count=len(full_text.split()),
            )
            return [doc]

        except Exception as exc:
            logger.error("pdf_parsing_failed", error=str(exc), title=title)
            raise IngestionError(f"Failed to parse PDF document: {exc}") from exc


class DOCXLoader(BaseLoader):
    """Loader for Microsoft Word (.docx) documents."""

    SUPPORTED_EXTENSIONS = {".docx", ".doc"}

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        ext = file_extension.lower() if file_extension.startswith(".") else f".{file_extension.lower()}"
        return ext in self.SUPPORTED_EXTENSIONS or (mime_type is not None and "wordprocessingml" in mime_type)

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> list[Document]:
        stream = _get_bytes_stream(source)
        try:
            doc_file = docx.Document(stream)
            paragraphs = [p.text.strip() for p in doc_file.paragraphs if p.text.strip()]
            full_text = "\n\n".join(paragraphs)

            doc_title = title or (metadata.get("filename", "DOCX Document") if metadata else "DOCX Document")
            content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()

            doc_meta = DocumentMetadata.from_dict(
                {"paragraph_count": len(paragraphs), **(metadata or {})},
                source_system=source_system,
            )

            doc = Document(
                title=doc_title,
                content=full_text,
                document_type=DocumentType.DOCX,
                metadata=doc_meta,
                content_hash=content_hash,
                token_count=len(full_text.split()),
            )
            return [doc]

        except Exception as exc:
            logger.error("docx_parsing_failed", error=str(exc), title=title)
            raise IngestionError(f"Failed to parse DOCX document: {exc}") from exc


def _get_bytes_stream(source: str | bytes | BinaryIO) -> io.BytesIO:
    """Helper to get a BytesIO stream from path, bytes, or file object."""
    if isinstance(source, str):
        import os
        if os.path.exists(source):
            with open(source, "rb") as f:
                return io.BytesIO(f.read())
        raise IngestionError(f"File path does not exist: {source}")
    elif isinstance(source, bytes):
        return io.BytesIO(source)
    elif hasattr(source, "read"):
        content = source.read()
        if isinstance(content, str):
            content = content.encode("utf-8")
        return io.BytesIO(content)
    raise IngestionError(f"Unsupported source type: {type(source)}")
