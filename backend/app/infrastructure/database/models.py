"""
SQLAlchemy ORM models for EnterpriseIT-RAG.

All tables are defined here and referenced by Alembic migrations.
Uses PostgreSQL-specific types (JSONB, UUID, ARRAY) for production performance.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base


def _uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class DocumentModel(Base):
    """Stores raw document metadata and ingestion status."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_status", "status"),
        Index("ix_documents_source_system", "source_system"),
        Index("ix_documents_content_hash", "content_hash"),
        Index("ix_documents_created_at", "created_at"),
        Index("ix_documents_document_type", "document_type"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    title: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    ingestion_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    chunks: Mapped[list[ChunkModel]] = relationship(
        "ChunkModel", back_populates="document", cascade="all, delete-orphan"
    )
    ingestion_job: Mapped[IngestionJobModel | None] = relationship(
        "IngestionJobModel", back_populates="documents", foreign_keys=[ingestion_job_id],
        primaryjoin="DocumentModel.ingestion_job_id == IngestionJobModel.id",
    )

    def __repr__(self) -> str:
        return f"<DocumentModel id={self.id!r} title={self.title!r} status={self.status!r}>"


class ChunkModel(Base):
    """Stores individual document chunks with metadata for retrieval."""

    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_document_id", "document_id"),
        Index("ix_chunks_chunk_index", "chunk_index"),
        Index("ix_chunks_parent_chunk_id", "parent_chunk_id"),
        Index("ix_chunks_section_title", "section_title"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String(30), nullable=False, default="recursive")
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_char: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    end_char: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    section_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    parent_chunk_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("chunks.id", ondelete="SET NULL"), nullable=True
    )
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    document: Mapped[DocumentModel] = relationship("DocumentModel", back_populates="chunks")
    parent_chunk: Mapped[ChunkModel | None] = relationship(
        "ChunkModel", remote_side="ChunkModel.id"
    )

    def __repr__(self) -> str:
        preview = self.content[:50].replace("\n", " ")
        return f"<ChunkModel id={self.id!r} doc={self.document_id!r} idx={self.chunk_index} preview={preview!r}>"


class IngestionJobModel(Base):
    """Tracks async ingestion job status."""

    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        Index("ix_ingestion_jobs_status", "status"),
        Index("ix_ingestion_jobs_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    source_path: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    documents: Mapped[list[DocumentModel]] = relationship(
        "DocumentModel",
        primaryjoin="IngestionJobModel.id == foreign(DocumentModel.ingestion_job_id)",
        back_populates="ingestion_job",
        viewonly=True,
    )


class QueryLogModel(Base):
    """Stores every query for analytics, evaluation, and debugging."""

    __tablename__ = "query_logs"
    __table_args__ = (
        Index("ix_query_logs_user_id", "user_id"),
        Index("ix_query_logs_created_at", "created_at"),
        Index("ix_query_logs_status", "status"),
        Index("ix_query_logs_query_type", "query_type"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_type: Mapped[str] = mapped_column(String(30), nullable=False, default="unknown")
    retrieval_strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    hallucination_risk: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_quality: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    agent_trace: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    filters_applied: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    total_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    retrieval_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    llm_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    feedback_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class EvaluationRunModel(Base):
    """Stores evaluation run metadata and aggregated metrics."""

    __tablename__ = "evaluation_runs"
    __table_args__ = (
        Index("ix_evaluation_runs_rag_variant", "rag_variant"),
        Index("ix_evaluation_runs_status", "status"),
        Index("ix_evaluation_runs_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    rag_variant: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    retrieval_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generation_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    performance_metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    samples: Mapped[list[EvaluationSampleModel]] = relationship(
        "EvaluationSampleModel", back_populates="run", cascade="all, delete-orphan"
    )


class EvaluationSampleModel(Base):
    """Stores individual evaluation samples."""

    __tablename__ = "evaluation_samples"
    __table_args__ = (
        Index("ix_evaluation_samples_run_id", "run_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    ground_truth_answer: Mapped[str] = mapped_column(Text, nullable=False)
    generated_answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ground_truth_contexts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    retrieved_contexts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    citations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    faithfulness: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    hallucination_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # Relationships
    run: Mapped[EvaluationRunModel] = relationship("EvaluationRunModel", back_populates="samples")
