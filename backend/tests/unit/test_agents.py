"""
Unit tests for Phase 5 Multi-Agent Orchestration Engine (Planner, Search, Reasoning, Generator, Verifier, Graph Engine).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.graph import AgentWorkflowEngine
from app.agents.planner_agent import PlannerAgent
from app.agents.reasoning_agent import ReasoningAgent
from app.agents.search_agent import SearchAgent
from app.agents.state import AgentState
from app.agents.verifier_agent import VerifierAgent


@pytest.fixture
def base_state() -> AgentState:
    return {
        "query_id": "test-q1",
        "query_text": "What is Kubernetes and how does HPA work?",
        "top_k": 5,
        "filters": {},
        "query_type": "procedural",
        "retrieval_strategy": "hybrid_reranked",
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


@pytest.mark.unit
@pytest.mark.asyncio
class TestPlannerAgent:
    async def test_planner_decomposes_multi_part_query(self, base_state):
        planner = PlannerAgent()
        res_state = await planner.plan(base_state)
        assert len(res_state["plan"]) >= 3
        assert len(res_state["sub_queries"]) >= 2
        assert len(res_state["agent_trace"]) == 1
        assert res_state["agent_trace"][0]["agent"] == "PlannerAgent"


@pytest.mark.unit
@pytest.mark.asyncio
class TestSearchAgent:
    async def test_search_agent_retrieval(self, base_state):
        mock_hybrid = AsyncMock()
        mock_graph = AsyncMock()
        mock_graph.retrieve_graph_context = AsyncMock(return_value=[])

        searcher = SearchAgent(hybrid_engine=mock_hybrid, graph_rag=mock_graph)
        base_state["sub_queries"] = ["What is Kubernetes?"]
        res_state = await searcher.execute_search(base_state)

        assert "retrieved_chunks" in res_state
        assert "evidence_score" in res_state
        assert len(res_state["agent_trace"]) == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestReasoningAgent:
    async def test_reasoning_synthesizes_facts(self, base_state):
        reasoner = ReasoningAgent()
        base_state["retrieved_chunks"] = [
            {"chunk_id": "c1", "content": "K8s is container orchestration.", "scores": {"final": 0.9}},
            {"chunk_id": "c2", "content": "HPA scales pods based on CPU.", "scores": {"final": 0.8}},
        ]
        res_state = await reasoner.reason(base_state)
        assert len(res_state["agent_trace"]) == 1
        assert res_state["agent_trace"][0]["agent"] == "ReasoningAgent"


@pytest.mark.unit
@pytest.mark.asyncio
class TestVerifierAgent:
    async def test_verifier_approves_valid_answer(self, base_state):
        verifier = VerifierAgent()
        base_state["draft_answer"] = "Kubernetes is container orchestration [Source 1]."
        base_state["citations"] = [{"citation_id": "[Source 1]", "document_title": "K8s Docs", "snippet": "Kubernetes is container orchestration platform."}]

        res_state = await verifier.verify(base_state)
        assert res_state["is_verified"] is True
        assert res_state["hallucination_detected"] is False
        assert "[Source 1]" in res_state["verified_answer"]

    async def test_verifier_flags_invalid_citation(self, base_state):
        verifier = VerifierAgent()
        base_state["draft_answer"] = "Fake fact [Source 99]."
        base_state["citations"] = [{"citation_id": "[Source 1]", "document_title": "K8s Docs", "snippet": "Kubernetes is container orchestration platform."}]

        res_state = await verifier.verify(base_state)
        assert res_state["hallucination_detected"] is True


@pytest.mark.unit
@pytest.mark.asyncio
class TestAgentWorkflowEngine:
    async def test_full_workflow_execution(self):
        engine = AgentWorkflowEngine()
        # Mock generator LLM call
        engine.generator.llm_client.complete = AsyncMock(
            return_value={"content": "Kubernetes overview.", "input_tokens": 10, "output_tokens": 10, "cost_usd": 0.001}
        )
        state = await engine.run_workflow("What is Kubernetes?")
        assert state["query_id"] is not None
        assert state["verified_answer"] != ""
        assert len(state["agent_trace"]) >= 5
