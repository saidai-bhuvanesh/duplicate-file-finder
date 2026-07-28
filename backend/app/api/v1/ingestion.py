"""
Ingestion Job management & Connector API endpoints.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.domain.entities.document import SourceSystem

router = APIRouter(prefix="/ingestion", tags=["Ingestion Jobs & Connectors"])
logger = get_logger(__name__, component="ingestion_api")


class DirectoryIngestionRequest(BaseModel):
    directory_path: str = Field(..., description="Absolute path to target directory on server")
    config: dict[str, Any] = Field(default_factory=dict, description="Ingestion options")


class ConnectorIngestionRequest(BaseModel):
    provider: SourceSystem = Field(..., description="Target connector system (confluence, jira, github, slack, notion)")
    target_identifier: str = Field(..., description="Space key, repository name, ticket key, channel, or page ID")
    content: str = Field(..., description="Raw text or JSON payload from the connector")
    title: str | None = Field(default=None, description="Document title")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Connector metadata")


class IngestionJobStatusResponse(BaseModel):
    job_id: str
    task_id: str
    status: str
    message: str


@router.post(
    "/directory",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestionJobStatusResponse,
    summary="Enqueue Directory Ingestion",
)
async def ingest_directory(request: DirectoryIngestionRequest) -> IngestionJobStatusResponse:
    """Enqueue background directory scan and ingestion via Celery worker."""
    job_id = str(uuid.uuid4())
    from app.workers.tasks.ingestion_tasks import ingest_directory_task

    task = ingest_directory_task.delay(
        directory_path=request.directory_path,
        job_id=job_id,
        config=request.config,
    )

    logger.info("directory_ingestion_enqueued", job_id=job_id, task_id=task.id)

    return IngestionJobStatusResponse(
        job_id=job_id,
        task_id=task.id,
        status="queued",
        message=f"Directory ingestion for '{request.directory_path}' queued successfully",
    )


@router.post(
    "/connectors",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestionJobStatusResponse,
    summary="Ingest from Enterprise Connectors",
)
async def ingest_connector(request: ConnectorIngestionRequest) -> IngestionJobStatusResponse:
    """Ingest content from external systems (Confluence, Jira, GitHub, Slack, Notion)."""
    job_id = str(uuid.uuid4())
    from app.workers.tasks.ingestion_tasks import ingest_document_task

    meta = {
        "provider": request.provider.value,
        "target_identifier": request.target_identifier,
        **(request.metadata),
    }

    task = ingest_document_task.delay(
        content=request.content,
        title=request.title or f"{request.provider.value.title()}: {request.target_identifier}",
        source_system=request.provider.value,
        metadata=meta,
        job_id=job_id,
    )

    logger.info("connector_ingestion_enqueued", provider=request.provider.value, task_id=task.id)

    return IngestionJobStatusResponse(
        job_id=job_id,
        task_id=task.id,
        status="queued",
        message=f"Content for connector '{request.provider.value}' queued successfully",
    )
