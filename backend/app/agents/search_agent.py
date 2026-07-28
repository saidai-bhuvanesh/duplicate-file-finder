"""
Search Agent executing hybrid vector and graph retrieval for sub-queries.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.agents.state import AgentState, AgentTraceStep
from app.core.logging import get_logger
from app.domain.entities.chunk import Chunk
from app.domain.entities.query import Query, RetrievalStrategy
from app.graph.graph_rag import GraphRAGEngine
from app.retrieval.evidence_gate import EvidenceSufficiencyGate
from app.retrieval.hybrid_engine import HybridRetrievalEngine

logger = get_logger(__name__, component="search_agent")


class SearchAgent:
    """
    Search Agent orchestrating multi-query hybrid & graph retrieval.
    """

    def __init__(
        self,
        hybrid_engine: HybridRetrievalEngine | None = None,
        graph_rag: GraphRAGEngine | None = None,
    ) -> None:
        self.hybrid_engine = hybrid_engine
        self.graph_rag = graph_rag or GraphRAGEngine()
        self.evidence_gate = EvidenceSufficiencyGate()

    async def execute_search(self, state: AgentState) -> AgentState:
        sub_queries = state.get("sub_queries", [state["query_text"]])
        top_k = state.get("top_k", 5)
        filters = state.get("filters", {})
        strategy_name = state.get("retrieval_strategy", RetrievalStrategy.HYBRID_RERANKED.value)

        logger.info("search_agent_executing", sub_queries_count=len(sub_queries))
        retrieved_chunks_map: dict[str, dict[str, Any]] = {}

        for sq in sub_queries:
            chunks: list[Chunk] = []

            # 1. Execute GraphRAG if strategy is GRAPH_HYBRID or graph keywords present
            if strategy_name == RetrievalStrategy.GRAPH_HYBRID.value or "owner" in sq.lower() or "team" in sq.lower():
                graph_chunks = await self.graph_rag.retrieve_graph_context(sq, top_k=top_k)
                chunks.extend(graph_chunks)

            # 2. Execute Hybrid Retrieval Engine if initialized
            if self.hybrid_engine:
                query_obj = Query(text=sq, top_k=top_k, filters=filters)
                context = await self.hybrid_engine.retrieve(query_obj)
                chunks.extend(context.chunks)

            # Deduplicate chunks
            for c in chunks:
                if c.id not in retrieved_chunks_map:
                    retrieved_chunks_map[c.id] = c.to_retrieval_dict()

        final_chunks_dict = list(retrieved_chunks_map.values())

        # Evaluate Evidence Gate
        reconstructed_chunks = [
            Chunk(
                id=d["chunk_id"],
                document_id=d["document_id"],
                content=d["content"],
                section_title=d.get("section_title"),
                final_score=d.get("scores", {}).get("final", 0.0),
                metadata=d.get("metadata", {}),
            )
            for d in final_chunks_dict
        ]
        evidence = self.evidence_gate.evaluate_evidence(state["query_text"], reconstructed_chunks)

        trace_entry: AgentTraceStep = {
            "agent": "SearchAgent",
            "status": "completed",
            "message": f"Retrieved {len(final_chunks_dict)} evidence chunks across {len(sub_queries)} sub-queries",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "chunks_count": len(final_chunks_dict),
                "verdict": evidence.verdict.value,
                "overall_score": evidence.overall_score,
            },
        }

        state["retrieved_chunks"] = final_chunks_dict
        state["evidence_score"] = evidence.to_dict()
        state["agent_trace"].append(trace_entry)
        return state
