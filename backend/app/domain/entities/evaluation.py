"""
Evaluation domain entities.

Represents evaluation runs, metrics, and benchmark comparisons
for the enterprise RAG evaluation framework.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RAGVariant(str, Enum):
    """RAG system variant being evaluated."""

    NAIVE_RAG = "naive_rag"
    HYBRID_RAG = "hybrid_rag"
    GRAPH_RAG = "graph_rag"
    ADAPTIVE_ENTERPRISE_RAG = "adaptive_enterprise_rag"


class EvaluationStatus(str, Enum):
    """Status of an evaluation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RetrievalMetrics:
    """Retrieval quality metrics."""

    precision_at_5: float = 0.0
    recall_at_5: float = 0.0
    mrr: float = 0.0          # Mean Reciprocal Rank
    ndcg_at_5: float = 0.0    # nDCG@5

    def to_dict(self) -> dict[str, float]:
        return {
            "precision_at_5": self.precision_at_5,
            "recall_at_5": self.recall_at_5,
            "mrr": self.mrr,
            "ndcg_at_5": self.ndcg_at_5,
        }


@dataclass
class GenerationMetrics:
    """Answer generation quality metrics."""

    answer_faithfulness: float = 0.0      # RAGAS: answer grounded in context
    context_recall: float = 0.0           # RAGAS: context covers answer
    context_precision: float = 0.0        # RAGAS: context is precise
    groundedness: float = 0.0             # Claims traceable to evidence
    citation_accuracy: float = 0.0        # Citations are correct
    hallucination_rate: float = 0.0       # Rate of unsupported claims
    enterprise_task_success: float = 0.0  # Task completion rate

    def to_dict(self) -> dict[str, float]:
        return {
            "answer_faithfulness": self.answer_faithfulness,
            "context_recall": self.context_recall,
            "context_precision": self.context_precision,
            "groundedness": self.groundedness,
            "citation_accuracy": self.citation_accuracy,
            "hallucination_rate": self.hallucination_rate,
            "enterprise_task_success": self.enterprise_task_success,
        }


@dataclass
class PerformanceMetrics:
    """System performance metrics."""

    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    avg_tokens_per_query: float = 0.0
    avg_cost_per_query_usd: float = 0.0
    total_cost_usd: float = 0.0
    queries_per_second: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            "avg_latency_ms": self.avg_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "avg_tokens_per_query": self.avg_tokens_per_query,
            "avg_cost_per_query_usd": self.avg_cost_per_query_usd,
            "total_cost_usd": self.total_cost_usd,
            "queries_per_second": self.queries_per_second,
        }


@dataclass
class EvaluationSample:
    """A single evaluation sample (question + ground truth + generated answer)."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question: str = ""
    ground_truth_answer: str = ""
    ground_truth_contexts: list[str] = field(default_factory=list)
    generated_answer: str = ""
    retrieved_contexts: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)

    # Per-sample metrics
    faithfulness: float | None = None
    context_recall: float | None = None
    context_precision: float | None = None
    hallucination_detected: bool = False

    latency_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0


@dataclass
class EvaluationRun:
    """
    An evaluation run comparing a RAG variant against a test dataset.

    One EvaluationRun = one variant × one dataset.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    rag_variant: RAGVariant = RAGVariant.ADAPTIVE_ENTERPRISE_RAG
    dataset_name: str = ""
    status: EvaluationStatus = EvaluationStatus.PENDING
    samples: list[EvaluationSample] = field(default_factory=list)
    retrieval_metrics: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    generation_metrics: GenerationMetrics = field(default_factory=GenerationMetrics)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        """Duration of the evaluation run in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def sample_count(self) -> int:
        return len(self.samples)
