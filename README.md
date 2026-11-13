# EnterpriseIT-RAG

EnterpriseIT-RAG is a multi-agent retrieval-augmented generation service with a React dashboard, a FastAPI backend, and integrations for PostgreSQL, Redis, Neo4j, and Celery.

## Run with Docker Compose

From the repository root, start the services with:

```powershell
docker compose up --build
```

The dashboard is available at `http://localhost`, and the API documentation is available at `http://localhost:8000/docs` in development mode. The Compose file provides development defaults; configure credentials through environment variables before using it outside a local development environment.

## Run the frontend locally

```powershell
cd frontend
npm ci
npm run dev
```

The Vite development server connects to the API at `http://localhost:8000/api/v1` by default. Set `VITE_API_BASE_URL` to override that URL.

## Run backend checks

```powershell
cd backend
python -m pip install -e ".[dev]"
python -m pytest
```
