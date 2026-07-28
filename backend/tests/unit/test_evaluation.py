"""
Unit tests for Phase 7 Automated RAG Evaluation & Benchmarking (RAGEvaluationMetrics, Generator, Evaluator).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.domain.entities.document import Document
from app.evaluation.evaluator import EvaluationRunner
from app.evaluation.generator import SyntheticTestsetGenerator
from app.evaluation.metrics import RAGEvaluationMetrics


@pytest.mark.unit
class TestRAGEvaluationMetrics:
    def test_compute_all_metrics(self):
        engine = RAGEvaluationMetrics()
        query = "How to deploy services on Kubernetes?"
        answer = "Deploy services using Kubernetes Deployment manifest."
        contexts = ["Kubernetes Deployment manifest allows deploying microservices."]
        ground_truth = "Use Kubernetes Deployment manifests to deploy microservices."

        metrics = engine.compute_all_metrics(query, answer, contexts, ground_truth)

        assert 0.0 <= metrics["faithfulness"] <= 1.0
        assert 0.0 <= metrics["answer_relevance"] <= 1.0
        assert 0.0 <= metrics["context_precision"] <= 1.0
        assert 0.0 <= metrics["context_recall"] <= 1.0
        assert 0.0 <= metrics["semantic_similarity"] <= 1.0
        assert 0.0 <= metrics["overall_score"] <= 1.0


@pytest.mark.unit
@pytest.mark.asyncio
class TestSyntheticTestsetGenerator:
    async def test_generate_test_samples(self):
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            return_value={"content": "Question: How does HPA scale?\nAnswer: HPA scales based on CPU utilization."}
        )

        generator = SyntheticTestsetGenerator(llm_client=mock_llm)
        doc = Document(
            title="K8s HPA Guide",
            content="Horizontal Pod Autoscaler (HPA) automatically scales the number of Pods in a replication controller or deployment based on observed CPU utilization.",
        )

        samples = await generator.generate_test_samples_from_document(doc, num_samples=1)

        assert len(samples) == 1
        assert "HPA" in samples[0]["question"] or "discussed" in samples[0]["question"]
        assert samples[0]["document_title"] == "K8s HPA Guide"


@pytest.mark.unit
@pytest.mark.asyncio
class TestEvaluationRunner:
    async def test_run_evaluation(self):
        mock_session = AsyncMock()

        runner = EvaluationRunner(session=mock_session)
        runner.query_service.execute_query = AsyncMock(
            return_value=MagicMock(
                answer="Deploy using Helm chart.",
                citations=[MagicMock(snippet="Helm chart deployment guide.")],
            )
        )

        test_samples = [
            {"question": "How to deploy using Helm?", "ground_truth": "Deploy using Helm chart."}
        ]

        res = await runner.run_evaluation(test_samples, name="Test Run")

        assert res["run_id"] is not None
        assert res["total_samples"] == 1
        assert "overall_score_mean" in res["summary_metrics"]
        assert mock_session.add.called
