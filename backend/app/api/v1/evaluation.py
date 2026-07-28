"""
Evaluation & Benchmarking REST API endpoints.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import DatabaseSessionDep
from app.core.logging import get_logger
from app.evaluation.evaluator import EvaluationRunner
from app.evaluation.generator import SyntheticTestsetGenerator
from app.infrastructure.database.models import DocumentModel, EvaluationRunModel, EvaluationSampleModel

router = APIRouter(prefix="/evaluation", tags=["Evaluation & Benchmarking"])
logger = get_logger(__name__, component="evaluation_api")


class EvalSampleInput(BaseModel):
    question: str = Field(..., description="Evaluation question")
    ground_truth: str = Field(..., description="Ideal ground-truth answer")


class TriggerEvalRunRequest(BaseModel):
    name: str = Field(default="RAG Benchmark Run", description="Name of evaluation run")
    dataset_name: str = Field(default="Synthetic Dataset", description="Dataset identifier")
    rag_variant: str = Field(default="hybrid_reranked", description="RAG strategy variant name")
    samples: list[EvalSampleInput] = Field(default_factory=list, description="Custom test samples")


class GenerateTestsetRequest(BaseModel):
    document_ids: list[str] = Field(default_factory=list, description="Target document IDs")
    num_samples_per_doc: int = Field(default=2, ge=1, le=5)


@router.post(
    "/runs",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Automated RAG Evaluation Run",
)
async def trigger_eval_run(
    request: TriggerEvalRunRequest,
    session: DatabaseSessionDep,
) -> dict:
    """Trigger an automated benchmark evaluation run across test samples."""
    eval_runner = EvaluationRunner(session=session)

    # Use provided test samples or fallback defaults
    test_samples = [
        {"question": s.question, "ground_truth": s.ground_truth}
        for s in request.samples
    ]
    if not test_samples:
        test_samples = [
            {
                "question": "What is the architecture of the enterprise platform?",
                "ground_truth": "The platform uses a microservices architecture deployed on Kubernetes.",
            },
            {
                "question": "How does the system handle document deduplication?",
                "ground_truth": "Document deduplication is enforced using SHA-256 content hashing in PostgreSQL.",
            },
        ]

    result = await eval_runner.run_evaluation(
        test_samples=test_samples,
        name=request.name,
        dataset_name=request.dataset_name,
        rag_variant=request.rag_variant,
    )
    return result


@router.get(
    "/runs",
    response_model=list[dict],
    summary="List Historical Evaluation Runs",
)
async def list_eval_runs(session: DatabaseSessionDep) -> list[dict]:
    """List historical benchmark evaluation runs and aggregate scores."""
    stmt = select(EvaluationRunModel).order_by(EvaluationRunModel.created_at.desc()).limit(20)
    result = await session.execute(stmt)
    runs = result.scalars().all()

    return [
        {
            "run_id": r.id,
            "name": r.name,
            "dataset_name": r.dataset_name,
            "rag_variant": r.rag_variant,
            "sample_count": r.sample_count,
            "generation_metrics": r.generation_metrics,
            "retrieval_metrics": r.retrieval_metrics,
            "performance_metrics": r.performance_metrics,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.get(
    "/runs/{run_id}",
    response_model=dict,
    summary="Get Evaluation Run Details",
)
async def get_eval_run_details(run_id: str, session: DatabaseSessionDep) -> dict:
    """Get sample-level metric scores for a specific evaluation run."""
    run_stmt = select(EvaluationRunModel).where(EvaluationRunModel.id == run_id)
    run_res = await session.execute(run_stmt)
    eval_run = run_res.scalar_one_or_none()

    if not eval_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evaluation run '{run_id}' not found")

    samples_stmt = select(EvaluationSampleModel).where(EvaluationSampleModel.run_id == run_id)
    samples_res = await session.execute(samples_stmt)
    samples = samples_res.scalars().all()

    return {
        "run_id": eval_run.id,
        "name": eval_run.name,
        "dataset_name": eval_run.dataset_name,
        "rag_variant": eval_run.rag_variant,
        "generation_metrics": eval_run.generation_metrics,
        "retrieval_metrics": eval_run.retrieval_metrics,
        "performance_metrics": eval_run.performance_metrics,
        "samples": [
            {
                "sample_id": s.id,
                "question": s.question,
                "ground_truth": s.ground_truth_answer,
                "generated_answer": s.generated_answer,
                "faithfulness": s.faithfulness,
                "context_precision": s.context_precision,
                "context_recall": s.context_recall,
                "latency_ms": s.latency_ms,
            }
            for s in samples
        ],
    }


@router.post(
    "/generate-testset",
    response_model=dict,
    summary="Generate Synthetic QA Testset",
)
async def generate_testset(
    request: GenerateTestsetRequest,
    session: DatabaseSessionDep,
) -> dict:
    """Generate synthetic ground-truth QA test pairs from ingested documents."""
    generator = SyntheticTestsetGenerator()

    if request.document_ids:
        stmt = select(DocumentModel).where(DocumentModel.id.in_(request.document_ids))
    else:
        stmt = select(DocumentModel).limit(5)

    result = await session.execute(stmt)
    doc_models = result.scalars().all()

    all_samples = []
    for d in doc_models:
        from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
        doc_entity = Document(
            id=d.id,
            title=d.title,
            content=d.content,
            document_type=DocumentType(d.document_type),
            metadata=DocumentMetadata.from_dict(d.metadata_json, source_system=SourceSystem(d.source_system)),
        )
        samples = await generator.generate_test_samples_from_document(
            doc_entity, num_samples=request.num_samples_per_doc
        )
        all_samples.extend(samples)

    return {
        "generated_samples_count": len(all_samples),
        "samples": all_samples,
    }
