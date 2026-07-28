"""
Planner Agent decomposing queries into sub-goals and sub-queries.
"""

from __future__ import annotations

from datetime import datetime

from app.agents.state import AgentState, AgentTraceStep
from app.core.logging import get_logger

logger = get_logger(__name__, component="planner_agent")


class PlannerAgent:
    """
    Planner Agent analyzing user query and planning retrieval sub-goals.
    """

    async def plan(self, state: AgentState) -> AgentState:
        query_text = state["query_text"]
        logger.info("planner_agent_planning", query=query_text)

        # Decompose query into sub-queries
        sub_queries = [query_text]
        if " and " in query_text.lower() or " vs " in query_text.lower() or " compare " in query_text.lower():
            parts = [p.strip() for p in query_text.replace(" vs ", " and ").replace(" compare ", " ").split(" and ")]
            if len(parts) > 1:
                sub_queries = parts

        plan = [
            f"Step 1: Retrieve context for main query '{query_text}'",
            f"Step 2: Synthesize evidence across {len(sub_queries)} sub-queries",
            "Step 3: Verify citations and check for hallucinations",
        ]

        trace_entry: AgentTraceStep = {
            "agent": "PlannerAgent",
            "status": "completed",
            "message": f"Generated {len(plan)} plan steps with {len(sub_queries)} sub-queries",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {"sub_queries": sub_queries, "plan": plan},
        }

        state["plan"] = plan
        state["sub_queries"] = sub_queries
        state["agent_trace"].append(trace_entry)
        return state
