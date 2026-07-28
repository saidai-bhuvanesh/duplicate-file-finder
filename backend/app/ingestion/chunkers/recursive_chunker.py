"""
Recursive character & token-aware chunker with configurable overlap.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.entities.document import Document
from app.ingestion.chunkers.base_chunker import BaseChunker


class RecursiveChunker(BaseChunker):
    """
    Splits text recursively using separators in order of decreasing priority:
    ["\n\n", "\n", ". ", " ", ""]
    Ensures chunks do not exceed token/character limits while preserving overlap.
    """

    SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", " ", ""]

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None) -> None:
        settings = get_settings()
        # Approximate 1 token ≈ 4 characters
        self.chunk_size_chars = (chunk_size or settings.chunking.size) * 4
        self.chunk_overlap_chars = (chunk_overlap or settings.chunking.overlap) * 4

    def chunk_document(self, document: Document) -> list[Chunk]:
        text = document.content
        if not text.strip():
            return []

        raw_chunks = self._split_text(text, self.SEPARATORS)
        chunks: list[Chunk] = []

        for idx, (chunk_text, start, end) in enumerate(raw_chunks):
            chunk = Chunk(
                document_id=document.id,
                content=chunk_text,
                chunk_type=ChunkType.RECURSIVE,
                chunk_index=idx,
                start_char=start,
                end_char=end,
                token_count=len(chunk_text.split()),
                metadata={
                    "document_title": document.title,
                    "document_type": document.document_type.value,
                    "source_system": document.metadata.source_system.value,
                },
            )
            chunks.append(chunk)

        return chunks

    def _split_text(self, text: str, separators: list[str]) -> list[tuple[str, int, int]]:
        """Splits text recursively into (chunk_text, start_char, end_char) tuples."""
        results: list[tuple[str, int, int]] = []
        
        if len(text) <= self.chunk_size_chars:
            return [(text, 0, len(text))]

        sep = separators[-1]
        for s in separators:
            if s == "":
                sep = ""
                break
            if s in text:
                sep = s
                break

        if sep:
            splits = text.split(sep)
        else:
            splits = list(text)

        current_chunk = ""
        chunk_start = 0
        current_pos = 0

        for split in splits:
            item = split + (sep if sep else "")
            if len(current_chunk) + len(item) <= self.chunk_size_chars:
                if not current_chunk:
                    chunk_start = current_pos
                current_chunk += item
            else:
                if current_chunk:
                    results.append((current_chunk.strip(), chunk_start, chunk_start + len(current_chunk)))
                    # Calculate overlap
                    overlap_len = min(len(current_chunk), self.chunk_overlap_chars)
                    current_chunk = current_chunk[-overlap_len:] + item if overlap_len > 0 else item
                    chunk_start = current_pos - overlap_len
                else:
                    # Item itself is larger than chunk_size_chars, recurse with next separators
                    if len(separators) > 1:
                        sub_chunks = self._split_text(item, separators[1:])
                        for sub_text, sub_s, sub_e in sub_chunks:
                            results.append((sub_text, current_pos + sub_s, current_pos + sub_e))
                    else:
                        results.append((item.strip(), current_pos, current_pos + len(item)))
                    current_chunk = ""

            current_pos += len(item)

        if current_chunk.strip():
            results.append((current_chunk.strip(), chunk_start, current_pos))

        return results
