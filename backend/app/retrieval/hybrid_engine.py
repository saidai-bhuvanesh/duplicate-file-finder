"""
Unified Hybrid Retrieval Engine combining BM25, FAISS, Cross-Encoder, and Parent-Doc Retrieval.
"""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.entities.query import Query, RetrievalStrategy, RetrievedContext
from app.domain.interfaces.chunk_repository import ChunkRepository
from app.retrieval.adaptive_router import AdaptiveRetrievalRouter
from app.retrieval.bm25_index import BM25Index
from app.retrieval.evidence_gate import EvidenceSufficiencyGate
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector_store import FAISSVectorStore

logger = get_logger(__name__, component="hybrid_engine")


class HybridRetrievalEngine:
    """
    Core Hybrid Retrieval Engine implementing:
    - Dense FAISS search
    - Sparse BM25 search
    - Reciprocal Rank Fusion (RRF)
    - Cross-Encoder Re-ranking
    - Parent Document Retrieval resolution
    - Adaptive Routing & Evidence Gate integration
    """

    def __init__(
        self,
        vector_store: FAISSVectorStore,
        bm25_index: BM25Index,
        chunk_repo: ChunkRepository,
        reranker: CrossEncoderReranker | None = None,
        router: AdaptiveRetrievalRouter | None = None,
        evidence_gate: EvidenceSufficiencyGate | None = None,
    ) -> None:
        self.vector_store = vector_store
        self.bm25_index = bm25_index
        self.chunk_repo = chunk_repo
        self.reranker = reranker or CrossEncoderReranker()
        self.router = router or AdaptiveRetrievalRouter()
        self.evidence_gate = evidence_gate or EvidenceSufficiencyGate()
        self.settings = get_settings().retrieval

    async def retrieve(
        self,
        query: Query,
        override_strategy: RetrievalStrategy | None = None,
    ) -> RetrievedContext:
        """
        Execute full retrieval workflow for a user query.
        """
        start_time = time.perf_counter()

        # 1. Adaptive Routing
        strategy, q_type = self.router.select_strategy(
            query_text=query.text,
            query_type=query.query_type,
            override_strategy=override_strategy or query.retrieval_strategy,
        )
        query.retrieval_strategy = strategy
        query.query_type = q_type

        # 2. Retrieve Candidate Chunks based on strategy
        candidates, dense_latency, rerank_latency = await self._execute_retrieval_stage(
            query=query, strategy=strategy
        )

        # 3. Resolve Parent-Document Context if Parent-Doc retrieval strategy or parent chunks present
        if strategy == RetrievalStrategy.PARENT_DOCUMENT:
            candidates = await self._resolve_parent_chunks(candidates)

        # 4. Evidence Gate evaluation & potential retry
        async def _retry_retrieval(new_query: str) -> list[Chunk]:
            q_copy = Query(text=new_query, top_k=query.top_k, filters=query.filters)
            cands, _, _ = await self._execute_retrieval_stage(q_copy, strategy)
            return cands

        verified_chunks, evidence_score = await self.evidence_gate.verify_or_retry(
            query=query.text,
            chunks=candidates,
            retrieval_fn=_retry_retrieval,
        )

        total_latency = (time.perf_counter() - start_time) * 1000

        logger.info(
            "hybrid_retrieval_completed",
            query_id=query.id,
            strategy=strategy.value,
            chunks_retrieved=len(verified_chunks),
            latency_ms=round(total_latency, 2),
        )

        return RetrievedContext(
            query_id=query.id,
            chunks=verified_chunks,
            strategy_used=strategy,
            retrieval_latency_ms=dense_latency,
            reranking_latency_ms=rerank_latency,
            total_candidates_retrieved=len(candidates),
        )

    async def _execute_retrieval_stage(
        self, query: Query, strategy: RetrievalStrategy
    ) -> tuple[list[Chunk], float, float]:
        top_k = query.top_k * 3  # Fetch candidate multiplier
        start_ret = time.perf_counter()

        bm25_hits: list[dict[str, Any]] = []
        dense_hits: list[Any] = []

        # Execute Sparse / Dense searches
        if strategy in (RetrievalStrategy.BM25_ONLY, RetrievalStrategy.HYBRID, RetrievalStrategy.HYBRID_RERANKED, RetrievalStrategy.PARENT_DOCUMENT):
            bm25_hits = self.bm25_index.search(query.text, top_k=top_k, filters=query.filters)

        if strategy in (RetrievalStrategy.DENSE_ONLY, RetrievalStrategy.HYBRID, RetrievalStrategy.HYBRID_RERANKED, RetrievalStrategy.PARENT_DOCUMENT):
            q_emb = self.vector_store.encode_text(query.text)[0].tolist()
            dense_hits = await self.vector_store.search(q_emb, top_k=top_k, filters=query.filters)

        retrieval_latency = (time.perf_counter() - start_ret) * 1000

        # Reciprocal Rank Fusion (RRF)
        fused_chunks = self._reciprocal_rank_fusion(bm25_hits, dense_hits)

        # Cross-Encoder Re-ranking
        start_rr = time.perf_counter()
        if strategy in (RetrievalStrategy.HYBRID_RERANKED, RetrievalStrategy.PARENT_DOCUMENT) and fused_chunks:
            reranked_chunks = self.reranker.rerank(query=query.text, chunks=fused_chunks, top_k=query.top_k)
        else:
            reranked_chunks = fused_chunks[: query.top_k]

        rerank_latency = (time.perf_counter() - start_rr) * 1000
        return reranked_chunks, retrieval_latency, rerank_latency

    def _reciprocal_rank_fusion(
        self,
        bm25_hits: list[dict[str, Any]],
        dense_hits: list[Any],
        rrf_k: int = 60,
    ) -> list[Chunk]:
        """
        Reciprocal Rank Fusion (RRF) combining sparse and dense candidate lists.
        Score(d) = sum(1 / (k + rank_i(d)))
        """
        scores: dict[str, float] = {}
        chunk_map: dict[str, Chunk] = {}

        # Process BM25 hits
        for rank, hit in enumerate(bm25_hits, 1):
            cid = hit["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
            if cid not in chunk_map:
                chunk_map[cid] = Chunk(
                    id=cid,
                    document_id=hit["document_id"],
                    content=hit["content"],
                    section_title=hit.get("section_title"),
                    bm25_score=hit["score"],
                    metadata=hit.get("metadata", {}),
                )

        # Process Dense hits
        for rank, hit in enumerate(dense_hits, 1):
            cid = hit.chunk_id
            scores[cid] = scores.get(cid, 0.0) + (1.0 / (rrf_k + rank))
            if cid not in chunk_map:
                chunk_map[cid] = Chunk(
                    id=cid,
                    document_id=hit.document_id,
                    content=hit.content,
                    dense_score=hit.score,
                    metadata=hit.metadata,
                )
            else:
                chunk_map[cid].dense_score = hit.score

        # Populate final RRF scores
        results = []
        for cid, rrf_score in scores.items():
            chunk = chunk_map[cid]
            chunk.final_score = round(rrf_score, 4)
            results.append(chunk)

        results.sort(key=lambda c: c.final_score or 0.0, reverse=True)
        return results

    async def _resolve_parent_chunks(self, child_chunks: list[Chunk]) -> list[Chunk]:
        """Resolve child chunk hits to their larger parent chunk context."""
        resolved: list[Chunk] = []
        seen_parents: set[str] = set()

        for c in child_chunks:
            if c.parent_chunk_id and c.parent_chunk_id not in seen_parents:
                parent = await self.chunk_repo.get_parent_chunk(c.id)
                if parent:
                    parent.final_score = c.final_score
                    resolved.append(parent)
                    seen_parents.add(parent.id)
            elif not c.parent_chunk_id and c.id not in seen_parents:
                resolved.append(c)
                seen_parents.add(c.id)

        return resolved if resolved else child_chunks
