"""
Retrieval Policy Engine (Step 2 of ARIE).

Selects the optimal retrieval policy out of 11 candidate strategies:
- BM25
- DENSE_FAISS
- HYBRID
- HYBRID_RERANKED
- GRAPHRAG
- PARENT_RETRIEVAL
- CONTEXT_COMPRESSION
- MULTI_QUERY
- QUERY_EXPANSION
- HYDE_RETRIEVAL
- EXTERNAL_SEARCH

Calculates expected latency, token cost, confidence score, and alternative strategy rationale.
"""

from __future__ import annotations

from typing import Dict, Tuple

from app.core.logging import get_logger
from app.domain.entities.arie import (
    QueryComplexity,
    QueryIntelligenceResult,
    QueryIntent,
    RequiredReasoning,
    RetrievalPolicyDecision,
    RetrievalStrategyOption,
)

logger = get_logger(__name__, component="policy_engine")


class RetrievalPolicyEngine:
    """
    Policy engine mapping multi-dimensional query intelligence to retrieval strategies.
    """

    STRATEGY_METRICS: Dict[RetrievalStrategyOption, Tuple[float, float]] = {
        # Strategy: (Latency_ms, Cost_USD)
        RetrievalStrategyOption.BM25: (15.0, 0.00002),
        RetrievalStrategyOption.DENSE_FAISS: (25.0, 0.00005),
        RetrievalStrategyOption.HYBRID: (38.0, 0.00010),
        RetrievalStrategyOption.HYBRID_RERANKED: (85.0, 0.00025),
        RetrievalStrategyOption.GRAPHRAG: (180.0, 0.00045),
        RetrievalStrategyOption.PARENT_RETRIEVAL: (60.0, 0.00018),
        RetrievalStrategyOption.CONTEXT_COMPRESSION: (110.0, 0.00030),
        RetrievalStrategyOption.MULTI_QUERY: (150.0, 0.00050),
        RetrievalStrategyOption.QUERY_EXPANSION: (130.0, 0.00040),
        RetrievalStrategyOption.HYDE_RETRIEVAL: (220.0, 0.00065),
        RetrievalStrategyOption.EXTERNAL_SEARCH: (350.0, 0.00085),
    }

    def select_policy(self, intel: QueryIntelligenceResult) -> RetrievalPolicyDecision:
        """
        Evaluate query intelligence features and decide optimal retrieval policy.
        """
        intent = intel.intent
        complexity = intel.complexity
        reasoning = intel.required_reasoning

        selected: RetrievalStrategyOption
        alternative: RetrievalStrategyOption
        reason: str
        why_not: str
        confidence: float

        # Rule 1: Graph Traversal / Incident & Multi-Hop Reasoning
        if intent in (QueryIntent.INCIDENT_ANALYSIS, QueryIntent.MULTI_HOP_REASONING) or reasoning == RequiredReasoning.GRAPH_TRAVERSAL:
            selected = RetrievalStrategyOption.GRAPHRAG
            alternative = RetrievalStrategyOption.HYBRID_RERANKED
            reason = "Query requires multi-hop relational graph traversal across IT entities (Service, Team, Incident, Repository)."
            why_not = "Hybrid vector search lacks explicit directional relationship links required for multi-hop graph traversal."
            confidence = 0.94

        # Rule 2: API Lookup & Code Search
        elif intent in (QueryIntent.API_LOOKUP, QueryIntent.CODE_SEARCH) or intel.has_code_syntax:
            selected = RetrievalStrategyOption.PARENT_RETRIEVAL
            alternative = RetrievalStrategyOption.BM25
            reason = "Query searches for exact code/API signatures requiring full enclosing parent context for complete code blocks."
            why_not = "Flat BM25 search returns isolated lines missing surrounding function or class definitions."
            confidence = 0.91

        # Rule 3: Root Cause Analysis
        elif intent == QueryIntent.ROOT_CAUSE_ANALYSIS:
            selected = RetrievalStrategyOption.MULTI_QUERY
            alternative = RetrievalStrategyOption.HYDE_RETRIEVAL
            reason = "Root cause analysis benefits from multi-query perspective decomposition to cover diverse failure vectors."
            why_not = "HyDE hypothetical document generation introduces speculative hallucination risks for failure analysis."
            confidence = 0.89

        # Rule 4: Architecture & Design Questions
        elif intent in (QueryIntent.ARCHITECTURE_QUESTION, QueryIntent.DESIGN_QUESTION):
            selected = RetrievalStrategyOption.HYDE_RETRIEVAL
            alternative = RetrievalStrategyOption.QUERY_EXPANSION
            reason = "Abstract architectural or design query benefits from Hypothetical Document Embeddings (HyDE) to bridge concept gaps."
            why_not = "Query expansion expands terminology but may not generate dense synthetic reference structures."
            confidence = 0.88

        # Rule 5: Comparative Analysis
        elif intent == QueryIntent.COMPARISON:
            selected = RetrievalStrategyOption.CONTEXT_COMPRESSION
            alternative = RetrievalStrategyOption.HYBRID_RERANKED
            reason = "Comparative queries span multiple documents; context compression extracts key comparison vectors cleanly."
            why_not = "Hybrid reranking includes redundant text boilerplate across competing documents."
            confidence = 0.87

        # Rule 6: Factual Definitions
        elif intent == QueryIntent.DEFINITION:
            if complexity == QueryComplexity.LOW:
                selected = RetrievalStrategyOption.DENSE_FAISS
                alternative = RetrievalStrategyOption.BM25
                reason = "Factual definition query maps cleanly to dense vector semantic similarity with minimal latency."
                why_not = "BM25 keyword matching fails on synonym variations for concise definition queries."
                confidence = 0.95
            else:
                selected = RetrievalStrategyOption.HYBRID_RERANKED
                alternative = RetrievalStrategyOption.DENSE_FAISS
                reason = "Detailed definition query benefits from hybrid reranking."
                why_not = "Pure dense FAISS may miss specific technical keywords in detailed definitions."
                confidence = 0.90

        # Rule 7: Troubleshooting / General IT Queries
        else:
            selected = RetrievalStrategyOption.HYBRID_RERANKED
            alternative = RetrievalStrategyOption.HYBRID
            reason = "General IT troubleshooting requires hybrid FAISS/BM25 recall merged with Cross-Encoder re-ranking precision."
            why_not = "Standard hybrid search without re-ranking places noisy keyword matches in top positions."
            confidence = 0.92

        latency, cost = self.STRATEGY_METRICS.get(selected, (100.0, 0.0003))

        return RetrievalPolicyDecision(
            selected_strategy=selected,
            reason=reason,
            confidence=confidence,
            expected_latency_ms=latency,
            estimated_cost_usd=cost,
            alternative_strategy=alternative,
            why_not=why_not,
        )
