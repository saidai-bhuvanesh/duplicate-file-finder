"""
Domain entities and Enums for Adaptive Retrieval Intelligence Engine (ARIE).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    DEFINITION = "definition"
    TROUBLESHOOTING = "troubleshooting"
    INCIDENT_ANALYSIS = "incident_analysis"
    CODE_SEARCH = "code_search"
    API_LOOKUP = "api_lookup"
    DESIGN_QUESTION = "design_question"
    ARCHITECTURE_QUESTION = "architecture_question"
    COMPARISON = "comparison"
    MULTI_HOP_REASONING = "multi_hop_reasoning"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    UNKNOWN = "unknown"


class QueryComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RequiredReasoning(str, Enum):
    SINGLE_DOCUMENT = "single_document"
    MULTI_DOCUMENT = "multi_document"
    MULTI_HOP = "multi_hop"
    GRAPH_TRAVERSAL = "graph_traversal"


class DataSourceType(str, Enum):
    CODE_REPOSITORY = "code_repository"
    DOCUMENTATION = "documentation"
    INCIDENT_REPORTS = "incident_reports"
    WIKI = "wiki"
    ARCHITECTURE_DOCS = "architecture_docs"
    SLACK = "slack"
    JIRA = "jira"
    GITHUB = "github"
    DATABASE_SCHEMA = "database_schema"


class FreshnessRequirement(str, Enum):
    HISTORICAL = "historical"
    RECENT = "recent"
    REAL_TIME = "real_time"


class RetrievalStrategyOption(str, Enum):
    BM25 = "bm25"
    DENSE_FAISS = "dense_faiss"
    HYBRID = "hybrid"
    HYBRID_RERANKED = "hybrid_reranked"
    GRAPHRAG = "graphrag"
    PARENT_RETRIEVAL = "parent_retrieval"
    CONTEXT_COMPRESSION = "context_compression"
    MULTI_QUERY = "multi_query"
    QUERY_EXPANSION = "query_expansion"
    HYDE_RETRIEVAL = "hyde_retrieval"
    EXTERNAL_SEARCH = "external_search"


class QueryIntelligenceResult(BaseModel):
    """Output of Step 1 Query Intelligence Classification."""

    query: str
    intent: QueryIntent
    complexity: QueryComplexity
    required_reasoning: RequiredReasoning
    target_data_sources: List[DataSourceType]
    freshness: FreshnessRequirement
    intent_scores: Dict[str, float] = Field(default_factory=dict)
    has_code_syntax: bool = False
    has_temporal_keywords: bool = False
    entity_references_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "intent": self.intent.value,
            "complexity": self.complexity.value,
            "required_reasoning": self.required_reasoning.value,
            "target_data_sources": [ds.value for ds in self.target_data_sources],
            "freshness": self.freshness.value,
            "intent_scores": self.intent_scores,
            "has_code_syntax": self.has_code_syntax,
            "has_temporal_keywords": self.has_temporal_keywords,
            "entity_references_count": self.entity_references_count,
        }


class RetrievalPolicyDecision(BaseModel):
    """Output of Step 2 Retrieval Policy Engine."""

    selected_strategy: RetrievalStrategyOption
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    expected_latency_ms: float
    estimated_cost_usd: float
    alternative_strategy: RetrievalStrategyOption
    why_not: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_strategy": self.selected_strategy.value,
            "reason": self.reason,
            "confidence": round(self.confidence, 4),
            "expected_latency_ms": round(self.expected_latency_ms, 2),
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "alternative_strategy": self.alternative_strategy.value,
            "why_not": self.why_not,
        }


class ARIEExplanation(BaseModel):
    """Output of Step 3 JSON Explanation Generator."""

    query: str
    intelligence: QueryIntelligenceResult
    decision: RetrievalPolicyDecision

    def to_json_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "selected_strategy": self.decision.selected_strategy.value,
            "reason": self.decision.reason,
            "confidence": round(self.decision.confidence, 4),
            "expected_latency": round(self.expected_latency_ms, 2),
            "expected_cost": round(self.decision.estimated_cost_usd, 6),
            "alternative_strategy": self.decision.alternative_strategy.value,
            "why_not": self.decision.why_not,
            "classification_details": self.intelligence.to_dict(),
        }

    @property
    def expected_latency_ms(self) -> float:
        return self.decision.expected_latency_ms


class ARIEBenchmarkSample(BaseModel):
    """Single query evaluation sample in 200-query benchmark."""

    sample_id: str
    query: str
    ground_truth_intent: QueryIntent
    ground_truth_strategy: RetrievalStrategyOption
    predicted_intent: QueryIntent
    selected_strategy: RetrievalStrategyOption
    accuracy_correct: bool
    precision_score: float
    latency_ms: float
    token_cost_usd: float
    hallucinated: bool


class ARIEBenchmarkReport(BaseModel):
    """Summary of 200-query benchmark execution."""

    total_samples: int
    classification_accuracy: float
    mean_precision: float
    mean_latency_ms: float
    total_token_cost_usd: float
    hallucination_rate: float
    baseline_comparisons: Dict[str, Dict[str, float]]
    intent_distribution: Dict[str, int]
    strategy_distribution: Dict[str, int]
