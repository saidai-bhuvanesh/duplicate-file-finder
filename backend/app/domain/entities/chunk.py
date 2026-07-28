"""
Chunk domain entity.

A Chunk is a segment of a Document after it has been split into
retrievable pieces by the chunking pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ChunkType(str, Enum):
    """The chunking strategy that produced this chunk."""

    SEMANTIC = "semantic"
    RECURSIVE = "recursive"
    FIXED_SIZE = "fixed_size"
    CODE = "code"
    PARENT = "parent"
    SENTENCE = "sentence"


@dataclass
class Chunk:
    """
    A retrievable chunk of a document.

    Each chunk carries:
    - Its own text content and position metadata
    - A reference to the parent document
    - An optional embedding vector (stored in FAISS)
    - Filtering metadata for retrieval
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    content: str = ""
    chunk_type: ChunkType = ChunkType.RECURSIVE
    chunk_index: int = 0          # Position within parent document
    start_char: int = 0           # Character offset in original document
    end_char: int = 0
    token_count: int = 0
    page_number: int | None = None
    section_title: str | None = None
    section_path: str | None = None   # e.g. "Design > Architecture > Microservices"
    parent_chunk_id: str | None = None  # For parent-document retrieval
    embedding: list[float] | None = None  # Dense vector (stored in FAISS)
    embedding_model: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Retrieval scores (populated at query time, not stored)
    bm25_score: float | None = None
    dense_score: float | None = None
    rerank_score: float | None = None
    final_score: float | None = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())

    @property
    def char_length(self) -> int:
        """Character length of the chunk content."""
        return len(self.content)

    @property
    def has_embedding(self) -> bool:
        """Return True if this chunk has been embedded."""
        return self.embedding is not None and len(self.embedding) > 0

    def to_retrieval_dict(self) -> dict[str, Any]:
        """
        Return a dict suitable for retrieval context.

        This is what the agents receive to construct answers.
        Does NOT include the embedding vector.
        """
        return {
            "chunk_id": self.id,
            "document_id": self.document_id,
            "content": self.content,
            "section_title": self.section_title,
            "section_path": self.section_path,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
            "scores": {
                "bm25": self.bm25_score,
                "dense": self.dense_score,
                "rerank": self.rerank_score,
                "final": self.final_score,
            },
        }

    def __repr__(self) -> str:
        preview = self.content[:60].replace("\n", " ")
        return (
            f"Chunk(id={self.id!r}, doc={self.document_id!r}, "
            f"idx={self.chunk_index}, preview={preview!r}...)"
        )
