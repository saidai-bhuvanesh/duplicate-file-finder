"""
Atlassian Confluence and Jira document loaders.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, BinaryIO

from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
from app.ingestion.loaders.base import BaseLoader

logger = get_logger(__name__, component="atlassian_loader")


class ConfluenceLoader(BaseLoader):
    """Loader for Confluence space pages or exported Confluence HTML/JSON."""

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        return False  # Invoked explicitly by registry for source_system == CONFLUENCE

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.CONFLUENCE,
    ) -> list[Document]:
        meta = metadata or {}
        raw_content = _read_as_text(source)

        # Parse HTML if Confluence page storage format / export HTML
        if "<html" in raw_content.lower() or "<p>" in raw_content.lower() or "<div" in raw_content.lower():
            soup = BeautifulSoup(raw_content, "lxml")
            for tag in soup(["script", "style", "nav"]):
                tag.decompose()
            clean_text = soup.get_text(separator="\n\n").strip()
            page_title = title or (soup.title.string.strip() if soup.title and soup.title.string else meta.get("title", "Confluence Page"))
        else:
            clean_text = raw_content.strip()
            page_title = title or meta.get("title", "Confluence Page")

        content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

        doc_meta = DocumentMetadata.from_dict(meta, source_system=SourceSystem.CONFLUENCE)

        return [
            Document(
                title=page_title,
                content=clean_text,
                document_type=DocumentType.CONFLUENCE,
                metadata=doc_meta,
                content_hash=content_hash,
                token_count=len(clean_text.split()),
            )
        ]


class JiraLoader(BaseLoader):
    """Loader for Jira issues/tickets or Jira export JSON."""

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        return False  # Invoked explicitly by registry for source_system == JIRA

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.JIRA,
    ) -> list[Document]:
        meta = metadata or {}
        raw_text = _read_as_text(source)

        try:
            data = json.loads(raw_text)
            if isinstance(data, dict):
                key = data.get("key") or meta.get("ticket_key", "JIRA-TICKET")
                summary = data.get("summary") or data.get("fields", {}).get("summary", "")
                description = data.get("description") or data.get("fields", {}).get("description", "")
                comments = data.get("comments") or data.get("fields", {}).get("comment", {}).get("comments", [])

                comment_texts = []
                for c in comments:
                    author = c.get("author", {}).get("displayName", "User")
                    body = c.get("body", "")
                    comment_texts.append(f"Comment by {author}:\n{body}")

                full_content = f"Ticket Key: {key}\nSummary: {summary}\n\nDescription:\n{description}\n\nComments:\n" + "\n---\n".join(comment_texts)
                page_title = title or f"Jira Ticket [{key}]: {summary}"
                ticket_key = key
            else:
                full_content = raw_text
                page_title = title or "Jira Document"
                ticket_key = meta.get("ticket_key")
        except Exception:
            full_content = raw_text
            page_title = title or "Jira Document"
            ticket_key = meta.get("ticket_key")

        content_hash = hashlib.sha256(full_content.encode("utf-8")).hexdigest()

        doc_meta = DocumentMetadata.from_dict(
            {"ticket_key": ticket_key, **meta},
            source_system=SourceSystem.JIRA,
        )

        return [
            Document(
                title=page_title,
                content=full_content,
                document_type=DocumentType.JIRA,
                metadata=doc_meta,
                content_hash=content_hash,
                token_count=len(full_content.split()),
            )
        ]


def _read_as_text(source: str | bytes | BinaryIO) -> str:
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
