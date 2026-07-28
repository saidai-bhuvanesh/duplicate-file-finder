"""
Ingestion Celery tasks.

Async tasks for document processing pipeline:
- ingest_document_task: Process a single document through full IngestionPipeline
- ingest_directory_task: Process a directory of files
- cleanup_stale_jobs: Periodic cleanup
"""

from __future__ import annotations

import os
import traceback
from typing import Any

from celery import Task
from celery.utils.log import get_task_logger

from app.workers.celery_app import celery_app

task_logger = get_task_logger(__name__)


class CallbackTask(Task):
    """Base task class with structured error handling."""

    def on_failure(self, exc: Exception, task_id: str, args: Any, kwargs: Any, einfo: Any) -> None:
        task_logger.error(
            f"Task {self.name} [{task_id}] failed: {exc}",
            extra={
                "task_id": task_id,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            },
        )

    def on_success(self, retval: Any, task_id: str, args: Any, kwargs: Any) -> None:
        task_logger.info(f"Task {self.name} [{task_id}] completed successfully")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="app.workers.tasks.ingestion_tasks.ingest_document",
    queue="ingestion",
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def ingest_document_task(
    self: Task,
    content: str,
    title: str | None = None,
    document_type: str = "text",
    source_system: str = "local_file",
    metadata: dict[str, Any] | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """
    Process a single document through the full IngestionPipeline asynchronously.
    """
    import asyncio

    task_logger.info(f"Starting ingestion task for title: {title}")

    async def _run() -> dict[str, Any]:
        from app.domain.entities.document import SourceSystem
        from app.infrastructure.database.connection import AsyncSessionFactory
        from app.infrastructure.repositories.chunk_repository import PostgresChunkRepository
        from app.infrastructure.repositories.document_repository import PostgresDocumentRepository
        from app.ingestion.pipeline import IngestionPipeline

        async with AsyncSessionFactory() as session:
            doc_repo = PostgresDocumentRepository(session)
            chunk_repo = PostgresChunkRepository(session)
            pipeline = IngestionPipeline(doc_repo, chunk_repo)

            src_sys = SourceSystem(source_system) if source_system in [s.value for s in SourceSystem] else SourceSystem.LOCAL_FILE

            saved_doc, saved_chunks = await pipeline.run(
                source=content,
                title=title,
                metadata=metadata,
                source_system=src_sys,
                job_id=job_id,
            )
            await session.commit()

            return {
                "document_id": saved_doc.id,
                "chunk_count": len(saved_chunks),
                "status": saved_doc.status.value,
            }

    try:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(_run())
    except Exception as exc:
        task_logger.error(f"Ingestion failed: {exc}")
        raise self.retry(exc=exc)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="app.workers.tasks.ingestion_tasks.ingest_directory",
    queue="ingestion",
    max_retries=2,
    acks_late=True,
)
def ingest_directory_task(
    self: Task,
    directory_path: str,
    job_id: str,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Scan and process all supported documents in a directory recursively.
    """
    import asyncio

    task_logger.info(f"Processing directory: {directory_path}, job: {job_id}")

    async def _run() -> dict[str, Any]:
        from app.domain.entities.document import SourceSystem
        from app.infrastructure.database.connection import AsyncSessionFactory
        from app.infrastructure.repositories.chunk_repository import PostgresChunkRepository
        from app.infrastructure.repositories.document_repository import PostgresDocumentRepository
        from app.ingestion.pipeline import IngestionPipeline

        if not os.path.exists(directory_path):
            raise ValueError(f"Directory path does not exist: {directory_path}")

        processed = 0
        failed = 0
        total_chunks = 0

        async with AsyncSessionFactory() as session:
            doc_repo = PostgresDocumentRepository(session)
            chunk_repo = PostgresChunkRepository(session)
            pipeline = IngestionPipeline(doc_repo, chunk_repo)

            for root, _, files in os.walk(directory_path):
                for f in files:
                    file_path = os.path.join(root, f)
                    try:
                        ext = os.path.splitext(f)[1]
                        meta = {
                            "filename": f,
                            "file_extension": ext,
                            "source_path": file_path,
                            **(config or {}),
                        }
                        saved_doc, chunks = await pipeline.run(
                            source=file_path,
                            title=f,
                            metadata=meta,
                            source_system=SourceSystem.LOCAL_FILE,
                            job_id=job_id,
                        )
                        processed += 1
                        total_chunks += len(chunks)
                    except Exception as exc:
                        task_logger.warning(f"Failed to ingest file {file_path}: {exc}")
                        failed += 1

            await session.commit()

        return {
            "job_id": job_id,
            "directory_path": directory_path,
            "processed_files": processed,
            "failed_files": failed,
            "total_chunks": total_chunks,
            "status": "completed",
        }

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@celery_app.task(
    name="app.workers.tasks.ingestion_tasks.cleanup_stale_jobs",
    queue="default",
)
def cleanup_stale_jobs() -> dict[str, Any]:
    """
    Periodic task: clean up stuck ingestion jobs older than 24 hours.
    """
    import asyncio

    async def _cleanup() -> dict[str, Any]:
        from sqlalchemy import text, update
        from app.infrastructure.database.connection import AsyncSessionFactory
        from app.infrastructure.database.models import IngestionJobModel

        async with AsyncSessionFactory() as session:
            stmt = (
                update(IngestionJobModel)
                .where(
                    IngestionJobModel.status == "running",
                    IngestionJobModel.started_at < text("NOW() - INTERVAL '24 hours'"),
                )
                .values(status="failed", error_message="Job timed out")
            )
            result = await session.execute(stmt)
            await session.commit()
            return {"stale_jobs_cleaned": result.rowcount}

    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(_cleanup())
        task_logger.info(f"Cleanup complete: {result}")
        return result
    finally:
        loop.close()
