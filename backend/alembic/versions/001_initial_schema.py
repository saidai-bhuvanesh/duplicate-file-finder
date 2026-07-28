"""Initial schema — documents, chunks, ingestion jobs, query logs, evaluations.

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── documents ─────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("source_system", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("ingestion_job_id", sa.String(36), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("indexed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_source_system", "documents", ["source_system"])
    op.create_index("ix_documents_content_hash", "documents", ["content_hash"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])
    op.create_index("ix_documents_document_type", "documents", ["document_type"])

    # Full text search index on title
    op.execute(
        "CREATE INDEX ix_documents_title_fts ON documents USING gin(to_tsvector('english', title))"
    )

    # ── ingestion_jobs ────────────────────────────────────────────────────────
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_path", sa.String(2000), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_files", sa.Integer, nullable=False, server_default="0"),
        sa.Column("processed_files", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_files", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_chunks", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(255), nullable=True),
    )
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])
    op.create_index("ix_ingestion_jobs_created_at", "ingestion_jobs", ["created_at"])

    # ── chunks ────────────────────────────────────────────────────────────────
    op.create_table(
        "chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("chunk_type", sa.String(30), nullable=False, server_default="recursive"),
        sa.Column("chunk_index", sa.Integer, nullable=False, server_default="0"),
        sa.Column("start_char", sa.Integer, nullable=False, server_default="0"),
        sa.Column("end_char", sa.Integer, nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("page_number", sa.Integer, nullable=True),
        sa.Column("section_title", sa.String(500), nullable=True),
        sa.Column("section_path", sa.String(1000), nullable=True),
        sa.Column(
            "parent_chunk_id",
            sa.String(36),
            sa.ForeignKey("chunks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])
    op.create_index("ix_chunks_chunk_index", "chunks", ["chunk_index"])
    op.create_index("ix_chunks_parent_chunk_id", "chunks", ["parent_chunk_id"])

    # ── query_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "query_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("query_text", sa.Text, nullable=False),
        sa.Column("query_type", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("retrieval_strategy", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("answer", sa.Text, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("hallucination_risk", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("evidence_quality", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("citations", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("agent_trace", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("filters_applied", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("total_latency_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("retrieval_latency_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("llm_latency_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("total_tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("feedback_rating", sa.Integer, nullable=True),
        sa.Column("feedback_comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_query_logs_user_id", "query_logs", ["user_id"])
    op.create_index("ix_query_logs_created_at", "query_logs", ["created_at"])
    op.create_index("ix_query_logs_status", "query_logs", ["status"])
    op.create_index("ix_query_logs_query_type", "query_logs", ["query_type"])

    # ── evaluation_runs ───────────────────────────────────────────────────────
    op.create_table(
        "evaluation_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("rag_variant", sa.String(50), nullable=False),
        sa.Column("dataset_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sample_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retrieval_metrics", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("generation_metrics", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("performance_metrics", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("config", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evaluation_runs_rag_variant", "evaluation_runs", ["rag_variant"])
    op.create_index("ix_evaluation_runs_status", "evaluation_runs", ["status"])

    # ── evaluation_samples ────────────────────────────────────────────────────
    op.create_table(
        "evaluation_samples",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question", sa.Text, nullable=False),
        sa.Column("ground_truth_answer", sa.Text, nullable=False),
        sa.Column("generated_answer", sa.Text, nullable=False, server_default=""),
        sa.Column("ground_truth_contexts", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("retrieved_contexts", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("citations", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("faithfulness", sa.Float, nullable=True),
        sa.Column("context_recall", sa.Float, nullable=True),
        sa.Column("context_precision", sa.Float, nullable=True),
        sa.Column("hallucination_detected", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("latency_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evaluation_samples_run_id", "evaluation_samples", ["run_id"])


def downgrade() -> None:
    op.drop_table("evaluation_samples")
    op.drop_table("evaluation_runs")
    op.drop_table("query_logs")
    op.drop_table("chunks")
    op.drop_table("ingestion_jobs")
    op.drop_table("documents")
