"""
Document management API endpoints.

Provides CRUD operations for documents and ingestion job management.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.core.dependencies import DocumentServiceDep, SettingsDep
from app.core.exceptions import DocumentNotFoundError, DuplicateDocumentError
from app.core.logging import get_logger
from app.domain.entities.document import DocumentStatus, DocumentType, SourceSystem

router = APIRouter(prefix="/documents", tags=["Documents"])
logger = get_logger(__name__, component="documents_api")


# ── Request / Response Schemas ────────────────────────────────────────────────


class DocumentCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=1000, description="Document title")
    content: str = Field(..., min_length=1, description="Document text content")
    document_type: DocumentType = Field(..., description="Type of document")
    source_system: SourceSystem = Field(..., description="Source system")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


class DocumentResponse(BaseModel):
    id: str
    title: str
    document_type: str
    source_system: str
    status: str
    content_hash: str
    chunk_count: int
    token_count: int
    word_count: int
    metadata: dict[str, Any]
    error_message: str | None
    created_at: str
    updated_at: str


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class IngestionJobResponse(BaseModel):
    job_id: str
    task_id: str
    status: str
    message: str


# ── Endpoint Implementations ──────────────────────────────────────────────────


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentResponse,
    summary="Ingest a document",
    description="Create and enqueue a document for async ingestion.",
)
async def create_document(
    request: DocumentCreateRequest,
    service: DocumentServiceDep,
    settings: SettingsDep,
) -> DocumentResponse:
    """
    Ingest a new document.

    Steps:
    1. Validate and deduplicate
    2. Persist to PostgreSQL
    3. Dispatch async Celery task for chunking + embedding

    Raises:
        409: If document with same content already exists.
        413: If document exceeds size limit.
    """
    try:
        document = await service.create_document(
            title=request.title,
            content=request.content,
            document_type=request.document_type,
            source_system=request.source_system,
            metadata=request.metadata,
        )

        # Dispatch async ingestion task
        from app.workers.tasks.ingestion_tasks import ingest_document_task
        task = ingest_document_task.delay(
            document_id=document.id,
            content=request.content,
            document_type=request.document_type.value,
            source_system=request.source_system.value,
            metadata=request.metadata,
        )

        logger.info(
            "document_ingestion_dispatched",
            document_id=document.id,
            task_id=task.id,
        )

        return _to_response(document)

    except DuplicateDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": exc.code, "message": exc.message, "details": exc.details},
        )


@router.get(
    "/",
    response_model=DocumentListResponse,
    summary="List documents",
    description="List all documents with optional filtering.",
)
async def list_documents(
    service: DocumentServiceDep,
    doc_status: DocumentStatus | None = Query(None, alias="status"),
    document_type: DocumentType | None = Query(None),
    source_system: SourceSystem | None = Query(None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> DocumentListResponse:
    """List documents with pagination and optional filters."""
    documents, total = await service.list_documents(
        status=doc_status,
        document_type=document_type,
        source_system=source_system,
        limit=limit,
        offset=offset,
    )
    return DocumentListResponse(
        items=[_to_response(d) for d in documents],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document by ID",
)
async def get_document(
    document_id: str,
    service: DocumentServiceDep,
) -> DocumentResponse:
    """Retrieve a single document by its ID."""
    try:
        document = await service.get_document(document_id)
        return _to_response(document)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: str,
    service: DocumentServiceDep,
) -> None:
    """Delete a document and all its chunks."""
    try:
        await service.delete_document(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        )


@router.get(
    "/stats/summary",
    response_model=dict,
    summary="Get document statistics",
)
async def get_document_stats(
    service: DocumentServiceDep,
) -> dict:
    """Return aggregate document statistics."""
    return await service.get_statistics()


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestionJobResponse,
    summary="Upload file for ingestion",
)
async def upload_file(
    file: UploadFile,
    service: DocumentServiceDep,
    settings: SettingsDep,
) -> IngestionJobResponse:
    """
    Upload a file and enqueue it for ingestion.

    Supported formats: PDF, DOCX, Markdown, HTML, CSV, JSON, YAML.
    Phase 2 will add full file type detection and parsing.
    """
    import uuid
    content = await file.read()
    content_text = content.decode("utf-8", errors="replace")

    # Determine document type from extension
    ext = (file.filename or "").lower().split(".")[-1]
    type_map = {
        "pdf": DocumentType.PDF,
        "docx": DocumentType.DOCX,
        "md": DocumentType.MARKDOWN,
        "html": DocumentType.HTML,
        "csv": DocumentType.CSV,
        "json": DocumentType.JSON,
        "yaml": DocumentType.YAML,
        "yml": DocumentType.YAML,
    }
    doc_type = type_map.get(ext, DocumentType.TEXT)

    try:
        document = await service.create_document(
            title=file.filename or "Uploaded File",
            content=content_text,
            document_type=doc_type,
            source_system=SourceSystem.LOCAL_FILE,
        )

        from app.workers.tasks.ingestion_tasks import ingest_document_task
        task = ingest_document_task.delay(
            document_id=document.id,
            content=content_text,
            document_type=doc_type.value,
            source_system=SourceSystem.LOCAL_FILE.value,
            metadata={"filename": file.filename},
        )

        return IngestionJobResponse(
            job_id=document.id,
            task_id=task.id,
            status="queued",
            message=f"File '{file.filename}' queued for ingestion",
        )
    except DuplicateDocumentError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A document with identical content already exists",
        )


# ── Helper ────────────────────────────────────────────────────────────────────


def _to_response(document: Any) -> DocumentResponse:
    """Convert domain entity to API response model."""
    return DocumentResponse(
        id=document.id,
        title=document.title,
        document_type=document.document_type.value,
        source_system=document.metadata.source_system.value,
        status=document.status.value,
        content_hash=document.content_hash,
        chunk_count=document.chunk_count,
        token_count=document.token_count,
        word_count=document.word_count,
        metadata=document.metadata.to_dict(),
        error_message=document.error_message,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
    )
