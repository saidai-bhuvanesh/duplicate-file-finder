"""
Code-aware chunker respecting functions, classes, and language AST structures.
"""

from __future__ import annotations

import re
from app.core.config import get_settings
from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.entities.document import Document
from app.ingestion.chunkers.base_chunker import BaseChunker


class CodeChunker(BaseChunker):
    """
    Code-aware chunker for programming languages (Python, JS/TS, Java, Go, C++, SQL, Terraform, etc.).
    Preserves top-level functions, classes, blocks, or methods intact.
    """

    # Regex definitions for function/class signatures in common languages
    DEF_REGEXES = {
        "python": re.compile(r"^(async\s+def\s+|def\s+|class\s+)", re.MULTILINE),
        "javascript": re.compile(r"^(function\s+|class\s+|const\s+\w+\s*=\s*(async\s*)?\(|export\s+)", re.MULTILINE),
        "typescript": re.compile(r"^(function\s+|class\s+|interface\s+|type\s+|export\s+)", re.MULTILINE),
        "java": re.compile(r"^(public|private|protected|class|interface|enum)\s+", re.MULTILINE),
        "go": re.compile(r"^(func\s+|type\s+\w+\s+struct)", re.MULTILINE),
        "rust": re.compile(r"^(pub\s+fn\s+|fn\s+|struct\s+|impl\s+|enum\s+)", re.MULTILINE),
        "terraform": re.compile(r"^(resource\s+|module\s+|variable\s+|output\s+|provider\s+)", re.MULTILINE),
        "sql": re.compile(r"^(CREATE\s+|ALTER\s+|INSERT\s+|SELECT\s+|UPDATE\s+)", re.MULTILINE | re.IGNORECASE),
    }

    def __init__(self, max_chunk_size: int | None = None) -> None:
        settings = get_settings()
        self.max_chunk_size_chars = (max_chunk_size or settings.chunking.size) * 4

    def chunk_document(self, document: Document) -> list[Chunk]:
        content = document.content
        if not content.strip():
            return []

        lang = document.metadata.language if document.metadata else "python"
        regex = self.DEF_REGEXES.get(lang.lower(), self.DEF_REGEXES["python"])

        matches = list(regex.finditer(content))
        if not matches:
            # Fall back to block / double newline splitting
            return self._split_by_blocks(document)

        blocks: list[tuple[str, int, int]] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            block_code = content[start:end].strip()
            if block_code:
                blocks.append((block_code, start, end))

        # Check for header imports / comments before first function match
        if matches[0].start() > 0:
            header_code = content[0:matches[0].start()].strip()
            if header_code:
                blocks.insert(0, (header_code, 0, matches[0].start()))

        chunks: list[Chunk] = []
        for idx, (block_code, start, end) in enumerate(blocks):
            # Extract section title (first line signature)
            first_line = block_code.split("\n")[0].strip()[:100]

            chunks.append(
                Chunk(
                    document_id=document.id,
                    content=block_code,
                    chunk_type=ChunkType.CODE,
                    chunk_index=idx,
                    start_char=start,
                    end_char=end,
                    section_title=first_line,
                    token_count=len(block_code.split()),
                    metadata={
                        "document_title": document.title,
                        "language": lang,
                        "signature": first_line,
                    },
                )
            )

        return chunks

    def _split_by_blocks(self, document: Document) -> list[Chunk]:
        lines = document.content.split("\n")
        chunks: list[Chunk] = []
        current_block = []
        current_len = 0
        start_pos = 0
        offset = 0

        for line in lines:
            current_block.append(line)
            current_len += len(line) + 1
            if current_len >= self.max_chunk_size_chars:
                text = "\n".join(current_block).strip()
                if text:
                    chunks.append(
                        Chunk(
                            document_id=document.id,
                            content=text,
                            chunk_type=ChunkType.CODE,
                            chunk_index=len(chunks),
                            start_char=start_pos,
                            end_char=offset + len(line),
                            token_count=len(text.split()),
                            metadata={"document_title": document.title},
                        )
                    )
                current_block = []
                current_len = 0
                start_pos = offset + len(line) + 1
            offset += len(line) + 1

        if current_block:
            text = "\n".join(current_block).strip()
            if text:
                chunks.append(
                    Chunk(
                        document_id=document.id,
                        content=text,
                        chunk_type=ChunkType.CODE,
                        chunk_index=len(chunks),
                        start_char=start_pos,
                        end_char=offset,
                        token_count=len(text.split()),
                        metadata={"document_title": document.title},
                    )
                )

        return chunks
