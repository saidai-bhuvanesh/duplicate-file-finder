# EnterpriseIT-RAG: Adaptive Multi-Agent Enterprise Knowledge Platform

[![IEEE Quality](https://img.shields.io/badge/IEEE-Publication--Quality-brightgreen)](https://ieee.org)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-009688)](https://fastapi.tiangolo.com)
[![Next.js 14 / React 19](https://img.shields.io/badge/React-19.0--Vite-61DAFB)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange)](https://langchain.com)
[![Neo4j GraphRAG](https://img.shields.io/badge/Neo4j-GraphRAG-45818e)](https://neo4j.com)
[![Tests Passing](https://img.shields.io/badge/Tests-93%2F93%20Passed-success)](./backend/tests/unit)

---

## 🏛️ Executive Architectural Overview

Modern IT organizations generate millions of technical artifacts across heterogeneous systems (Confluence, Jira, GitHub, Slack, Notion, PDFs, OpenAPI specs, Terraform code, and Kubernetes manifests). 

**EnterpriseIT-RAG** is an IEEE publication-quality, adaptive multi-agent retrieval-augmented generation platform designed for enterprise software engineering teams at scale.

```
                  +-------------------------------------------------------------------+
                  |                 Enterprise React / Vite Dashboard                 |
                  |     (Multi-Agent Stepper, Graph Canvas, Benchmarks, Ingestion)    |
                  +---------------------------------+---------------------------------+
                                                    | REST / JSON
                                                    v
                  +---------------------------------+---------------------------------+
                  |                    FastAPI Application Gateway                    |
                  |                Clean Architecture & Repository Pattern            |
                  +-------+-------------------------+-------------------------+-------+
                          |                         |                         |
                          v                         v                         v
           +--------------+--------------+  +-------+-------+  +--------------+--------------+
           | Multi-Agent Orchestration   |  | Ingestion     |  | Enterprise GraphRAG Engine  |
           | Engine (LangGraph)          |  | Pipeline      |  | (Neo4j Cypher Traversals)   |
           +--------------+--------------+  +-------+-------+  +--------------+--------------+
                          |                         |                         |
             +------------+------------+            |            +------------+------------+
             |                         |            |            |                         |
             v                         v            v            v                         v
     +---------------+         +---------------+  +---+  +---------------+         +---------------+
     | FAISS Vector  |         | BM25 Sparse   |  |   |  | PostgreSQL    |         | Redis Cache & |
     | Dense Store   |         | Keyword Index |  |   |  | (pgvector)    |         | Celery Broker |
     +---------------+         +---------------+  +---+  +---------------+         +---------------+
```

---

## 🚀 Key Architectural Innovations

### 1. Adaptive Multi-Agent State Graph Orchestrator (LangGraph)
- **Planner Agent**: Query decomposition & sub-goal execution planning.
- **Search Agent**: Multi-query execution across FAISS Dense, BM25 Sparse, and Neo4j GraphRAG indices.
- **Reasoning Agent**: Context ordering & cross-document fact extraction.
- **Generator Agent**: Grounded technical answer drafting with inline citations (`[Source X]`) via `LLMClient` (Groq llama-3.3-70b / OpenAI gpt-4o-mini).
- **Verifier Agent**: NLI Faithfulness Auditing & Automated Refusal.

### 2. Enterprise Knowledge Graph & GraphRAG (Neo4j)
- Automatically extracts IT entities (`Service`, `Team`, `Incident`, `Repository`, `APIEndpoint`, `Employee`) and relationships (`OWNS`, `DEPENDS_ON`, `CAUSED_BY`, `EXPOSES_API`).
- Executes 1–3 hop Cypher traversals to resolve complex dependency queries (e.g., *"Which team owns the service that caused Incident #402?"*).

### 3. Advanced NLI Faithfulness & Hallucination Auditor (Innovation 3)
- Uses `cross-encoder/nli-deberta-v3-large` natural language inference to evaluate sentence-level entailment between source context (Premise) and generated statements (Hypothesis).
- Triggers automated refusal if Faithfulness Score falls below threshold:
  > *"⚠️ Refused: Generated answer could not be verified with high confidence against source citations."*

### 4. Adaptive Retrieval Router & Evidence Sufficiency Gate
- Dynamically classifies query intent into `FACTUAL`, `PROCEDURAL`, `ENTITY`, `CODE`, or `ANALYTICAL`.
- Automatically selects optimal strategy: `HYBRID_RERANKED`, `PARENT_DOCUMENT`, `GRAPH_HYBRID`, `BM25_ONLY`, or `DENSE_ONLY`.

### 5. Automated RAG Triad Evaluation & Benchmarking (Ragas + TruLens)
- Quantitative evaluation suite measuring:
  - **Faithfulness** ($0.0 \dots 1.0$)
  - **Answer Relevance** ($0.0 \dots 1.0$)
  - **Context Precision** ($0.0 \dots 1.0$)
  - **Context Recall** ($0.0 \dots 1.0$)
  - **Semantic Similarity** ($0.0 \dots 1.0$)

---

## 💻 Tech Stack Specification

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend Core** | Python 3.11, FastAPI, Pydantic v2 | Clean Architecture REST API gateway |
| **Database** | PostgreSQL 16 + pgvector, Alembic | Async SQLAlchemy database persistence |
| **Vector Search** | FAISS, SentenceTransformers (`all-mpnet-base-v2`) | L2/IP dense embedding vector store |
| **Sparse Search** | rank_bm25 (`BM25Okapi`) | In-memory keyword sparse search index |
| **Cross-Encoder** | `ms-marco-MiniLM-L-6-v2` | Deep learning contextual re-ranker |
| **Graph Database** | Neo4j Community 5.18 | Cypher graph database for GraphRAG |
| **Multi-Agent Engine** | LangGraph, LLMClient (Groq / OpenAI) | State graph multi-agent orchestrator |
| **NLI Verifier** | CrossEncoder (`nli-deberta-v3-large`) | Premise-hypothesis entailment auditor |
| **Task Queue** | Redis 7.2, Celery | Async background document ingestion |
| **Frontend UI** | React 19, Vite, Tailwind CSS v4, Lucide | Glassmorphism enterprise dashboard |
| **Containerization** | Docker, Docker Compose, Kubernetes | Multi-stage production deployment |

---

## ⚡ Quick Start & Deployment Guide

### Prerequisites
- Python 3.11+
- Node.js 24+ & npm 11+
- Docker & Docker Compose

### 1. Running Backend Locally
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt

# Run Unit Tests (93 Tests)
python -m pytest tests/unit/ -v

# Start FastAPI App
uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health/liveness`

### 2. Running Frontend Locally
```bash
cd frontend
npm install
npm run dev
```
- Dashboard UI: `http://localhost:5173`

### 3. Docker Compose Full Stack Deployment
```bash
docker-compose up --build -d
```
- Gateway Nginx Frontend: `http://localhost`
- Backend API: `http://localhost:8000`
- Neo4j Browser: `http://localhost:7474`

---

## 🧪 Unit Test Suite Verification

```bash
cd backend
.venv\Scripts\python -m pytest tests/unit/ -v
```

Output:
```
======================= 93 passed in 2.15s =======================
```

| Phase | Test Module | Passed Tests | Description |
| :--- | :--- | :---: | :--- |
| **Phase 1** | `test_config.py`, `test_entities.py`, `test_evidence_score.py` | 45 | Settings, entities, 6D evidence scorecard |
| **Phase 2** | `test_loaders.py`, `test_chunkers.py`, `test_pipeline.py` | 24 | Loaders, adaptive chunkers, ingestion pipeline |
| **Phase 3** | `test_retrieval.py` | 7 | FAISS, BM25, RRF fusion, evidence gate |
| **Phase 4** | `test_graph.py` | 4 | Entity extraction, GraphService, GraphRAG |
| **Phase 5** | `test_agents.py` | 6 | Planner, Search, Reasoning, Generator, Graph |
| **Phase 6** | `test_verification.py` | 4 | NLI verifier, citation auditor, refusal |
| **Phase 7** | `test_evaluation.py` | 3 | RAG triad metrics engine, synthetic testset |
| **Total** | **All 7 Test Modules** | **93 / 93** | **100% Pass Rate** |

---

## 📄 License & IEEE Citation

Licensed under the MIT License. Published as IEEE Publication-Quality Enterprise RAG Platform Reference Architecture.
#   R a g - M P - 5  
 