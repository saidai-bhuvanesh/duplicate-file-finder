"""
Query and QueryResult domain entities.

Represents a user query through its entire lifecycle from
initial input to final answered response.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.domain.entities.chunk import Chunk


class QueryType(str, Enum):
    """Classified type of user query — determines routing strategy."""

    FACTUAL = "factual"          # Who/What/When — use dense retrieval
    PROCEDURAL = "procedural"    # How-to — use semantic + BM25
    ANALYTICAL = "analytical"    # Compare/Analyze — multi-hop + graph
    DEBUGGING = "debugging"      # Error/Fix — code-aware retrieval
    ENTITY = "entity"            # Who is X, what is Y — graph-first
    CODE = "code"                # Code examples — code retrieval
    INCIDENT = "incident"        # Incident postmortem — specialized
    ARCHITECTURAL = "architectural"  # System design — graph + docs
    UNKNOWN = "unknown"


class RetrievalStrategy(str, Enum):
    """Retrieval strategy selected by the Adaptive Router."""

    BM25_ONLY = "bm25_only"
    DENSE_ONLY = "dense_only"
    HYBRID = "hybrid"
    HYBRID_RERANKED = "hybrid_reranked"
    GRAPH_RAG = "graph_rag"
    GRAPH_HYBRID = "graph_hybrid"
    MULTI_HOP = "multi_hop"
    PARENT_DOCUMENT = "parent_document"


class AnswerStatus(str, Enum):
    """Status of the answer generation pipeline."""

    PENDING = "pending"
    RETRIEVING = "retrieving"
    EVIDENCE_GATE_FAILED = "evidence_gate_failed"
    GENERATING = "generating"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass
class QueryExpansion:
    """Result of query expansion (HyDE + multi-query)."""

    original_query: str
    expanded_queries: list[str] = field(default_factory=list)
    hypothetical_document: str | None = None  # HyDE
    keywords: list[str] = field(default_factory=list)


@dataclass
class Query:
    """
    Represents a user query and all metadata accumulated during processing.

    This entity travels through the entire multi-agent pipeline and
    accumulates state at each stage.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    user_id: str | None = None
    session_id: str | None = None
    query_type: QueryType = QueryType.UNKNOWN
    retrieval_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID_RERANKED
    filters: dict[str, Any] = field(default_factory=dict)  # Metadata filters
    top_k: int = 5
    expansion: QueryExpansion | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            self.id = str(uuid.uuid4())


@dataclass
class RetrievedContext:
    """
    Represents the retrieved context before answer generation.

    Carries chunks, evidence scores, and explainability metadata.
    """

    query_id: str
    chunks: list[Chunk] = field(default_factory=list)
    strategy_used: RetrievalStrategy = RetrievalStrategy.HYBRID_RERANKED
    retrieval_latency_ms: float = 0.0
    reranking_latency_ms: float = 0.0
    total_candidates_retrieved: int = 0

    @property
    def top_chunks(self) -> list[Chunk]:
        """Return chunks sorted by final score descending."""
        return sorted(
            [c for c in self.chunks if c.final_score is not None],
            key=lambda c: c.final_score or 0.0,
            reverse=True,
        )

    @property
    def unique_document_ids(self) -> list[str]:
        """Return unique document IDs from retrieved chunks."""
        seen: set[str] = set()
        result = []
        for chunk in self.chunks:
            if chunk.document_id not in seen:
                seen.add(chunk.document_id)
                result.append(chunk.document_id)
        return result

    @property
    def context_text(self) -> str:
        """Concatenated context text for LLM prompt assembly."""
        parts = []
        for i, chunk in enumerate(self.top_chunks, 1):
            header = f"[Source {i}]"
            if chunk.section_title:
                header += f" {chunk.section_title}"
            parts.append(f"{header}\n{chunk.content}")
        return "\n\n---\n\n".join(parts)


@dataclass
class Citation:
    """A verifiable citation linking answer content to source evidence."""

    chunk_id: str
    document_id: str
    document_title: str
    source_url: str | None = None
    section_title: str | None = None
    page_number: int | None = None
    relevance_score: float = 0.0
    quote: str | None = None  # Verbatim quote from source
    section_path: str | None = None
    snippet: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "document_title": self.document_title,
            "source_url": self.source_url,
            "section_title": self.section_title,
            "page_number": self.page_number,
            "relevance_score": self.relevance_score,
            "quote": self.quote,
            "section_path": self.section_path,
            "snippet": self.snippet or self.quote or "",
        }


@dataclass
class QueryResult:
    """
    Final result returned to the user.

    Contains the answer, citations, confidence, and full explainability.
    """

    query_id: str
    query_text: str
    answer: str
    status: AnswerStatus
    citations: list[Citation] = field(default_factory=list)
    confidence_score: float = 0.0
    hallucination_risk: float = 0.0  # 0=none, 1=high
    strategy_used: RetrievalStrategy = RetrievalStrategy.HYBRID_RERANKED
    query_type: QueryType = QueryType.UNKNOWN

    # Explainability
    agent_trace: list[dict[str, Any]] = field(default_factory=list)
    retrieval_explanation: str | None = None
    evidence_quality: dict[str, float] = field(default_factory=dict)

    # Performance
    total_latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    total_tokens_used: int = 0
    estimated_cost_usd: float = 0.0

    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_sufficient_evidence(self) -> bool:
        """Return True if answer is backed by sufficient evidence."""
        return self.status == AnswerStatus.COMPLETED and self.confidence_score >= 0.5

    @property
    def source_count(self) -> int:
        """Number of unique sources cited."""
        return len({c.document_id for c in self.citations})
