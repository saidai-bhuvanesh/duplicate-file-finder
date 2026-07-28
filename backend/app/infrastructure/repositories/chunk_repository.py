"""
PostgreSQL implementation of ChunkRepository.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseError
from app.core.logging import get_logger
from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.interfaces.chunk_repository import ChunkRepository
from app.infrastructure.database.models import ChunkModel

logger = get_logger(__name__, component="chunk_repository")


class PostgresChunkRepository(ChunkRepository):
    """PostgreSQL-backed chunk repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, chunks: list[Chunk]) -> list[Chunk]:
        try:
            models = [self._to_model(c) for c in chunks]
            self._session.add_all(models)
            await self._session.flush()
            logger.info("chunks_created", count=len(chunks))
            return [self._to_entity(m) for m in models]
        except Exception as exc:
            raise DatabaseError(
                f"Failed to bulk create chunks: {exc}", operation="create_many"
            ) from exc

    async def get_by_id(self, chunk_id: str) -> Chunk | None:
        try:
            model = await self._session.get(ChunkModel, chunk_id)
            return self._to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseError(f"Failed to get chunk: {exc}", operation="get_by_id") from exc

    async def get_by_document_id(self, document_id: str) -> list[Chunk]:
        try:
            stmt = (
                select(ChunkModel)
                .where(ChunkModel.document_id == document_id)
                .order_by(ChunkModel.chunk_index)
            )
            result = await self._session.execute(stmt)
            return [self._to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseError(
                f"Failed to get chunks for document: {exc}", operation="get_by_document_id"
            ) from exc

    async def get_parent_chunk(self, chunk_id: str) -> Chunk | None:
        try:
            child = await self._session.get(ChunkModel, chunk_id)
            if not child or not child.parent_chunk_id:
                return None
            parent = await self._session.get(ChunkModel, child.parent_chunk_id)
            return self._to_entity(parent) if parent else None
        except Exception as exc:
            raise DatabaseError(
                f"Failed to get parent chunk: {exc}", operation="get_parent_chunk"
            ) from exc

    async def get_surrounding_chunks(self, chunk_id: str, window: int = 1) -> list[Chunk]:
        try:
            target = await self._session.get(ChunkModel, chunk_id)
            if not target:
                return []

            min_idx = max(0, target.chunk_index - window)
            max_idx = target.chunk_index + window

            stmt = (
                select(ChunkModel)
                .where(
                    ChunkModel.document_id == target.document_id,
                    ChunkModel.chunk_index >= min_idx,
                    ChunkModel.chunk_index <= max_idx,
                    ChunkModel.parent_chunk_id == None,  # noqa: E711
                )
                .order_by(ChunkModel.chunk_index)
            )
            result = await self._session.execute(stmt)
            return [self._to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseError(
                f"Failed to get surrounding chunks: {exc}", operation="get_surrounding_chunks"
            ) from exc

    async def delete_by_document_id(self, document_id: str) -> int:
        try:
            stmt = select(ChunkModel).where(ChunkModel.document_id == document_id)
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            for model in models:
                await self._session.delete(model)
            await self._session.flush()
            return len(models)
        except Exception as exc:
            raise DatabaseError(
                f"Failed to delete chunks: {exc}", operation="delete_by_document_id"
            ) from exc

    async def count_by_document_id(self, document_id: str) -> int:
        try:
            from sqlalchemy import func
            stmt = (
                select(func.count())
                .select_from(ChunkModel)
                .where(ChunkModel.document_id == document_id)
            )
            result = await self._session.execute(stmt)
            return result.scalar_one()
        except Exception as exc:
            raise DatabaseError(
                f"Failed to count chunks: {exc}", operation="count_by_document_id"
            ) from exc

    async def get_by_ids(self, chunk_ids: list[str]) -> list[Chunk]:
        try:
            stmt = select(ChunkModel).where(ChunkModel.id.in_(chunk_ids))
            result = await self._session.execute(stmt)
            return [self._to_entity(m) for m in result.scalars().all()]
        except Exception as exc:
            raise DatabaseError(
                f"Failed to batch get chunks: {exc}", operation="get_by_ids"
            ) from exc

    # ── Mapper Methods ────────────────────────────────────────────────────────

    def _to_model(self, entity: Chunk) -> ChunkModel:
        return ChunkModel(
            id=entity.id,
            document_id=entity.document_id,
            content=entity.content,
            chunk_type=entity.chunk_type.value,
            chunk_index=entity.chunk_index,
            start_char=entity.start_char,
            end_char=entity.end_char,
            token_count=entity.token_count,
            page_number=entity.page_number,
            section_title=entity.section_title,
            section_path=entity.section_path,
            parent_chunk_id=entity.parent_chunk_id,
            embedding_model=entity.embedding_model,
            metadata_=entity.metadata,
            created_at=entity.created_at,
        )

    def _to_entity(self, model: ChunkModel) -> Chunk:
        return Chunk(
            id=model.id,
            document_id=model.document_id,
            content=model.content,
            chunk_type=ChunkType(model.chunk_type),
            chunk_index=model.chunk_index,
            start_char=model.start_char,
            end_char=model.end_char,
            token_count=model.token_count,
            page_number=model.page_number,
            section_title=model.section_title,
            section_path=model.section_path,
            parent_chunk_id=model.parent_chunk_id,
            embedding_model=model.embedding_model,
            metadata=model.metadata_ or {},
            created_at=model.created_at,
        )
