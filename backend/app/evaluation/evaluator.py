"""
Evaluation Execution Runner orchestrating RAG benchmarks & PostgreSQL persistence.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.query_service import QueryService
from app.core.logging import get_logger
from app.evaluation.metrics import RAGEvaluationMetrics
from app.infrastructure.database.models import EvaluationRunModel, EvaluationSampleModel

logger = get_logger(__name__, component="evaluation_runner")


class EvaluationRunner:
    """
    Executes automated RAG benchmark evaluation runs across test datasets.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.metrics_engine = RAGEvaluationMetrics()
        self.query_service = QueryService(session=session)

    async def run_evaluation(
        self,
        test_samples: list[dict[str, Any]],
        name: str = "Standard RAG Benchmark",
        dataset_name: str = "Synthetic IT Knowledge Dataset",
        rag_variant: str = "hybrid_reranked",
    ) -> dict[str, Any]:
        """
        Execute benchmark run over test samples and save results to PostgreSQL.
        """
        start_time = time.perf_counter()
        run_id = str(uuid.uuid4())

        logger.info("starting_evaluation_run", run_id=run_id, sample_count=len(test_samples))

        samples_results: list[dict[str, Any]] = []
        total_faithfulness = 0.0
        total_relevance = 0.0
        total_precision = 0.0
        total_recall = 0.0
        total_similarity = 0.0
        total_overall = 0.0

        for sample in test_samples:
            s_start = time.perf_counter()
            question = sample["question"]
            ground_truth = sample.get("ground_truth", "")

            # Execute RAG query workflow
            q_result = await self.query_service.execute_query(query_text=question, top_k=5)
            s_latency = (time.perf_counter() - s_start) * 1000

            retrieved_contexts = [c.snippet for c in q_result.citations if c.snippet]
            if not retrieved_contexts:
                retrieved_contexts = [q_result.answer]

            # Compute RAG metrics
            m = self.metrics_engine.compute_all_metrics(
                query=question,
                answer=q_result.answer,
                contexts=retrieved_contexts,
                ground_truth=ground_truth,
            )

            total_faithfulness += m["faithfulness"]
            total_relevance += m["answer_relevance"]
            total_precision += m["context_precision"]
            total_recall += m["context_recall"]
            total_similarity += m["semantic_similarity"]
            total_overall += m["overall_score"]

            sample_model = EvaluationSampleModel(
                id=str(uuid.uuid4()),
                run_id=run_id,
                question=question,
                ground_truth_answer=ground_truth,
                generated_answer=q_result.answer,
                retrieved_contexts=retrieved_contexts,
                citations=[c.to_dict() for c in q_result.citations],
                faithfulness=m["faithfulness"],
                context_precision=m["context_precision"],
                context_recall=m["context_recall"],
                latency_ms=s_latency,
            )
            self.session.add(sample_model)

            samples_results.append({
                "question": question,
                "answer": q_result.answer,
                "metrics": m,
                "latency_ms": round(s_latency, 2),
            })

        count = max(len(test_samples), 1)
        avg_f = round(total_faithfulness / count, 4)
        avg_ar = round(total_relevance / count, 4)
        avg_cp = round(total_precision / count, 4)
        avg_cr = round(total_recall / count, 4)
        avg_ss = round(total_similarity / count, 4)
        avg_ov = round(total_overall / count, 4)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Save Evaluation Run record to PostgreSQL
        run_model = EvaluationRunModel(
            id=run_id,
            name=name,
            rag_variant=rag_variant,
            dataset_name=dataset_name,
            status="completed",
            sample_count=len(test_samples),
            retrieval_metrics={
                "context_precision_mean": avg_cp,
                "context_recall_mean": avg_cr,
            },
            generation_metrics={
                "faithfulness_mean": avg_f,
                "answer_relevance_mean": avg_ar,
                "semantic_similarity_mean": avg_ss,
                "overall_score_mean": avg_ov,
            },
            performance_metrics={
                "latency_p50_ms": round(elapsed_ms / count, 2),
                "total_elapsed_ms": round(elapsed_ms, 2),
            },
            config={"metric_engine": "RAGMetricsEngine_v1"},
        )
        self.session.add(run_model)
        await self.session.commit()

        logger.info(
            "evaluation_run_completed",
            run_id=run_id,
            overall_score=avg_ov,
            samples=len(test_samples),
        )

        return {
            "run_id": run_id,
            "name": name,
            "total_samples": len(test_samples),
            "summary_metrics": {
                "faithfulness_mean": avg_f,
                "answer_relevance_mean": avg_ar,
                "context_precision_mean": avg_cp,
                "context_recall_mean": avg_cr,
                "semantic_similarity_mean": avg_ss,
                "overall_score_mean": avg_ov,
            },
            "elapsed_ms": round(elapsed_ms, 2),
            "samples": samples_results,
        }
