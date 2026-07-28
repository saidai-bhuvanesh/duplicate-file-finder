"""
Reasoning Agent synthesizing facts across heterogeneous retrieved chunks.
"""

from __future__ import annotations

from datetime import datetime

from app.agents.state import AgentState, AgentTraceStep
from app.core.logging import get_logger

logger = get_logger(__name__, component="reasoning_agent")


class ReasoningAgent:
    """
    Reasoning Agent analyzing retrieved context, extracting facts, and organizing evidence.
    """

    async def reason(self, state: AgentState) -> AgentState:
        chunks = state.get("retrieved_chunks", [])
        logger.info("reasoning_agent_processing", chunks_count=len(chunks))

        # Sort chunks by relevance score
        sorted_chunks = sorted(
            chunks,
            key=lambda c: c.get("scores", {}).get("final", 0.0) or c.get("final_score", 0.0),
            reverse=True,
        )

        # Extract top evidence snippets with source tags
        evidence_facts = []
        for i, c in enumerate(sorted_chunks[:5], 1):
            title = c.get("section_title") or c.get("metadata", {}).get("document_title", f"Source {i}")
            snippet = c.get("content", "")[:300].replace("\n", " ")
            evidence_facts.append(f"[Source {i}] ({title}): {snippet}")

        trace_entry: AgentTraceStep = {
            "agent": "ReasoningAgent",
            "status": "completed",
            "message": f"Synthesized {len(evidence_facts)} primary facts from {len(chunks)} evidence chunks",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {"synthesized_facts_count": len(evidence_facts)},
        }

        state["agent_trace"].append(trace_entry)
        return state
