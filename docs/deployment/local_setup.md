# EnterpriseIT-RAG — Local Development Setup Guide

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker Desktop | ≥ 4.x | Infrastructure services |
| Python | 3.11+ | Backend runtime |
| pip | Latest | Package manager |

---

## Step 1: Clone and Configure

```bash
git clone <your-repo-url>
cd MP-5

# Copy environment template
cp backend/.env.example backend/.env
```

Edit `backend/.env` and set your API keys:
```
GROQ_API_KEY=gsk_your_key_here
OPENAI_API_KEY=sk-your_key_here   # Optional fallback
```

---

## Step 2: Start Infrastructure Services

```bash
cd infra
docker compose up -d

# Verify all services are healthy
docker compose ps
```

Expected output:
```
NAME              STATUS
rag_postgres      Up (healthy)
rag_redis         Up (healthy)
rag_neo4j         Up (healthy)
```

Service URLs:
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`
- **Neo4j Browser**: http://localhost:7474 (user: neo4j / pass: neo4j_password)
- **Flower**: http://localhost:5555

---

## Step 3: Install Python Dependencies

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Linux/Mac

# Install all dependencies
pip install -e ".[dev]"

# Download spaCy model
python -m spacy download en_core_web_sm
```

---

## Step 4: Run Database Migrations

```bash
cd backend
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
```

---

## Step 5: Start the API Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Step 6: Start Celery Worker (separate terminal)

```bash
cd backend
.venv\Scripts\activate
celery -A app.workers.celery_app worker --loglevel=info -Q ingestion,default --concurrency=2
```

---

## Step 7: Verify Everything Works

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"...","uptime_seconds":5.2}

# Readiness check (all deps)
curl http://localhost:8000/ready

# Version info
curl http://localhost:8000/version

# API documentation
# Open: http://localhost:8000/docs
```

---

## Step 8: Run Unit Tests

```bash
cd backend

# Run all unit tests (no external dependencies required)
pytest tests/unit/ -v -m unit

# Run with coverage
pytest tests/unit/ -v --cov=app --cov-report=term-missing

# Run everything (integration tests require running services)
pytest tests/ -v
```

---

## Step 9: Ingest Your First Document

```bash
curl -X POST http://localhost:8000/api/v1/documents/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Kubernetes Overview",
    "content": "Kubernetes is an open-source container orchestration system...",
    "document_type": "markdown",
    "source_system": "local_file"
  }'
```

---

## Troubleshooting

### PostgreSQL not starting
```bash
# Check logs
docker compose logs postgres

# Reset volumes
docker compose down -v
docker compose up -d
```

### Alembic migration fails
```bash
# Check DB is reachable
docker compose exec postgres psql -U rag_user -d enterpriseit_rag -c "SELECT 1"

# Run with verbose
alembic upgrade head --sql   # Preview SQL without running
```

### Import errors in Python
```bash
# Make sure you're in the virtual env and backend dir
cd backend
pip install -e ".[dev]"
```

---

## Neo4j Browser

Navigate to http://localhost:7474 and login with:
- **Username**: neo4j
- **Password**: neo4j_password

Phase 4 will populate the graph with entities extracted from your documents.
