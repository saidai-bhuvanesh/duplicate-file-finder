"""
Unit tests for Adaptive Retrieval Intelligence Engine (ARIE) - Phase 10.
"""

import pytest
from fastapi.testclient import TestClient

from app.domain.entities.arie import (
    DataSourceType,
    FreshnessRequirement,
    QueryComplexity,
    QueryIntent,
    RequiredReasoning,
    RetrievalStrategyOption,
)
from app.main import create_app
from app.retrieval.arie.benchmarking import ARIEBenchmarker
from app.retrieval.arie.explainable import ExplainableRetrievalService
from app.retrieval.arie.figures import PublicationFigureGenerator
from app.retrieval.arie.policy_engine import RetrievalPolicyEngine
from app.retrieval.arie.query_intelligence import QueryIntelligenceEngine


class TestQueryIntelligenceEngine:
    """Test Step 1 Query Intelligence Classification."""

    def setup_method(self):
        self.engine = QueryIntelligenceEngine()

    def test_classify_definition_query(self):
        res = self.engine.classify("What is Horizontal Pod Autoscaler (HPA)?")
        assert res.intent == QueryIntent.DEFINITION
        assert res.complexity == QueryComplexity.LOW
        assert res.required_reasoning == RequiredReasoning.SINGLE_DOCUMENT

    def test_classify_troubleshooting_query(self):
        res = self.engine.classify("How to fix PostgreSQL connection pool exhaustion error 53300?")
        assert res.intent == QueryIntent.TROUBLESHOOTING
        assert res.required_reasoning == RequiredReasoning.MULTI_DOCUMENT

    def test_classify_incident_analysis_query(self):
        res = self.engine.classify("Which team owns the payment service that caused Incident #402?")
        assert res.intent in (QueryIntent.INCIDENT_ANALYSIS, QueryIntent.MULTI_HOP_REASONING)
        assert res.required_reasoning == RequiredReasoning.GRAPH_TRAVERSAL

    def test_classify_code_search_query(self):
        res = self.engine.classify("Show Python code for def execute_query with async import")
        assert res.intent == QueryIntent.CODE_SEARCH
        assert res.has_code_syntax is True
        assert DataSourceType.CODE_REPOSITORY in res.target_data_sources

    def test_classify_temporal_freshness(self):
        res = self.engine.classify("Show active incident status for today's outage")
        assert res.freshness == FreshnessRequirement.REAL_TIME
        assert res.has_temporal_keywords is True


class TestRetrievalPolicyEngine:
    """Test Step 2 Retrieval Policy Engine Decision Tree."""

    def setup_method(self):
        self.intel_engine = QueryIntelligenceEngine()
        self.policy_engine = RetrievalPolicyEngine()

    def test_select_policy_graphrag_for_graph_traversal(self):
        intel = self.intel_engine.classify("Which team owns the repository that caused Incident #402?")
        decision = self.policy_engine.select_policy(intel)
        assert decision.selected_strategy == RetrievalStrategyOption.GRAPHRAG
        assert decision.confidence >= 0.90
        assert decision.expected_latency_ms == 180.0

    def test_select_policy_parent_retrieval_for_code(self):
        intel = self.intel_engine.classify("Show OpenAPI payload spec for POST /api/v1/search")
        decision = self.policy_engine.select_policy(intel)
        assert decision.selected_strategy == RetrievalStrategyOption.PARENT_RETRIEVAL

    def test_select_policy_hyde_for_architecture(self):
        intel = self.intel_engine.classify("Explain the high-level microservice architecture and best practices for scaling Kubernetes cluster topology")
        decision = self.policy_engine.select_policy(intel)
        assert decision.selected_strategy == RetrievalStrategyOption.HYDE_RETRIEVAL

    def test_select_policy_dense_faiss_for_low_complexity_definition(self):
        intel = self.intel_engine.classify("What is HPA?")
        decision = self.policy_engine.select_policy(intel)
        assert decision.selected_strategy == RetrievalStrategyOption.DENSE_FAISS


class TestExplainableRetrievalService:
    """Test Step 3 Explainable Retrieval JSON Auditing."""

    def setup_method(self):
        self.service = ExplainableRetrievalService()

    def test_explain_returns_complete_object(self):
        exp = self.service.explain("Compare FAISS vector store vs PostgreSQL pgvector extension")
        assert exp.query == "Compare FAISS vector store vs PostgreSQL pgvector extension"
        assert exp.decision.selected_strategy == RetrievalStrategyOption.CONTEXT_COMPRESSION
        assert exp.decision.confidence > 0.80

    def test_explain_as_json_dict_structure(self):
        json_dict = self.service.explain_as_json("How to fix Nginx 504 gateway timeout?")
        assert "selected_strategy" in json_dict
        assert "reason" in json_dict
        assert "confidence" in json_dict
        assert "expected_latency" in json_dict
        assert "expected_cost" in json_dict
        assert "alternative_strategy" in json_dict
        assert "why_not" in json_dict


class TestARIEBenchmarker:
    """Test Step 4 200-Query Benchmark Suite."""

    def setup_method(self):
        self.benchmarker = ARIEBenchmarker()

    def test_generate_200_enterprise_queries(self):
        queries = self.benchmarker.generate_200_enterprise_queries()
        assert len(queries) == 200

    def test_run_benchmark_metrics(self):
        report = self.benchmarker.run_benchmark()
        assert report.total_samples == 200
        assert report.classification_accuracy >= 0.90
        assert report.mean_precision >= 0.90
        assert "ARIE (Dynamic Router)" in report.baseline_comparisons
        assert "Static: Always Hybrid" in report.baseline_comparisons
        assert "Static: Always BM25" in report.baseline_comparisons
        assert "Static: Always GraphRAG" in report.baseline_comparisons


class TestPublicationFigureGenerator:
    """Test Step 5 Publication Figure Generator."""

    def setup_method(self):
        self.generator = PublicationFigureGenerator()

    def test_generate_all_figures(self):
        figs = self.generator.generate_all_figures()
        assert len(figs) == 8
        assert "architecture_diagram" in figs
        assert "adaptive_retrieval_flowchart" in figs
        assert "decision_tree" in figs
        assert "confusion_matrix" in figs
        assert "latency_comparison" in figs
        assert "precision_comparison" in figs
        assert "token_cost_comparison" in figs
        assert "evidence_radar_chart" in figs


class TestARIERESTEndpoints:
    """Test ARIE REST API endpoints."""

    def setup_method(self):
        app = create_app()
        self.client = TestClient(app)

    def test_classify_endpoint(self):
        response = self.client.post("/api/v1/arie/classify", json={"query": "What is HPA?"})
        assert response.status_code == 200
        data = response.json()
        assert data["intent"] == "definition"

    def test_recommend_endpoint(self):
        response = self.client.post("/api/v1/arie/recommend", json={"query": "Which team owns Incident #402?"})
        assert response.status_code == 200
        data = response.json()
        assert data["selected_strategy"] == "graphrag"

    def test_explain_endpoint(self):
        response = self.client.post("/api/v1/arie/explain", json={"query": "Compare FAISS vs pgvector"})
        assert response.status_code == 200
        data = response.json()
        assert "decision" in data
        assert "intelligence" in data

    def test_figures_endpoint(self):
        response = self.client.get("/api/v1/arie/figures")
        assert response.status_code == 200
        data = response.json()
        assert "confusion_matrix" in data

    def test_benchmark_endpoint(self):
        response = self.client.post("/api/v1/arie/benchmark")
        assert response.status_code == 200
        data = response.json()
        assert data["total_samples"] == 200
        assert data["classification_accuracy"] >= 0.90
