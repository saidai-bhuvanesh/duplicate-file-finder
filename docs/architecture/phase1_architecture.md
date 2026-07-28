# Phase 1 — Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     EnterpriseIT-RAG Platform (Phase 1)                     │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  Client (curl / Postman / Future Next.js)                                    │
│          │                                                                    │
│          ▼ HTTP/HTTPS                                                         │
│  ┌──────────────────────────────────────────────────────────────┐            │
│  │                    FastAPI Application                        │            │
│  │                                                               │            │
│  │  Middleware Stack:                                            │            │
│  │  ┌────────────────┐ ┌──────────────────┐ ┌───────────────┐  │            │
│  │  │ RequestLogging │ │ CORS Middleware   │ │ ExceptionMap  │  │            │
│  │  └────────────────┘ └──────────────────┘ └───────────────┘  │            │
│  │                                                               │            │
│  │  API Routes (v1):                                            │            │
│  │  ┌─────────────┐ ┌──────────────────┐ ┌─────────────────┐  │            │
│  │  │ /health     │ │ /documents       │ │ /search (stub)  │  │            │
│  │  │ /ready      │ │ GET/POST/DELETE  │ │                 │  │            │
│  │  │ /version    │ │ /upload          │ │                 │  │            │
│  │  └─────────────┘ └──────────────────┘ └─────────────────┘  │            │
│  │                                                               │            │
│  │  Dependency Injection (FastAPI Depends):                     │            │
│  │  ┌──────────────────────────────────────────────────────┐   │            │
│  │  │  Settings | AsyncSession | Redis | Repositories      │   │            │
│  │  └──────────────────────────────────────────────────────┘   │            │
│  └──────────────────────────────────────────────────────────────┘            │
│          │                                                                    │
│          ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐            │
│  │                  Application Layer (Services)                 │            │
│  │  ┌──────────────────────────┐  ┌──────────────────────────┐  │            │
│  │  │    DocumentService       │  │    QueryService (Ph.3)   │  │            │
│  │  │  - create_document()     │  │    (stub)                │  │            │
│  │  │  - get_document()        │  │                          │  │            │
│  │  │  - list_documents()      │  │                          │  │            │
│  │  │  - delete_document()     │  │                          │  │            │
│  │  │  - get_statistics()      │  │                          │  │            │
│  │  └──────────────────────────┘  └──────────────────────────┘  │            │
│  └──────────────────────────────────────────────────────────────┘            │
│          │                                                                    │
│          ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐            │
│  │                    Domain Layer                               │            │
│  │                                                               │            │
│  │  Entities:     Document │ Chunk │ Query │ QueryResult        │            │
│  │  Value Objects: EvidenceScore (6-dimensional scoring)        │            │
│  │  Interfaces:   DocumentRepository │ ChunkRepository          │            │
│  │               VectorStore (abstract)                          │            │
│  │  Exceptions:  InsufficientEvidenceError │ HallucinationError │            │
│  └──────────────────────────────────────────────────────────────┘            │
│          │                                                                    │
│          ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐            │
│  │                  Infrastructure Layer                         │            │
│  │                                                               │            │
│  │  ┌─────────────────┐  ┌──────────────┐  ┌────────────────┐  │            │
│  │  │  PostgreSQL      │  │    Redis     │  │   Celery       │  │            │
│  │  │  (SQLAlchemy)    │  │  (cache)     │  │   Workers      │  │            │
│  │  │                  │  │              │  │                │  │            │
│  │  │  documents       │  │  Query cache │  │  ingestion     │  │            │
│  │  │  chunks          │  │  Doc cache   │  │  evaluation    │  │            │
│  │  │  ingestion_jobs  │  │  Emb cache   │  │  cleanup       │  │            │
│  │  │  query_logs      │  │              │  │                │  │            │
│  │  │  eval_runs       │  │              │  │                │  │            │
│  │  └─────────────────┘  └──────────────┘  └────────────────┘  │            │
│  └──────────────────────────────────────────────────────────────┘            │
└───────────────────────────────────────────────────────────────────────────────┘
```

## Clean Architecture Dependency Rule

```
API Layer → Application Layer → Domain Layer ← Infrastructure Layer
```

- Inner layers have **no dependencies** on outer layers
- Domain entities are pure Python dataclasses — no ORM, no FastAPI
- Infrastructure implements domain interfaces (Repository Pattern)
- FastAPI dependencies wire everything together via DI

## Database Schema (Phase 1)

```mermaid
erDiagram
    documents {
        uuid id PK
        string title
        text content
        string document_type
        string source_system
        string status
        string content_hash UK
        int chunk_count
        int token_count
        jsonb metadata
        string ingestion_job_id FK
        text error_message
        datetime indexed_at
        datetime created_at
        datetime updated_at
    }

    ingestion_jobs {
        uuid id PK
        string source_path
        string source_type
        string status
        int total_files
        int processed_files
        int failed_files
        int total_chunks
        jsonb config
        datetime started_at
        datetime completed_at
        datetime created_at
    }

    chunks {
        uuid id PK
        uuid document_id FK
        text content
        string chunk_type
        int chunk_index
        int start_char
        int end_char
        int token_count
        int page_number
        string section_title
        string section_path
        uuid parent_chunk_id FK
        string embedding_model
        jsonb metadata
        datetime created_at
    }

    query_logs {
        uuid id PK
        text query_text
        string query_type
        string retrieval_strategy
        string status
        text answer
        float confidence_score
        float hallucination_risk
        jsonb evidence_quality
        jsonb citations
        jsonb agent_trace
        float total_latency_ms
        int total_tokens_used
        float estimated_cost_usd
        datetime created_at
    }

    evaluation_runs {
        uuid id PK
        string name
        string rag_variant
        string dataset_name
        string status
        jsonb retrieval_metrics
        jsonb generation_metrics
        jsonb performance_metrics
        datetime created_at
    }

    evaluation_samples {
        uuid id PK
        uuid run_id FK
        text question
        text ground_truth_answer
        text generated_answer
        float faithfulness
        float context_recall
        bool hallucination_detected
        datetime created_at
    }

    documents ||--o{ chunks : "has"
    evaluation_runs ||--o{ evaluation_samples : "contains"
```

## Key Design Decisions

1. **PostgreSQL JSONB for metadata** — Avoids schema migrations when adding new source systems. Metadata is queryable with GIN indexes.

2. **Content hash deduplication** — SHA-256 hash prevents duplicate ingestion of identical documents, critical for large enterprise deployments.

3. **Celery task isolation** — Ingestion runs async in separate worker process. API server never blocks on slow operations (PDF parsing, embedding generation).

4. **Repository pattern** — Domain code never imports SQLAlchemy. Repositories map ORM models ↔ domain entities. Enables unit testing without databases.

5. **Frozen EvidenceScore** — Immutable value object prevents accidental mutation of quality scores between agents.

6. **lru_cache settings** — Settings loaded once per process. Tests call `get_settings.cache_clear()` between cases.
