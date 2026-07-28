"""
Unit tests for Phase 3 Hybrid Retrieval Engine, BM25 Index, FAISS Vector Store, Reranker, Router, and Evidence Gate.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.entities.query import Query, QueryType, RetrievalStrategy
from app.domain.value_objects.evidence_score import EvidenceScore, EvidenceVerdict
from app.retrieval.adaptive_router import AdaptiveRetrievalRouter
from app.retrieval.bm25_index import BM25Index, _tokenize
from app.retrieval.evidence_gate import EvidenceSufficiencyGate
from app.retrieval.hybrid_engine import HybridRetrievalEngine
from app.retrieval.reranker import CrossEncoderReranker
from app.retrieval.vector_store import FAISSVectorStore


@pytest.mark.unit
class TestBM25Index:
    def test_tokenization(self):
        tokens = _tokenize("Kubernetes Horizontal Pod Autoscaler (HPA)")
        assert "kubernetes" in tokens
        assert "horizontal" in tokens
        assert "pod" in tokens

    def test_index_build_and_search(self, tmp_path):
        index_path = str(tmp_path / "test_bm25")
        index = BM25Index(index_path=index_path)

        chunks = [
            Chunk(id="c1", document_id="d1", content="Kubernetes cluster setup guide"),
            Chunk(id="c2", document_id="d2", content="Docker compose container networking"),
            Chunk(id="c3", document_id="d3", content="Terraform AWS S3 bucket module"),
        ]
        index.build_index(chunks)

        results = index.search("Kubernetes", top_k=2)
        assert len(results) >= 1
        assert results[0]["chunk_id"] == "c1"
        assert results[0]["score"] > 0.0


@pytest.mark.unit
class TestAdaptiveRouter:
    def test_query_classification(self):
        router = AdaptiveRetrievalRouter()
        assert router.classify_query("def process_data(x):") == QueryType.CODE
        assert router.classify_query("How to deploy microservices on Kubernetes?") == QueryType.DEBUGGING or router.classify_query("How to deploy microservices on Kubernetes?") == QueryType.PROCEDURAL
        assert router.classify_query("Who is the owner of auth-service?") == QueryType.ENTITY
        assert router.classify_query("What is the architecture of the platform?") == QueryType.ARCHITECTURAL

    def test_strategy_selection(self):
        router = AdaptiveRetrievalRouter()
        strategy, qtype = router.select_strategy("def calculate():")
        assert strategy in (RetrievalStrategy.HYBRID_RERANKED, RetrievalStrategy.BM25_ONLY)


@pytest.mark.unit
class TestEvidenceSufficiencyGate:
    def test_evaluate_evidence(self):
        gate = EvidenceSufficiencyGate()
        chunks = [
            Chunk(id="c1", document_id="d1", content="Kubernetes documentation overview", final_score=0.9),
            Chunk(id="c2", document_id="d2", content="Container orchestration details", final_score=0.8),
        ]
        score = gate.evaluate_evidence("Kubernetes container", chunks)
        assert isinstance(score, EvidenceScore)
        assert score.confidence > 0.0

    @pytest.mark.asyncio
    async def test_verify_sufficient_evidence(self):
        gate = EvidenceSufficiencyGate()
        chunks = [
            Chunk(id="c1", document_id="d1", content="Kubernetes documentation overview", final_score=0.9),
            Chunk(id="c2", document_id="d2", content="Container orchestration details", final_score=0.8),
        ]
        mock_retrieval_fn = AsyncMock(return_value=[])
        verified_chunks, score = await gate.verify_or_retry("Kubernetes container", chunks, mock_retrieval_fn)
        assert len(verified_chunks) > 0


@pytest.mark.unit
class TestHybridEngineRRF:
    def test_reciprocal_rank_fusion(self, mock_chunk_repo):
        vector_store = MagicMock(spec=FAISSVectorStore)
        bm25_index = MagicMock(spec=BM25Index)
        engine = HybridRetrievalEngine(vector_store, bm25_index, mock_chunk_repo)

        bm25_hits = [
            {"chunk_id": "c1", "document_id": "d1", "content": "A", "score": 2.5},
            {"chunk_id": "c2", "document_id": "d2", "content": "B", "score": 1.5},
        ]
        dense_hits = [
            MagicMock(chunk_id="c2", document_id="d2", content="B", score=0.9),
            MagicMock(chunk_id="c3", document_id="d3", content="C", score=0.8),
        ]

        fused = engine._reciprocal_rank_fusion(bm25_hits, dense_hits)
        assert len(fused) == 3
        # c2 appears in both lists, so its RRF score should be highest
        assert fused[0].id == "c2"
