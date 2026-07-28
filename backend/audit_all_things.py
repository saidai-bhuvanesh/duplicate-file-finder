import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def audit():
    items = [
        # Phase 1: Core Backend Foundation
        ("Clean Architecture App Core Config", "d:/MP-5/backend/app/core/config.py"),
        ("Database Models (SQLAlchemy)", "d:/MP-5/backend/app/infrastructure/database/models.py"),
        ("Redis Cache Client", "d:/MP-5/backend/app/infrastructure/cache/redis_client.py"),
        ("6D Evidence Scorecard Value Object", "d:/MP-5/backend/app/domain/value_objects/evidence_score.py"),
        ("FastAPI Main Entrypoint", "d:/MP-5/backend/app/main.py"),
        
        # Phase 2: Document Ingestion Pipeline
        ("Document Loader Registry", "d:/MP-5/backend/app/ingestion/loaders/loader_registry.py"),
        ("Code Loader", "d:/MP-5/backend/app/ingestion/loaders/code_loader.py"),
        ("Slack/Teams Loader", "d:/MP-5/backend/app/ingestion/loaders/slack_teams_loader.py"),
        ("PDF / DOCX Loader", "d:/MP-5/backend/app/ingestion/loaders/pdf_docx_loader.py"),
        ("AST Code Chunkers", "d:/MP-5/backend/app/ingestion/chunkers/code_chunker.py"),
        ("Parent-Child Chunkers", "d:/MP-5/backend/app/ingestion/chunkers/parent_child_chunker.py"),
        ("Celery Task Queue Worker", "d:/MP-5/backend/app/workers/celery_app.py"),
        
        # Phase 3: Hybrid Retrieval Engine
        ("FAISS Vector Store", "d:/MP-5/backend/app/retrieval/vector_store.py"),
        ("BM25 Sparse Search Index", "d:/MP-5/backend/app/retrieval/bm25_index.py"),
        ("RRF Hybrid Fusion Engine", "d:/MP-5/backend/app/retrieval/hybrid_engine.py"),
        ("Evidence Sufficiency Gate", "d:/MP-5/backend/app/retrieval/evidence_gate.py"),
        
        # Phase 4: Knowledge Graph RAG Engine
        ("Neo4j Graph Database Driver", "d:/MP-5/backend/app/infrastructure/database/neo4j_driver.py"),
        ("Graph Entity Extractor & RAG Engine", "d:/MP-5/backend/app/graph/graph_rag.py"),
        ("Graph Entity Synchronization Service", "d:/MP-5/backend/app/graph/graph_service.py"),
        
        # Phase 5: Multi-Agent Orchestration Engine
        ("LangGraph Workflow Engine", "d:/MP-5/backend/app/agents/graph.py"),
        ("Planner Agent", "d:/MP-5/backend/app/agents/planner_agent.py"),
        ("Search Agent", "d:/MP-5/backend/app/agents/search_agent.py"),
        ("Reasoning Agent", "d:/MP-5/backend/app/agents/reasoning_agent.py"),
        ("Generator Agent", "d:/MP-5/backend/app/agents/generator_agent.py"),
        ("Verifier Agent", "d:/MP-5/backend/app/agents/verifier_agent.py"),
        
        # Phase 6: Grounding & Verification Subsystem
        ("NLI Faithfulness Verifier", "d:/MP-5/backend/app/agents/nli_verifier.py"),
        ("Citation Auditor", "d:/MP-5/backend/app/agents/citation_auditor.py"),
        
        # Phase 7: RAG Benchmarking Suite
        ("RAG Metrics Evaluator", "d:/MP-5/backend/app/evaluation/metrics.py"),
        ("Synthetic Testset Generator", "d:/MP-5/backend/app/evaluation/generator.py"),
        ("Benchmarking API Router", "d:/MP-5/backend/app/api/v1/evaluation.py"),
        
        # Phase 8: React Dashboard Frontend
        ("React App Component", "d:/MP-5/frontend/src/App.tsx"),
        ("Search Workspace Component", "d:/MP-5/frontend/src/components/SearchWorkspace.tsx"),
        ("Knowledge Graph Visualizer View", "d:/MP-5/frontend/src/components/KnowledgeGraphView.tsx"),
        ("Ingestion Pipeline Dashboard", "d:/MP-5/frontend/src/components/IngestionDashboard.tsx"),
        ("Benchmarking Suite Evaluation View", "d:/MP-5/frontend/src/components/EvaluationDashboard.tsx"),
        ("Navbar Component", "d:/MP-5/frontend/src/components/Navbar.tsx"),
        
        # Phase 9: Production DevOps & Deployments
        ("Backend Multi-Stage Dockerfile", "d:/MP-5/backend/Dockerfile"),
        ("Frontend Multi-Stage Dockerfile", "d:/MP-5/frontend/Dockerfile"),
        ("Docker Compose Orchestration Manifest", "d:/MP-5/docker-compose.yml"),
        ("Kubernetes Production Deployment", "d:/MP-5/infra/k8s/deployment.yaml"),
        ("GitHub Actions CI/CD Pipeline", "d:/MP-5/.github/workflows/ci.yml"),
        
        # Phase 10: Adaptive Retrieval Intelligence Engine (ARIE)
        ("Query Intelligence Engine (Step 1)", "d:/MP-5/backend/app/retrieval/arie/query_intelligence.py"),
        ("Adaptive Policy Engine (Step 2)", "d:/MP-5/backend/app/retrieval/arie/policy_engine.py"),
        ("Latency & Cost Benchmarking (Step 3)", "d:/MP-5/backend/app/retrieval/arie/benchmarking.py"),
        ("ARIE API Router", "d:/MP-5/backend/app/api/v1/arie.py"),
    ]
    
    found_count = 0
    missing_count = 0
    
    print("=" * 90)
    print("📋 ENTERPRISEIT-RAG SYSTEM-WIDE COMPONENT AUDIT MATRIX")
    print("=" * 90)
    
    for name, path in items:
        exists = os.path.exists(path)
        status = "FOUND ✓" if exists else "MISSING ✗"
        if exists:
            found_count += 1
            size = os.path.getsize(path)
            print(f"[{status}] {name:<45} | Size: {size:>6} B | File: {os.path.basename(path)}")
        else:
            missing_count += 1
            print(f"[{status}] {name:<45} | Path: {path}")

    print("=" * 90)
    print(f"Audit Summary: Total Items Checked: {len(items)} | Found: {found_count} | Missing: {missing_count}")
    print("=" * 90)

if __name__ == "__main__":
    audit()
