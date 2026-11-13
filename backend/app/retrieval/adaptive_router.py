"""
Adaptive Retrieval Router dynamically selecting retrieval strategy per query.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger
from app.domain.entities.query import QueryType, RetrievalStrategy

logger = get_logger(__name__, component="adaptive_router")


class AdaptiveRetrievalRouter:
    """
    Innovation 1: Adaptive Retrieval Routing.
    Classifies incoming query intent and selects optimal retrieval strategy.
    """

    # Keyword rules for fast heuristic classification
    CODE_KEYWORDS = {"def", "function", "class", "syntax", "error", "exception", "traceback", "import", "docker", "k8s", "kubernetes", "terraform", "sql", "api", "endpoint", "python", "sqlalchemy", "code"}
    INCIDENT_KEYWORDS = {"incident", "postmortem", "outage", "downtime", "sev1", "sev2", "bug", "p0", "p1", "alert", "sla", "policy", "failure", "escalation"}
    ENTITY_KEYWORDS = {"who", "team", "owner", "service", "repo", "repository", "author", "maintainer", "lead", "which team"}
    PROCEDURAL_KEYWORDS = {"how to", "how does", "how do", "steps", "guide", "setup", "install", "deploy", "configure", "runbook", "sop", "scale", "scaling", "manage"}

    def classify_query(self, query_text: str) -> QueryType:
        """Classify user query intent into QueryType."""
        text_lower = query_text.lower()
        words = set(re.findall(r"\b\w+\b", text_lower))

        if any(phrase in text_lower for phrase in self.PROCEDURAL_KEYWORDS):
            return QueryType.PROCEDURAL
        elif words & self.INCIDENT_KEYWORDS:
            return QueryType.INCIDENT
        elif "which team" in text_lower or (words & self.ENTITY_KEYWORDS):
            return QueryType.ENTITY
        elif words & self.CODE_KEYWORDS or re.search(r"```|\.py|\.ts|\.java|\.go|\.tf", text_lower):
            return QueryType.CODE if "how" not in text_lower else QueryType.PROCEDURAL
        elif any(word in text_lower for word in ["compare", "architecture", "versus", "vs", "design", "tradeoff"]):
            return QueryType.ARCHITECTURAL
        elif any(word in text_lower for word in ["what is", "what are", "when", "where", "definition", "overview"]):
            return QueryType.FACTUAL
        else:
            return QueryType.FACTUAL

    def select_strategy(
        self,
        query_text: str,
        query_type: QueryType | None = None,
        override_strategy: RetrievalStrategy | None = None,
    ) -> tuple[RetrievalStrategy, QueryType]:
        """
        Dynamically select optimal retrieval strategy for the query.

        Args:
            query_text: Raw query.
            query_type: Pre-classified query type or None.
            override_strategy: Manual override if requested by API user.

        Returns:
            Tuple of (RetrievalStrategy, QueryType)
        """
        if override_strategy:
            q_type = query_type or self.classify_query(query_text)
            logger.info("strategy_overridden", strategy=override_strategy.value, query_type=q_type.value)
            return override_strategy, q_type

        q_type = query_type or self.classify_query(query_text)

        if q_type in (QueryType.CODE, QueryType.DEBUGGING):
            strategy = RetrievalStrategy.HYBRID_RERANKED
        elif q_type in (QueryType.ENTITY, QueryType.ANALYTICAL):
            strategy = RetrievalStrategy.GRAPH_HYBRID
        elif q_type in (QueryType.PROCEDURAL, QueryType.ARCHITECTURAL):
            strategy = RetrievalStrategy.PARENT_DOCUMENT
        elif q_type == QueryType.FACTUAL:
            strategy = RetrievalStrategy.HYBRID_RERANKED
        else:
            strategy = RetrievalStrategy.HYBRID_RERANKED

        logger.info("adaptive_strategy_selected", query_type=q_type.value, strategy=strategy.value)
        return strategy, q_type
