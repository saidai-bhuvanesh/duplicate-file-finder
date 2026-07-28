"""
Query Application Service orchestrating multi-agent query execution & PostgreSQL log persistence.
"""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import AgentWorkflowEngine
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.domain.entities.query import (
    AnswerStatus,
    Citation,
    Query,
    QueryResult,
    QueryType,
    RetrievalStrategy,
)
from app.infrastructure.database.models import QueryLogModel
from app.infrastructure.repositories.chunk_repository import PostgresChunkRepository
from app.retrieval.bm25_index import BM25Index
from app.retrieval.hybrid_engine import HybridRetrievalEngine
from app.retrieval.vector_store import FAISSVectorStore

logger = get_logger(__name__, component="query_service")


class QueryService:
    """
    Application Service handling user queries using the Multi-Agent pipeline.
    """

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()

        chunk_repo = PostgresChunkRepository(session)
        vector_store = FAISSVectorStore()
        bm25_index = BM25Index()

        hybrid_engine = HybridRetrievalEngine(vector_store, bm25_index, chunk_repo)
        self.workflow_engine = AgentWorkflowEngine(hybrid_engine=hybrid_engine)

    async def execute_query(
        self,
        query_text: str,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        retrieval_strategy: RetrievalStrategy | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ) -> QueryResult:
        """
        Execute multi-agent workflow for query, log to PostgreSQL, and return QueryResult.
        """
        start_time = time.perf_counter()

        strat_str = (retrieval_strategy or RetrievalStrategy.HYBRID_RERANKED).value

        # Execute Multi-Agent Graph Trajectory
        agent_state = await self.workflow_engine.run_workflow(
            query_text=query_text,
            top_k=top_k,
            filters=filters or {},
            retrieval_strategy=strat_str,
        )

        total_latency = (time.perf_counter() - start_time) * 1000

        # Build Citation objects
        citations = []
        for c in agent_state.get("citations", []):
            citations.append(
                Citation(
                    chunk_id=c.get("chunk_id", ""),
                    document_id=c.get("document_id", ""),
                    document_title=c.get("document_title", ""),
                    source_url=c.get("source_url"),
                    section_title=c.get("section_title"),
                    section_path=c.get("section_path"),
                    page_number=c.get("page_number"),
                    relevance_score=c.get("relevance_score", 0.0),
                    snippet=c.get("snippet", ""),
                )
            )

        evidence_dict = agent_state.get("evidence_score", {})
        conf_score = evidence_dict.get("confidence", 0.8)
        halluc_risk = 1.0 - evidence_dict.get("overall_score", 0.8)

        # Log query to PostgreSQL (Best Effort)
        try:
            query_log = QueryLogModel(
                id=agent_state["query_id"],
                query_text=query_text,
                query_type=agent_state.get("query_type", QueryType.UNKNOWN.value),
                retrieval_strategy=strat_str,
                status=AnswerStatus.COMPLETED.value if agent_state.get("is_verified") else AnswerStatus.FAILED.value,
                answer=agent_state.get("verified_answer", ""),
                confidence_score=conf_score,
                hallucination_risk=halluc_risk,
                evidence_quality=evidence_dict,
                citations=[c.to_dict() for c in citations],
                agent_trace=agent_state.get("agent_trace", []),
                filters_applied=filters or {},
                total_latency_ms=total_latency,
                retrieval_latency_ms=total_latency * 0.4,
                llm_latency_ms=total_latency * 0.6,
                total_tokens_used=agent_state.get("total_tokens_used", 0),
                estimated_cost_usd=agent_state.get("estimated_cost_usd", 0.0),
                user_id=user_id,
                session_id=session_id,
            )
            self.session.add(query_log)
            await self.session.commit()
        except Exception as db_exc:
            logger.warning("db_logging_skipped", error=str(db_exc))

        logger.info(
            "query_execution_logged",
            query_id=agent_state["query_id"],
            total_latency_ms=round(total_latency, 2),
        )

        return QueryResult(
            query_id=agent_state["query_id"],
            query_text=query_text,
            answer=agent_state.get("verified_answer", ""),
            status=AnswerStatus.COMPLETED if agent_state.get("is_verified") else AnswerStatus.FAILED,
            confidence_score=conf_score,
            hallucination_risk=halluc_risk,
            citations=citations,
            evidence_quality=evidence_dict,
            strategy_used=RetrievalStrategy(strat_str),
            query_type=QueryType(agent_state.get("query_type", QueryType.UNKNOWN.value)),
            agent_trace=agent_state.get("agent_trace", []),
            retrieval_latency_ms=total_latency * 0.4,
            total_latency_ms=total_latency,
            total_tokens_used=agent_state.get("total_tokens_used", 0),
            estimated_cost_usd=agent_state.get("estimated_cost_usd", 0.0),
        )
