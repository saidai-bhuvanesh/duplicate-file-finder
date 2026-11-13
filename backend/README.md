# EnterpriseIT-RAG Backend

FastAPI service for document ingestion, retrieval, knowledge graph queries, and RAG evaluation.

## Local development

Install the project and its development dependencies from this directory:

```powershell
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

Run the backend tests with:

```powershell
python -m pytest
```

PostgreSQL, Redis, and Neo4j are required for their corresponding live API features. The root `docker-compose.yml` defines the local service stack.
