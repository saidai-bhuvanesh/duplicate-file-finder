"""
Slack and Microsoft Teams message exports document loader.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, BinaryIO

from app.core.logging import get_logger
from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
from app.ingestion.loaders.base import BaseLoader

logger = get_logger(__name__, component="slack_teams_loader")


class SlackTeamsLoader(BaseLoader):
    """Loader for Slack and MS Teams JSON channel message exports."""

    def supports(self, file_extension: str, mime_type: str | None = None) -> bool:
        return False  # Triggered explicitly or by registry

    async def load(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.SLACK,
    ) -> list[Document]:
        meta = metadata or {}
        raw_text = _read_text(source)
        channel = meta.get("channel", "general")
        doc_type = DocumentType.SLACK_EXPORT if source_system == SourceSystem.SLACK else DocumentType.TEAMS_EXPORT

        try:
            messages = json.loads(raw_text)
            if isinstance(messages, list):
                formatted_msgs = []
                for msg in messages:
                    user = msg.get("user") or msg.get("user_profile", {}).get("real_name") or msg.get("from", {}).get("user", {}).get("displayName", "User")
                    text = msg.get("text") or msg.get("body", {}).get("content", "")
                    ts = msg.get("ts") or msg.get("createdDateTime", "")
                    if text.strip():
                        formatted_msgs.append(f"[{ts}] {user}: {text.strip()}")
                full_content = f"Channel #{channel} Export:\n\n" + "\n".join(formatted_msgs)
            else:
                full_content = raw_text
        except Exception:
            full_content = raw_text

        doc_title = title or f"{source_system.value.upper()} Export: #{channel}"
        content_hash = hashlib.sha256(full_content.encode("utf-8")).hexdigest()

        doc_meta = DocumentMetadata.from_dict(
            {"channel": channel, **meta},
            source_system=source_system,
        )

        return [
            Document(
                title=doc_title,
                content=full_content,
                document_type=doc_type,
                metadata=doc_meta,
                content_hash=content_hash,
                token_count=len(full_content.split()),
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
