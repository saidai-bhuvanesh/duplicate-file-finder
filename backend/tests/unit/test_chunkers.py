"""
Unit tests for chunking algorithms: RecursiveChunker, SemanticChunker, CodeChunker, and ParentChildChunker.
"""

import pytest

from app.domain.entities.chunk import ChunkType
from app.domain.entities.document import Document, DocumentMetadata, DocumentType, SourceSystem
from app.ingestion.chunkers.recursive_chunker import RecursiveChunker
from app.ingestion.chunkers.semantic_chunker import SemanticChunker
from app.ingestion.chunkers.code_chunker import CodeChunker
from app.ingestion.chunkers.parent_child_chunker import ParentChildChunker


@pytest.mark.unit
class TestRecursiveChunker:
    def test_chunking_short_document(self):
        doc = Document(title="Short", content="Hello world")
        chunker = RecursiveChunker(chunk_size=512)
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 1
        assert chunks[0].content == "Hello world"
        assert chunks[0].chunk_type == ChunkType.RECURSIVE

    def test_chunking_long_document(self):
        long_text = "Paragraph 1 sentence.\n\n" + ("This is paragraph content. " * 50) + "\n\nParagraph 3."
        doc = Document(title="Long", content=long_text)
        chunker = RecursiveChunker(chunk_size=50, chunk_overlap=5)  # small size forces splits
        chunks = chunker.chunk_document(doc)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c.content) > 0


@pytest.mark.unit
class TestSemanticChunker:
    def test_markdown_heading_boundaries(self):
        doc_text = "# Introduction\nWelcome to the system.\n\n## Architecture\nThe system uses microservices.\n\n## Deployment\nDeployed on K8s."
        doc = Document(title="Doc", content=doc_text, document_type=DocumentType.MARKDOWN)
        chunker = SemanticChunker()
        chunks = chunker.chunk_document(doc)

        assert len(chunks) == 3
        assert chunks[0].section_title == "Introduction"
        assert chunks[1].section_title == "Architecture"
        assert chunks[2].section_title == "Deployment"
        assert chunks[1].chunk_type == ChunkType.SEMANTIC

    def test_fallback_to_paragraphs(self):
        doc_text = "Paragraph 1 text.\n\nParagraph 2 text."
        doc = Document(title="Doc", content=doc_text)
        chunker = SemanticChunker()
        chunks = chunker.chunk_document(doc)
        assert len(chunks) == 2


@pytest.mark.unit
class TestCodeChunker:
    def test_python_code_chunking(self):
        code = (
            "import os\n\n"
            "def foo():\n    return 1\n\n"
            "class Bar:\n    def baz(self):\n        pass\n"
        )
        doc = Document(
            title="app.py",
            content=code,
            document_type=DocumentType.CODE,
            metadata=DocumentMetadata(source_system=SourceSystem.LOCAL_FILE, language="python"),
        )
        chunker = CodeChunker()
        chunks = chunker.chunk_document(doc)

        assert len(chunks) >= 2
        for c in chunks:
            assert c.chunk_type == ChunkType.CODE
            assert c.metadata.get("language") == "python"


@pytest.mark.unit
class TestParentChildChunker:
    def test_parent_child_linkage(self):
        long_content = "Word " * 1000
        doc = Document(title="ParentChildDoc", content=long_content)
        chunker = ParentChildChunker(parent_chunk_size=200, child_chunk_size=50)
        chunks = chunker.chunk_document(doc)

        parents = [c for c in chunks if c.chunk_type == ChunkType.PARENT]
        children = [c for c in chunks if c.chunk_type != ChunkType.PARENT]

        assert len(parents) > 0
        assert len(children) > 0

        # Verify child parent_chunk_id points to valid parent
        parent_ids = {p.id for p in parents}
        for child in children:
            assert child.parent_chunk_id in parent_ids
