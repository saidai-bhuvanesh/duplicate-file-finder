"""
Verifier Agent performing NLI Faithfulness Auditing, Citation Verification, and Automated Refusal.
"""

from __future__ import annotations

from datetime import datetime

from app.agents.citation_auditor import CitationAuditor
from app.agents.nli_verifier import NLIVerifier
from app.agents.state import AgentState, AgentTraceStep
from app.core.logging import get_logger

logger = get_logger(__name__, component="verifier_agent")


class VerifierAgent:
    """
    Verifier Agent performing NLI Faithfulness Auditing, Citation Verification, and Automated Refusal.
    """

    def __init__(
        self,
        nli_verifier: NLIVerifier | None = None,
        auditor: CitationAuditor | None = None,
    ) -> None:
        self.nli_verifier = nli_verifier or NLIVerifier()
        self.auditor = auditor or CitationAuditor(nli_verifier=self.nli_verifier)

    async def verify(self, state: AgentState) -> AgentState:
        draft = state.get("draft_answer", "")
        citations = state.get("citations", [])

        logger.info("verifier_agent_verifying", draft_len=len(draft), citations_count=len(citations))

        if not draft or "⚠️ No evidence chunks" in draft:
            state["is_verified"] = False
            state["hallucination_detected"] = False
            state["verified_answer"] = draft or "⚠️ Insufficient evidence in verified knowledge base to validate this statement."
            trace_entry: AgentTraceStep = {
                "agent": "VerifierAgent",
                "status": "completed",
                "message": "Verification complete (Refusal or no draft text)",
                "timestamp": datetime.utcnow().isoformat(),
                "details": {"is_verified": False},
            }
            state["agent_trace"].append(trace_entry)
            return state

        # 1. Audit citations & NLI faithfulness
        audited_text, hallucinated, faithfulness_score = self.auditor.audit_answer(draft, citations)

        # 2. Automated Refusal Mechanism if Faithfulness Score < 0.3 or major hallucination
        if faithfulness_score < 0.3 and len(citations) > 0:
            logger.warning("refusal_triggered_low_faithfulness", faithfulness_score=faithfulness_score)
            verified_final = "⚠️ Refused: Generated answer could not be verified with high confidence against source citations."
            is_verified = False
            hallucinated = True
        else:
            verified_final = audited_text
            is_verified = not hallucinated

        trace_entry: AgentTraceStep = {
            "agent": "VerifierAgent",
            "status": "completed",
            "message": f"NLI verification complete. Faithfulness: {faithfulness_score}, Hallucinations: {hallucinated}",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "faithfulness_score": faithfulness_score,
                "hallucination_detected": hallucinated,
                "is_verified": is_verified,
            },
        }

        state["is_verified"] = is_verified
        state["hallucination_detected"] = hallucinated
        state["verified_answer"] = verified_final
        state["agent_trace"].append(trace_entry)
        return state
