"""
Document domain entity.

Represents a raw document ingested from any source system.
This is a pure domain entity — no ORM or framework dependencies.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class DocumentStatus(str, Enum):
    """Lifecycle status of a document through the ingestion pipeline."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    ARCHIVED = "archived"


class DocumentType(str, Enum):
    """Supported document types."""

    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "markdown"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    TEXT = "text"
    CODE = "code"
    YAML = "yaml"
    OPENAPI = "openapi"
    CONFLUENCE = "confluence"
    JIRA = "jira"
    NOTION = "notion"
    GITHUB_ISSUE = "github_issue"
    GITHUB_PR = "github_pr"
    GITHUB_README = "github_readme"
    SLACK_EXPORT = "slack_export"
    TEAMS_EXPORT = "teams_export"
    RUNBOOK = "runbook"
    INCIDENT = "incident"
    ARCHITECTURE = "architecture"
    TERRAFORM = "terraform"
    KUBERNETES = "kubernetes"
    DOCKER = "docker"


class SourceSystem(str, Enum):
    """Source system from which the document was ingested."""

    LOCAL_FILE = "local_file"
    CONFLUENCE = "confluence"
    JIRA = "jira"
    GITHUB = "github"
    GITLAB = "gitlab"
    NOTION = "notion"
    SHAREPOINT = "sharepoint"
    SLACK = "slack"
    TEAMS = "teams"
    REST_API = "rest_api"
    S3 = "s3"
    GCS = "gcs"
    AZURE_BLOB = "azure_blob"


@dataclass
class DocumentMetadata:
    """
    Rich metadata attached to a document.

    Enables metadata filtering during retrieval, version-aware search,
    and source attribution in citations.
    """

    source_system: SourceSystem
    source_url: str | None = None
    source_path: str | None = None
    author: str | None = None
    authors: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: str | None = None
    language: str = "en"
    tags: list[str] = field(default_factory=list)
    project: str | None = None
    team: str | None = None
    repository: str | None = None
    branch: str | None = None
    commit_hash: str | None = None
    space: str | None = None       # Confluence space
    page_id: str | None = None     # Confluence page ID
    ticket_key: str | None = None  # Jira ticket key
    channel: str | None = None     # Slack channel
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata for storage in PostgreSQL JSONB."""
        return {
            "source_system": self.source_system.value,
            "source_url": self.source_url,
            "source_path": self.source_path,
            "author": self.author,
            "authors": self.authors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "version": self.version,
            "language": self.language,
            "tags": self.tags,
            "project": self.project,
            "team": self.team,
            "repository": self.repository,
            "branch": self.branch,
            "commit_hash": self.commit_hash,
            "space": self.space,
            "page_id": self.page_id,
            "ticket_key": self.ticket_key,
            "channel": self.channel,
            **self.extra,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None = None,
        source_system: SourceSystem = SourceSystem.LOCAL_FILE,
    ) -> DocumentMetadata:
        """Safely construct DocumentMetadata from an arbitrary dictionary."""
        d = dict(data or {})
        sys = d.pop("source_system", None)
        if sys:
            if isinstance(sys, SourceSystem):
                source_system = sys
            elif isinstance(sys, str):
                try:
                    source_system = SourceSystem(sys)
                except ValueError:
                    pass

        known_fields = {
            "source_url", "source_path", "author", "authors", "created_at", "updated_at",
            "version", "language", "tags", "project", "team", "repository", "branch",
            "commit_hash", "space", "page_id", "ticket_key", "channel",
        }

        init_kwargs: dict[str, Any] = {"source_system": source_system}
        extra_kwargs: dict[str, Any] = {}

        for k, v in d.items():
            if k in known_fields:
                init_kwargs[k] = v
            else:
                extra_kwargs[k] = v

        if "extra" in d and isinstance(d["extra"], dict):
            extra_kwargs.update(d["extra"])

        init_kwargs["extra"] = extra_kwargs
        return cls(**init_kwargs)


@dataclass
class Document:
    """
    Core document entity.

    Represents a single document from any source system, after parsing
    but before chunking. Contains raw text and rich metadata.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    content: str = ""
    document_type: DocumentType = DocumentType.TEXT
    status: DocumentStatus = DocumentStatus.PENDING
    metadata: DocumentMetadata = field(
        default_factory=lambda: DocumentMetadata(source_system=SourceSystem.LOCAL_FILE)
    )
    content_hash: str = ""       # SHA-256 or xxhash of content (for dedup)
    chunk_count: int = 0
    token_count: int = 0
    ingestion_job_id: str | None = None
    error_message: str | None = None
    indexed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())

    def mark_processing(self) -> None:
        """Transition document to processing state."""
        self.status = DocumentStatus.PROCESSING
        self.updated_at = datetime.utcnow()

    def mark_indexed(self, chunk_count: int) -> None:
        """Transition document to indexed state after successful ingestion."""
        self.status = DocumentStatus.INDEXED
        self.chunk_count = chunk_count
        self.indexed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.error_message = None

    def mark_failed(self, error: str) -> None:
        """Transition document to failed state with error message."""
        self.status = DocumentStatus.FAILED
        self.error_message = error
        self.updated_at = datetime.utcnow()

    @property
    def is_indexed(self) -> bool:
        """Return True if document has been successfully indexed."""
        return self.status == DocumentStatus.INDEXED

    @property
    def word_count(self) -> int:
        """Approximate word count from content."""
        return len(self.content.split())

    def __repr__(self) -> str:
        return (
            f"Document(id={self.id!r}, title={self.title!r}, "
            f"type={self.document_type.value!r}, status={self.status.value!r})"
        )
