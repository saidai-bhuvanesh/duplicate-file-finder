"""
Explainable Retrieval Service (Step 3 of ARIE).

Generates structured JSON explanations for retrieval policy decisions.
"""

from __future__ import annotations

from typing import Any, Dict

from app.core.logging import get_logger
from app.domain.entities.arie import ARIEExplanation, QueryIntelligenceResult, RetrievalPolicyDecision
from app.retrieval.arie.policy_engine import RetrievalPolicyEngine
from app.retrieval.arie.query_intelligence import QueryIntelligenceEngine

logger = get_logger(__name__, component="explainable_retrieval")


class ExplainableRetrievalService:
    """
    Service providing explainable retrieval recommendations and structured JSON audits.
    """

    def __init__(
        self,
        intelligence_engine: QueryIntelligenceEngine | None = None,
        policy_engine: RetrievalPolicyEngine | None = None,
    ) -> None:
        self.intelligence_engine = intelligence_engine or QueryIntelligenceEngine()
        self.policy_engine = policy_engine or RetrievalPolicyEngine()

    def explain(self, query_text: str) -> ARIEExplanation:
        """
        Analyze query_text and produce a complete ARIEExplanation object.
        """
        intelligence: QueryIntelligenceResult = self.intelligence_engine.classify(query_text)
        decision: RetrievalPolicyDecision = self.policy_engine.select_policy(intelligence)

        explanation = ARIEExplanation(
            query=query_text,
            intelligence=intelligence,
            decision=decision,
        )

        logger.info(
            "explanation_generated",
            query=query_text,
            selected_strategy=decision.selected_strategy.value,
        )

        return explanation

    def explain_as_json(self, query_text: str) -> Dict[str, Any]:
        """
        Return the explanation in standard JSON dict format matching IEEE paper specs.
        """
        explanation = self.explain(query_text)
        return explanation.to_json_dict()
