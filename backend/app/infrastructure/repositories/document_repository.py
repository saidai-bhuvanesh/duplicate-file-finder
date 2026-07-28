"""
PostgreSQL implementation of DocumentRepository.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError
from app.core.logging import get_logger
from app.domain.entities.document import (
    Document,
    DocumentMetadata,
    DocumentStatus,
    DocumentType,
    SourceSystem,
)
from app.domain.interfaces.document_repository import DocumentRepository
from app.infrastructure.database.models import DocumentModel

logger = get_logger(__name__, component="document_repository")


class PostgresDocumentRepository(DocumentRepository):
    """PostgreSQL-backed document repository using SQLAlchemy async."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        try:
            model = self._to_model(document)
            self._session.add(model)
            await self._session.flush()
            logger.info("document_created", document_id=document.id, title=document.title)
            return self._to_entity(model)
        except Exception as exc:
            logger.error("document_create_failed", error=str(exc), document_id=document.id)
            raise DatabaseError(f"Failed to create document: {exc}", operation="create") from exc

    async def get_by_id(self, document_id: str) -> Document | None:
        try:
            result = await self._session.get(DocumentModel, document_id)
            return self._to_entity(result) if result else None
        except Exception as exc:
            raise DatabaseError(f"Failed to get document: {exc}", operation="get_by_id") from exc

    async def get_by_content_hash(self, content_hash: str) -> Document | None:
        try:
            stmt = select(DocumentModel).where(DocumentModel.content_hash == content_hash)
            result = await self._session.execute(stmt)
            model = result.scalar_one_or_none()
            return self._to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseError(
                f"Failed to get document by hash: {exc}", operation="get_by_content_hash"
            ) from exc

    async def update(self, document: Document) -> Document:
        try:
            model = await self._session.get(DocumentModel, document.id)
            if not model:
                raise DatabaseError(
                    f"Document not found for update: {document.id}", operation="update"
                )
            model.title = document.title
            model.content = document.content
            model.status = document.status.value
            model.chunk_count = document.chunk_count
            model.token_count = document.token_count
            model.metadata_ = document.metadata.to_dict()
            model.error_message = document.error_message
            model.indexed_at = document.indexed_at
            model.updated_at = datetime.utcnow()
            await self._session.flush()
            return self._to_entity(model)
        except DatabaseError:
            raise
        except Exception as exc:
            raise DatabaseError(f"Failed to update document: {exc}", operation="update") from exc

    async def delete(self, document_id: str) -> bool:
        try:
            model = await self._session.get(DocumentModel, document_id)
            if not model:
                return False
            await self._session.delete(model)
            await self._session.flush()
            logger.info("document_deleted", document_id=document_id)
            return True
        except Exception as exc:
            raise DatabaseError(f"Failed to delete document: {exc}", operation="delete") from exc

    async def list(
        self,
        status: DocumentStatus | None = None,
        document_type: DocumentType | None = None,
        source_system: SourceSystem | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        try:
            stmt = select(DocumentModel)
            count_stmt = select(func.count()).select_from(DocumentModel)

            if status:
                stmt = stmt.where(DocumentModel.status == status.value)
                count_stmt = count_stmt.where(DocumentModel.status == status.value)
            if document_type:
                stmt = stmt.where(DocumentModel.document_type == document_type.value)
                count_stmt = count_stmt.where(DocumentModel.document_type == document_type.value)
            if source_system:
                stmt = stmt.where(DocumentModel.source_system == source_system.value)
                count_stmt = count_stmt.where(DocumentModel.source_system == source_system.value)
            if tags:
                # PostgreSQL JSONB array containment
                stmt = stmt.where(DocumentModel.metadata_["tags"].astext.contains(str(tags[0])))

            stmt = stmt.order_by(DocumentModel.created_at.desc()).limit(limit).offset(offset)

            results = await self._session.execute(stmt)
            models = results.scalars().all()
            count_result = await self._session.execute(count_stmt)
            total = count_result.scalar_one()

            return [self._to_entity(m) for m in models], total
        except Exception as exc:
            raise DatabaseError(f"Failed to list documents: {exc}", operation="list") from exc

    async def count(
        self,
        status: DocumentStatus | None = None,
        source_system: SourceSystem | None = None,
    ) -> int:
        try:
            stmt = select(func.count()).select_from(DocumentModel)
            if status:
                stmt = stmt.where(DocumentModel.status == status.value)
            if source_system:
                stmt = stmt.where(DocumentModel.source_system == source_system.value)
            result = await self._session.execute(stmt)
            return result.scalar_one()
        except Exception as exc:
            raise DatabaseError(f"Failed to count documents: {exc}", operation="count") from exc

    async def search_by_title(self, query: str, limit: int = 10) -> list[Document]:
        try:
            stmt = (
                select(DocumentModel)
                .where(DocumentModel.title.ilike(f"%{query}%"))
                .limit(limit)
            )
            result = await self._session.execute(stmt)
            return [self._to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseError(
                f"Failed to search documents by title: {exc}", operation="search_by_title"
            ) from exc

    async def get_stale_documents(self, max_age_days: int) -> list[Document]:
        try:
            from datetime import timedelta
            cutoff_dt = datetime.utcnow() - timedelta(days=max_age_days)
            stmt = select(DocumentModel).where(
                DocumentModel.status == DocumentStatus.INDEXED.value,
                DocumentModel.updated_at < cutoff_dt,
            )
            result = await self._session.execute(stmt)
            return [self._to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseError(
                f"Failed to get stale documents: {exc}", operation="get_stale_documents"
            ) from exc

    async def bulk_update_status(
        self, document_ids: list[str], status: DocumentStatus
    ) -> int:
        try:
            stmt = (
                update(DocumentModel)
                .where(DocumentModel.id.in_(document_ids))
                .values(status=status.value, updated_at=datetime.utcnow())
            )
            result = await self._session.execute(stmt)
            return result.rowcount
        except Exception as exc:
            raise DatabaseError(
                f"Failed to bulk update status: {exc}", operation="bulk_update_status"
            ) from exc

    # ── Mapper Methods ────────────────────────────────────────────────────────

    def _to_model(self, entity: Document) -> DocumentModel:
        """Convert domain entity to ORM model."""
        return DocumentModel(
            id=entity.id,
            title=entity.title,
            content=entity.content,
            document_type=entity.document_type.value,
            source_system=entity.metadata.source_system.value,
            status=entity.status.value,
            content_hash=entity.content_hash,
            chunk_count=entity.chunk_count,
            token_count=entity.token_count,
            metadata_=entity.metadata.to_dict(),
            ingestion_job_id=entity.ingestion_job_id,
            error_message=entity.error_message,
            indexed_at=entity.indexed_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def _to_entity(self, model: DocumentModel) -> Document:
        """Convert ORM model to domain entity."""
        meta = model.metadata_ or {}
        metadata = DocumentMetadata(
            source_system=SourceSystem(meta.get("source_system", "local_file")),
            source_url=meta.get("source_url"),
            source_path=meta.get("source_path"),
            author=meta.get("author"),
            authors=meta.get("authors", []),
            version=meta.get("version"),
            language=meta.get("language", "en"),
            tags=meta.get("tags", []),
            project=meta.get("project"),
            team=meta.get("team"),
            repository=meta.get("repository"),
            branch=meta.get("branch"),
            commit_hash=meta.get("commit_hash"),
            space=meta.get("space"),
            page_id=meta.get("page_id"),
            ticket_key=meta.get("ticket_key"),
            channel=meta.get("channel"),
        )
        return Document(
            id=model.id,
            title=model.title,
            content=model.content,
            document_type=DocumentType(model.document_type),
            status=DocumentStatus(model.status),
            metadata=metadata,
            content_hash=model.content_hash,
            chunk_count=model.chunk_count,
            token_count=model.token_count,
            ingestion_job_id=model.ingestion_job_id,
            error_message=model.error_message,
            indexed_at=model.indexed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
