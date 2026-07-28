"""
FastAPI Router exposing Adaptive Retrieval Intelligence Engine (ARIE) endpoints.
"""

from __future__ import annotations

from typing import Any, Dict
from pydantic import BaseModel

from fastapi import APIRouter, status

from app.domain.entities.arie import (
    ARIEBenchmarkReport,
    ARIEExplanation,
    QueryIntelligenceResult,
    RetrievalPolicyDecision,
)
from app.retrieval.arie.benchmarking import ARIEBenchmarker
from app.retrieval.arie.explainable import ExplainableRetrievalService
from app.retrieval.arie.figures import PublicationFigureGenerator

router = APIRouter(prefix="/arie", tags=["Adaptive Retrieval Intelligence Engine (ARIE)"])

service = ExplainableRetrievalService()
benchmarker = ARIEBenchmarker(service)
figure_generator = PublicationFigureGenerator()


class ClassifyQueryRequest(BaseModel):
    query: str


@router.post(
    "/classify",
    response_model=QueryIntelligenceResult,
    status_code=status.HTTP_200_OK,
    summary="Step 1: Classify multi-dimensional query intelligence features",
)
async def classify_query(request: ClassifyQueryRequest) -> QueryIntelligenceResult:
    """Classify query intent, complexity, reasoning depth, target data sources, and freshness."""
    return service.intelligence_engine.classify(request.query)


@router.post(
    "/recommend",
    response_model=RetrievalPolicyDecision,
    status_code=status.HTTP_200_OK,
    summary="Step 2: Recommend optimal retrieval policy",
)
async def recommend_policy(request: ClassifyQueryRequest) -> RetrievalPolicyDecision:
    """Determine optimal retrieval strategy among 11 candidate options with cost & latency estimates."""
    intel = service.intelligence_engine.classify(request.query)
    return service.policy_engine.select_policy(intel)


@router.post(
    "/explain",
    response_model=ARIEExplanation,
    status_code=status.HTTP_200_OK,
    summary="Step 3: Generate IEEE explainable retrieval JSON explanation",
)
async def explain_retrieval(request: ClassifyQueryRequest) -> ARIEExplanation:
    """Generate complete structured JSON explanation report for query retrieval selection."""
    return service.explain(request.query)


@router.post(
    "/benchmark",
    response_model=ARIEBenchmarkReport,
    status_code=status.HTTP_200_OK,
    summary="Step 4: Execute 200-query enterprise benchmark evaluation",
)
async def run_benchmark() -> ARIEBenchmarkReport:
    """Run 200-query benchmark evaluation comparing ARIE against static baselines."""
    return benchmarker.run_benchmark()


@router.get(
    "/figures",
    response_model=Dict[str, str],
    status_code=status.HTTP_200_OK,
    summary="Step 5: Fetch publication-ready IEEE figures and diagrams",
)
async def get_publication_figures() -> Dict[str, str]:
    """Return all 8 publication figures (ASCII/SVG diagrams)."""
    return figure_generator.generate_all_figures()
