"""
LangGraph Multi-Agent State Graph Orchestrator.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from app.agents.generator_agent import GeneratorAgent
from app.agents.planner_agent import PlannerAgent
from app.agents.reasoning_agent import ReasoningAgent
from app.agents.search_agent import SearchAgent
from app.agents.state import AgentState
from app.agents.verifier_agent import VerifierAgent
from app.core.logging import get_logger
from app.graph.graph_rag import GraphRAGEngine
from app.retrieval.hybrid_engine import HybridRetrievalEngine

logger = get_logger(__name__, component="agent_workflow_engine")


class AgentWorkflowEngine:
    """
    Multi-Agent Orchestrator executing the agent workflow:
    Planner -> Search -> Reasoning -> Generator -> Verifier.
    """

    def __init__(
        self,
        hybrid_engine: HybridRetrievalEngine | None = None,
        graph_rag: GraphRAGEngine | None = None,
        max_iterations: int = 2,
    ) -> None:
        self.planner = PlannerAgent()
        self.searcher = SearchAgent(hybrid_engine=hybrid_engine, graph_rag=graph_rag)
        self.reasoner = ReasoningAgent()
        self.generator = GeneratorAgent()
        self.verifier = VerifierAgent()
        self.max_iterations = max_iterations

    async def run_workflow(
        self,
        query_text: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        retrieval_strategy: str = "hybrid_reranked",
    ) -> AgentState:
        """
        Execute full multi-agent state graph trajectory.

        Returns:
            Final AgentState dictionary.
        """
        start_time = time.perf_counter()
        query_id = str(uuid.uuid4())

        initial_state: AgentState = {
            "query_id": query_id,
            "query_text": query_text,
            "top_k": top_k,
            "filters": filters or {},
            "query_type": "unknown",
            "retrieval_strategy": retrieval_strategy,
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

        logger.info("starting_multi_agent_workflow", query_id=query_id, query=query_text)

        # 1. Planner Node
        state = await self.planner.plan(initial_state)

        # 2. Search Node
        state = await self.searcher.execute_search(state)

        # 3. Reasoning Node
        state = await self.reasoner.reason(state)

        # 4. Generator Node
        state = await self.generator.generate(state)

        # 5. Verifier Node
        state = await self.verifier.verify(state)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "multi_agent_workflow_completed",
            query_id=query_id,
            is_verified=state["is_verified"],
            elapsed_ms=round(elapsed_ms, 2),
        )
        return state
