"""
Loader Registry for automatic document loader selection and dispatch.
"""

from __future__ import annotations

import os
from typing import Any, BinaryIO

from app.core.exceptions import UnsupportedDocumentTypeError
from app.core.logging import get_logger
from app.domain.entities.document import Document, SourceSystem
from app.ingestion.loaders.atlassian_loader import ConfluenceLoader, JiraLoader
from app.ingestion.loaders.base import BaseLoader
from app.ingestion.loaders.code_loader import CodeLoader
from app.ingestion.loaders.github_loader import GitHubLoader
from app.ingestion.loaders.notion_loader import NotionLoader
from app.ingestion.loaders.pdf_docx_loader import DOCXLoader, PDFLoader
from app.ingestion.loaders.slack_teams_loader import SlackTeamsLoader
from app.ingestion.loaders.text_loader import HTMLLoader, StructuredDataLoader, TextLoader

logger = get_logger(__name__, component="loader_registry")


class LoaderRegistry:
    """
    Central registry for auto-selecting and dispatching loaders.
    """

    def __init__(self) -> None:
        self.loaders: list[BaseLoader] = [
            PDFLoader(),
            DOCXLoader(),
            CodeLoader(),
            HTMLLoader(),
            StructuredDataLoader(),
            TextLoader(),  # TextLoader acts as a fallback for plain text / MD
        ]
        # System-specific loaders
        self.system_loaders: dict[SourceSystem, BaseLoader] = {
            SourceSystem.CONFLUENCE: ConfluenceLoader(),
            SourceSystem.JIRA: JiraLoader(),
            SourceSystem.GITHUB: GitHubLoader(),
            SourceSystem.SLACK: SlackTeamsLoader(),
            SourceSystem.TEAMS: SlackTeamsLoader(),
            SourceSystem.NOTION: NotionLoader(),
        }

    def get_loader_for_source(
        self,
        source: str | bytes | BinaryIO,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> BaseLoader:
        """
        Determine appropriate loader for given source or system.
        """
        # 1. System-specific loader
        if source_system in self.system_loaders:
            return self.system_loaders[source_system]

        meta = metadata or {}
        filename = meta.get("filename", "")
        file_ext = meta.get("file_extension") or (os.path.splitext(filename)[1] if filename else "")

        if not file_ext and isinstance(source, str) and os.path.isfile(source):
            file_ext = os.path.splitext(source)[1]

        mime_type = meta.get("mime_type")

        # 2. Iterate supported extension loaders
        for loader in self.loaders:
            if loader.supports(file_ext, mime_type):
                return loader

        # Fallback to TextLoader if readable text
        return TextLoader()

    async def load_document(
        self,
        source: str | bytes | BinaryIO,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> list[Document]:
        """Auto-detect loader and load document(s)."""
        loader = self.get_loader_for_source(source, metadata, source_system)
        logger.info(
            "loader_selected",
            loader_type=type(loader).__name__,
            title=title,
            source_system=source_system.value,
        )
        return await loader.load(
            source=source,
            title=title,
            metadata=metadata,
            source_system=source_system,
        )


# Global singleton instance
_registry = LoaderRegistry()


def get_loader_registry() -> LoaderRegistry:
    return _registry
