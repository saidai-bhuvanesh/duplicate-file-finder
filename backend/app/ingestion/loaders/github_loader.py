"""
GitHub Repositories, Issues, and Pull Requests document loader.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, BinaryIO

from app.core.logging import get_logger
from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
from app.ingestion.loaders.base import BaseLoader

logger = get_logger(__name__, component="github_loader")


class GitHubLoader(BaseLoader):
    """
    Loader for GitHub items:
    - Repository source files / READMEs
    - GitHub Issues JSON / raw
    - GitHub Pull Requests JSON / raw
    """

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        return False  # Triggered explicitly by registry for source_system == GITHUB

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.GITHUB,
    ) -> list[Document]:
        meta = metadata or {}
        raw_text = _read_text(source)
        item_type = meta.get("item_type", "file")  # issue, pr, readme, code

        if item_type in ("issue", "github_issue"):
            return [self._parse_issue(raw_text, title, meta)]
        elif item_type in ("pr", "pull_request", "github_pr"):
            return [self._parse_pr(raw_text, title, meta)]
        else:
            return [self._parse_file(raw_text, title, meta)]

    def _parse_issue(self, raw_text: str, title: str | None, meta: dict[str, Any]) -> Document:
        try:
            data = json.loads(raw_text)
            number = data.get("number")
            issue_title = data.get("title", "")
            body = data.get("body", "")
            comments = data.get("comments_data", [])

            comment_str = "\n---\n".join(
                f"Comment by {c.get('user', {}).get('login', 'user')}:\n{c.get('body', '')}"
                for c in comments
            )
            full_content = f"Issue #{number}: {issue_title}\n\nBody:\n{body}\n\nComments:\n{comment_str}"
            doc_title = title or f"GitHub Issue #{number}: {issue_title}"
        except Exception:
            full_content = raw_text
            doc_title = title or "GitHub Issue"

        content_hash = hashlib.sha256(full_content.encode("utf-8")).hexdigest()
        doc_meta = DocumentMetadata.from_dict(meta, source_system=SourceSystem.GITHUB)

        return Document(
            title=doc_title,
            content=full_content,
            document_type=DocumentType.GITHUB_ISSUE,
            metadata=doc_meta,
            content_hash=content_hash,
            token_count=len(full_content.split()),
        )

    def _parse_pr(self, raw_text: str, title: str | None, meta: dict[str, Any]) -> Document:
        try:
            data = json.loads(raw_text)
            number = data.get("number")
            pr_title = data.get("title", "")
            body = data.get("body", "")
            full_content = f"Pull Request #{number}: {pr_title}\n\nBody:\n{body}"
            doc_title = title or f"GitHub PR #{number}: {pr_title}"
        except Exception:
            full_content = raw_text
            doc_title = title or "GitHub Pull Request"

        content_hash = hashlib.sha256(full_content.encode("utf-8")).hexdigest()
        doc_meta = DocumentMetadata.from_dict(meta, source_system=SourceSystem.GITHUB)

        return Document(
            title=doc_title,
            content=full_content,
            document_type=DocumentType.GITHUB_PR,
            metadata=doc_meta,
            content_hash=content_hash,
            token_count=len(full_content.split()),
        )

    def _parse_file(self, raw_text: str, title: str | None, meta: dict[str, Any]) -> Document:
        filename = meta.get("filename", "File")
        doc_title = title or f"GitHub File: {filename}"
        doc_type = DocumentType.GITHUB_README if filename.lower().startswith("readme") else DocumentType.CODE

        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        doc_meta = DocumentMetadata.from_dict(meta, source_system=SourceSystem.GITHUB)

        return Document(
            title=doc_title,
            content=raw_text,
            document_type=doc_type,
            metadata=doc_meta,
            content_hash=content_hash,
            token_count=len(raw_text.split()),
        )


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
