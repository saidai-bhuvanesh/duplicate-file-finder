"""
Unit tests for domain entities.
"""

import pytest
from datetime import datetime

from app.domain.entities.document import (
    Document,
    DocumentMetadata,
    DocumentStatus,
    DocumentType,
    SourceSystem,
)
from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.entities.query import (
    Query,
    QueryType,
    RetrievalStrategy,
    RetrievedContext,
    Citation,
    QueryResult,
    AnswerStatus,
)


@pytest.mark.unit
class TestDocumentEntity:
    def test_document_has_uuid_by_default(self):
        doc = Document()
        assert doc.id is not None
        assert len(doc.id) == 36  # UUID format

    def test_document_unique_ids(self):
        doc1 = Document()
        doc2 = Document()
        assert doc1.id != doc2.id

    def test_document_mark_processing(self):
        doc = Document(title="Test", content="content")
        doc.mark_processing()
        assert doc.status == DocumentStatus.PROCESSING

    def test_document_mark_indexed(self):
        doc = Document(title="Test", content="content")
        doc.mark_indexed(chunk_count=10)
        assert doc.status == DocumentStatus.INDEXED
        assert doc.chunk_count == 10
        assert doc.indexed_at is not None
        assert doc.error_message is None

    def test_document_mark_failed(self):
        doc = Document(title="Test", content="content")
        doc.mark_failed("Parsing error")
        assert doc.status == DocumentStatus.FAILED
        assert doc.error_message == "Parsing error"
        assert not doc.is_indexed

    def test_document_word_count(self):
        doc = Document(content="hello world foo bar")
        assert doc.word_count == 4

    def test_document_metadata_to_dict(self):
        meta = DocumentMetadata(
            source_system=SourceSystem.CONFLUENCE,
            author="Alice",
            tags=["architecture", "design"],
            project="project-x",
        )
        d = meta.to_dict()
        assert d["source_system"] == "confluence"
        assert d["author"] == "Alice"
        assert d["tags"] == ["architecture", "design"]
        assert d["project"] == "project-x"

    def test_document_repr(self):
        doc = Document(title="My Doc", document_type=DocumentType.PDF)
        r = repr(doc)
        assert "My Doc" in r
        assert "pdf" in r


@pytest.mark.unit
class TestChunkEntity:
    def test_chunk_has_uuid_by_default(self):
        chunk = Chunk()
        assert chunk.id is not None

    def test_chunk_has_embedding_false_when_none(self):
        chunk = Chunk()
        assert not chunk.has_embedding

    def test_chunk_has_embedding_true_when_set(self):
        chunk = Chunk(embedding=[0.1, 0.2, 0.3])
        assert chunk.has_embedding

    def test_chunk_char_length(self):
        chunk = Chunk(content="hello world")
        assert chunk.char_length == 11

    def test_chunk_to_retrieval_dict(self):
        chunk = Chunk(
            document_id="doc-123",
            content="Some content",
            section_title="Introduction",
            final_score=0.95,
            bm25_score=0.8,
            dense_score=0.9,
        )
        d = chunk.to_retrieval_dict()
        assert d["document_id"] == "doc-123"
        assert d["content"] == "Some content"
        assert d["section_title"] == "Introduction"
        assert d["scores"]["final"] == 0.95
        assert "embedding" not in d  # Embedding must NOT be in retrieval dict


@pytest.mark.unit
class TestQueryEntities:
    def test_query_has_uuid_by_default(self):
        q = Query(text="What is Kubernetes?")
        assert q.id is not None
        assert len(q.id) == 36

    def test_retrieved_context_top_chunks_sorted(self):
        chunk1 = Chunk(document_id="d1", content="A", final_score=0.5)
        chunk2 = Chunk(document_id="d2", content="B", final_score=0.9)
        chunk3 = Chunk(document_id="d3", content="C", final_score=0.7)

        ctx = RetrievedContext(query_id="q1", chunks=[chunk1, chunk2, chunk3])
        top = ctx.top_chunks

        assert top[0].final_score == 0.9
        assert top[1].final_score == 0.7
        assert top[2].final_score == 0.5

    def test_retrieved_context_unique_document_ids(self):
        chunk1 = Chunk(document_id="doc-1", content="A")
        chunk2 = Chunk(document_id="doc-2", content="B")
        chunk3 = Chunk(document_id="doc-1", content="C")  # Duplicate doc

        ctx = RetrievedContext(query_id="q1", chunks=[chunk1, chunk2, chunk3])
        unique = ctx.unique_document_ids

        assert len(unique) == 2
        assert "doc-1" in unique
        assert "doc-2" in unique

    def test_retrieved_context_text(self):
        chunk1 = Chunk(document_id="d1", content="First content", final_score=0.9)
        chunk2 = Chunk(document_id="d2", content="Second content", final_score=0.8)
        ctx = RetrievedContext(query_id="q1", chunks=[chunk1, chunk2])
        text = ctx.context_text
        assert "First content" in text
        assert "Second content" in text
        assert "[Source 1]" in text

    def test_query_result_has_sufficient_evidence(self):
        result = QueryResult(
            query_id="q1",
            query_text="test",
            answer="answer",
            status=AnswerStatus.COMPLETED,
            confidence_score=0.8,
        )
        assert result.has_sufficient_evidence is True

    def test_query_result_insufficient_evidence_low_confidence(self):
        result = QueryResult(
            query_id="q1",
            query_text="test",
            answer="answer",
            status=AnswerStatus.COMPLETED,
            confidence_score=0.3,
        )
        assert result.has_sufficient_evidence is False

    def test_query_result_source_count(self):
        citations = [
            Citation(
                chunk_id="c1", document_id="doc-1", document_title="T1",
                source_url=None, section_title=None, page_number=None, relevance_score=0.9,
            ),
            Citation(
                chunk_id="c2", document_id="doc-2", document_title="T2",
                source_url=None, section_title=None, page_number=None, relevance_score=0.8,
            ),
            Citation(
                chunk_id="c3", document_id="doc-1", document_title="T1",  # Duplicate
                source_url=None, section_title=None, page_number=None, relevance_score=0.7,
            ),
        ]
        result = QueryResult(
            query_id="q1",
            query_text="test",
            answer="answer",
            status=AnswerStatus.COMPLETED,
            citations=citations,
        )
        assert result.source_count == 2
