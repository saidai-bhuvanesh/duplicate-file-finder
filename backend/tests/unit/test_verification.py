"""
Unit tests for Phase 6 NLI Verifier, Citation Auditor, and Verifier Agent refusal.
"""

import pytest

from app.agents.citation_auditor import CitationAuditor
from app.agents.nli_verifier import NLIVerifier
from app.agents.state import AgentState
from app.agents.verifier_agent import VerifierAgent


@pytest.mark.unit
class TestNLIVerifier:
    def test_verify_faithfulness_entailment(self):
        verifier = NLIVerifier()
        res = verifier.verify_faithfulness(
            premise="Kubernetes uses Horizontal Pod Autoscaler (HPA) to scale pods based on CPU metric.",
            hypothesis="HPA scales pods based on CPU metric in Kubernetes.",
        )
        assert res["is_faithful"] is True
        assert res["label"] in ("entailment", "neutral")

    def test_compute_faithfulness_score(self):
        verifier = NLIVerifier()
        score = verifier.compute_faithfulness_score(
            generated_sentences=["HPA scales pods.", "Kubernetes is container orchestration."],
            source_contexts=["Kubernetes is a container orchestration platform. HPA scales pods automatically."],
        )
        assert score > 0.5


@pytest.mark.unit
class TestCitationAuditor:
    def test_audit_valid_citations(self):
        auditor = CitationAuditor()
        draft = "Kubernetes is container orchestration [Source 1]."
        citations = [{"citation_id": "[Source 1]", "snippet": "Kubernetes is container orchestration platform."}]

        audited_text, hallucinated, score = auditor.audit_answer(draft, citations)
        assert hallucinated is False
        assert score > 0.0

    def test_audit_unsupported_citations(self):
        auditor = CitationAuditor()
        draft = "Quantum computer deployment [Source 1]."
        citations = [{"citation_id": "[Source 1]", "snippet": "PostgreSQL database configuration."}]

        audited_text, hallucinated, score = auditor.audit_answer(draft, citations)
        assert hallucinated is True


@pytest.mark.unit
@pytest.mark.asyncio
class TestVerifierAgentRefusal:
    async def test_refusal_on_empty_draft(self):
        verifier = VerifierAgent()
        state: AgentState = {
            "query_id": "q1",
            "query_text": "test",
            "top_k": 5,
            "filters": {},
            "query_type": "unknown",
            "retrieval_strategy": "hybrid",
            "plan": [],
            "sub_queries": [],
            "retrieved_chunks": [],
            "evidence_score": {},
            "draft_answer": "",
            "verified_answer": "",
            "citations": [],
            "agent_trace": [],
            "iteration": 1,
            "is_verified": False,
            "hallucination_detected": False,
            "total_tokens_used": 0,
            "estimated_cost_usd": 0.0,
        }

        res = await verifier.verify(state)
        assert "Insufficient evidence" in res["verified_answer"]
        assert res["is_verified"] is False
