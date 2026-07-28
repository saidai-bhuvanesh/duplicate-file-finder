"""
Semantic boundary-aware chunker for natural markdown/heading structured texts.
"""

from __future__ import annotations

import re
from app.core.config import get_settings
from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.entities.document import Document
from app.ingestion.chunkers.base_chunker import BaseChunker


class SemanticChunker(BaseChunker):
    """
    Chunks document content by respecting natural semantic boundaries such as:
    Markdown headers (#, ##, ###), section breaks, or double newlines.
    Extracted sections are tagged with section_title and section_path.
    """

    HEADING_REGEX = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __init__(self, max_chunk_size: int | None = None) -> None:
        settings = get_settings()
        self.max_chunk_size_chars = (max_chunk_size or settings.chunking.size) * 4

    def chunk_document(self, document: Document) -> list[Chunk]:
        text = document.content
        if not text.strip():
            return []

        # Find heading positions
        matches = list(self.HEADING_REGEX.finditer(text))
        if not matches:
            # Fall back to double newline paragraph splitting if no headings
            return self._split_paragraphs(document)

        sections: list[tuple[str, str, int, int]] = []
        heading_stack: list[str] = []

        for i, match in enumerate(matches):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            start_pos = match.start()

            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            section_content = text[start_pos:end_pos].strip()

            # Update heading stack for hierarchy
            while len(heading_stack) >= level:
                heading_stack.pop()
            heading_stack.append(heading_text)
            section_path = " > ".join(heading_stack)

            sections.append((heading_text, section_path, section_content, start_pos, end_pos))

        chunks: list[Chunk] = []
        for idx, (title, path, content, start, end) in enumerate(sections):
            # If section content exceeds max size, split paragraphs inside section
            if len(content) > self.max_chunk_size_chars:
                sub_chunks = self._subsegment_content(document, content, title, path, start, idx)
                chunks.extend(sub_chunks)
            else:
                chunks.append(
                    Chunk(
                        document_id=document.id,
                        content=content,
                        chunk_type=ChunkType.SEMANTIC,
                        chunk_index=len(chunks),
                        start_char=start,
                        end_char=end,
                        section_title=title,
                        section_path=path,
                        token_count=len(content.split()),
                        metadata={
                            "document_title": document.title,
                            "section_title": title,
                            "section_path": path,
                        },
                    )
                )

        return chunks

    def _split_paragraphs(self, document: Document) -> list[Chunk]:
        paragraphs = document.content.split("\n\n")
        chunks: list[Chunk] = []
        current_offset = 0

        for idx, para in enumerate(paragraphs):
            para_strip = para.strip()
            if not para_strip:
                current_offset += len(para) + 2
                continue

            chunks.append(
                Chunk(
                    document_id=document.id,
                    content=para_strip,
                    chunk_type=ChunkType.SEMANTIC,
                    chunk_index=idx,
                    start_char=current_offset,
                    end_char=current_offset + len(para_strip),
                    token_count=len(para_strip.split()),
                    metadata={"document_title": document.title},
                )
            )
            current_offset += len(para) + 2

        return chunks

    def _subsegment_content(
        self, document: Document, content: str, title: str, path: str, start_offset: int, base_idx: int
    ) -> list[Chunk]:
        paragraphs = content.split("\n\n")
        sub_chunks: list[Chunk] = []
        curr_text = ""
        curr_start = start_offset
        offset = start_offset

        for p in paragraphs:
            if len(curr_text) + len(p) + 2 <= self.max_chunk_size_chars:
                curr_text += ("\n\n" if curr_text else "") + p
            else:
                if curr_text.strip():
                    sub_chunks.append(
                        Chunk(
                            document_id=document.id,
                            content=curr_text.strip(),
                            chunk_type=ChunkType.SEMANTIC,
                            chunk_index=base_idx + len(sub_chunks),
                            start_char=curr_start,
                            end_char=curr_start + len(curr_text),
                            section_title=title,
                            section_path=path,
                            token_count=len(curr_text.split()),
                            metadata={"document_title": document.title, "section_path": path},
                        )
                    )
                curr_text = p
                curr_start = offset
            offset += len(p) + 2

        if curr_text.strip():
            sub_chunks.append(
                Chunk(
                    document_id=document.id,
                    content=curr_text.strip(),
                    chunk_type=ChunkType.SEMANTIC,
                    chunk_index=base_idx + len(sub_chunks),
                    start_char=curr_start,
                    end_char=offset,
                    section_title=title,
                    section_path=path,
                    token_count=len(curr_text.split()),
                    metadata={"document_title": document.title, "section_path": path},
                )
            )
        return sub_chunks
