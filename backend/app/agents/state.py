"""
AgentState schema for LangGraph multi-agent orchestration pipeline.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentTraceStep(TypedDict):
    """Execution step log in agent reasoning trace."""

    agent: str
    status: str
    message: str
    timestamp: str
    details: dict[str, Any]


class AgentState(TypedDict):
    """
    State dictionary passed between LangGraph agent nodes.
    """

    query_id: str
    query_text: str
    top_k: int
    filters: dict[str, Any]
    query_type: str
    retrieval_strategy: str
    plan: list[str]
    sub_queries: list[str]
    retrieved_chunks: list[dict[str, Any]]
    evidence_score: dict[str, Any]
    draft_answer: str
    verified_answer: str
    citations: list[dict[str, Any]]
    agent_trace: list[AgentTraceStep]
    iteration: int
    is_verified: bool
    hallucination_detected: bool
    total_tokens_used: int
    estimated_cost_usd: float
