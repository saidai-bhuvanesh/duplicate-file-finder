"""
Parent-Child chunker establishing parent chunks and small child chunks.
"""

from __future__ import annotations

import uuid
from app.core.config import get_settings
from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.entities.document import Document
from app.ingestion.chunkers.base_chunker import BaseChunker
from app.ingestion.chunkers.recursive_chunker import RecursiveChunker


class ParentChildChunker(BaseChunker):
    """
    Creates large Parent chunks (e.g. 2048 tokens) and subdivides each into
    smaller Child chunks (e.g. 512 tokens).
    Small child chunks are indexed in vector search for fine-grained similarity,
    while returning the larger parent chunk context to the LLM.
    """

    def __init__(
        self,
        parent_chunk_size: int | None = None,
        child_chunk_size: int | None = None,
        child_overlap: int | None = None,
    ) -> None:
        settings = get_settings()
        self.parent_size = parent_chunk_size or settings.chunking.parent_chunk_size
        self.child_size = child_chunk_size or settings.chunking.size
        self.child_overlap = child_overlap or settings.chunking.overlap

        self.parent_chunker = RecursiveChunker(chunk_size=self.parent_size, chunk_overlap=0)
        self.child_chunker = RecursiveChunker(chunk_size=self.child_size, chunk_overlap=self.child_overlap)

    def chunk_document(self, document: Document) -> list[Chunk]:
        # 1. Generate Parent Chunks
        parent_chunks = self.parent_chunker.chunk_document(document)
        all_chunks: list[Chunk] = []

        global_idx = 0
        for p_idx, p_chunk in enumerate(parent_chunks):
            # Mark parent chunk
            p_chunk.chunk_type = ChunkType.PARENT
            p_chunk.id = str(uuid.uuid4())
            p_chunk.chunk_index = global_idx
            global_idx += 1
            all_chunks.append(p_chunk)

            # 2. Subsegment Parent Chunk into Child Chunks
            temp_doc = Document(
                id=document.id,
                title=document.title,
                content=p_chunk.content,
                document_type=document.document_type,
                metadata=document.metadata,
            )
            children = self.child_chunker.chunk_document(temp_doc)

            for c in children:
                c.id = str(uuid.uuid4())
                c.parent_chunk_id = p_chunk.id  # Link to parent!
                c.chunk_type = ChunkType.RECURSIVE
                c.chunk_index = global_idx
                # Adjust offsets relative to original document
                c.start_char += p_chunk.start_char
                c.end_char += p_chunk.start_char
                c.section_title = p_chunk.section_title
                c.section_path = p_chunk.section_path
                global_idx += 1
                all_chunks.append(c)

        return all_chunks
