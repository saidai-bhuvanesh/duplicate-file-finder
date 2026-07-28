"""
Search API endpoints integrated with Multi-Agent Orchestration Engine (LangGraph).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.application.services.query_service import QueryService
from app.core.dependencies import DatabaseSessionDep, SettingsDep
from app.core.logging import get_logger
from app.domain.entities.query import AnswerStatus, QueryType, RetrievalStrategy

router = APIRouter(prefix="/search", tags=["Search"])
logger = get_logger(__name__, component="search_api")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="User query")
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict[str, Any] = Field(default_factory=dict)
    retrieval_strategy: RetrievalStrategy | None = Field(
        default=None,
        description="Override auto-selected strategy",
    )
    include_trace: bool = Field(default=True, description="Include agent reasoning trace")


class SearchResponse(BaseModel):
    query_id: str
    query: str
    answer: str
    status: str
    confidence_score: float
    hallucination_risk: float
    citations: list[dict[str, Any]]
    evidence_quality: dict[str, Any]
    strategy_used: str
    query_type: str
    agent_trace: list[dict[str, Any]]
    retrieval_latency_ms: float
    total_latency_ms: float
    total_tokens_used: int
    estimated_cost_usd: float


@router.post(
    "/",
    response_model=SearchResponse,
    summary="Search the knowledge base",
    description="Query the enterprise knowledge base using the Multi-Agent Orchestration Engine (LangGraph).",
)
async def search(
    request: SearchRequest,
    session: DatabaseSessionDep,
) -> SearchResponse:
    """
    Execute full multi-agent search pipeline:
    Planner -> Search -> Reasoning -> Generator -> Verifier.
    """
    logger.info("multi_agent_search_request", query=request.query, top_k=request.top_k)

    query_service = QueryService(session=session)
    result = await query_service.execute_query(
        query_text=request.query,
        top_k=request.top_k,
        filters=request.filters,
        retrieval_strategy=request.retrieval_strategy,
    )

    return SearchResponse(
        query_id=result.query_id,
        query=result.query_text,
        answer=result.answer,
        status=result.status.value,
        confidence_score=result.confidence_score,
        hallucination_risk=result.hallucination_risk,
        citations=[c.to_dict() for c in result.citations],
        evidence_quality=result.evidence_quality,
        strategy_used=result.strategy_used.value,
        query_type=result.query_type.value,
        agent_trace=result.agent_trace if request.include_trace else [],
        retrieval_latency_ms=round(result.retrieval_latency_ms, 2),
        total_latency_ms=round(result.total_latency_ms, 2),
        total_tokens_used=result.total_tokens_used,
        estimated_cost_usd=round(result.estimated_cost_usd, 6),
    )
