"""
BM25 Sparse Retrieval Index using rank_bm25.
"""

from __future__ import annotations

import os
import pickle
import re
from typing import Any

from rank_bm25 import BM25Okapi

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.entities.chunk import Chunk

logger = get_logger(__name__, component="bm25_index")


def _tokenize(text: str) -> list[str]:
    """Tokenize and normalize text for BM25 indexing."""
    # Convert to lowercase and find all alphanumeric tokens
    tokens = re.findall(r"\b\w+\b", text.lower())
    # Filter short tokens
    return [t for t in tokens if len(t) > 1]


class BM25Index:
    """
    BM25 Sparse Keyword Index.
    """

    def __init__(self, index_path: str | None = None) -> None:
        settings = get_settings()
        self.index_path = index_path or settings.retrieval.bm25_index_path
        self.k1 = settings.retrieval.bm25_k1
        self.b = settings.retrieval.bm25_b

        self._bm25: BM25Okapi | None = None
        self._corpus_chunks: list[dict[str, Any]] = []
        self._tokenized_corpus: list[list[str]] = []

    def build_index(self, chunks: list[Chunk]) -> None:
        """Build or rebuild BM25 index from a list of Chunk domain entities."""
        self._corpus_chunks = [
            {
                "chunk_id": c.id,
                "document_id": c.document_id,
                "content": c.content,
                "section_title": c.section_title,
                "metadata": c.metadata,
            }
            for c in chunks
        ]
        self._tokenized_corpus = [_tokenize(c["content"]) for c in self._corpus_chunks]

        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus, k1=self.k1, b=self.b)
            logger.info("bm25_index_built", chunk_count=len(chunks))
        else:
            self._bm25 = None

        self.save()

    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Add new chunks and rebuild index."""
        existing_ids = {c["chunk_id"] for c in self._corpus_chunks}
        new_chunks = [c for c in chunks if c.id not in existing_ids]

        if not new_chunks:
            return

        for c in new_chunks:
            record = {
                "chunk_id": c.id,
                "document_id": c.document_id,
                "content": c.content,
                "section_title": c.section_title,
                "metadata": c.metadata,
            }
            self._corpus_chunks.append(record)
            self._tokenized_corpus.append(_tokenize(c.content))

        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(self._tokenized_corpus, k1=self.k1, b=self.b)
            logger.info("bm25_index_updated", added=len(new_chunks), total=len(self._corpus_chunks))

        self.save()

    def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform BM25 keyword search.

        Returns:
            List of dicts: {"chunk_id", "document_id", "content", "score", "metadata"}
        """
        if self._bm25 is None or not self._corpus_chunks:
            if os.path.exists(f"{self.index_path}.pkl"):
                self.load()
            else:
                logger.warning("bm25_index_empty")
                return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        doc_scores = self._bm25.get_scores(query_tokens)
        top_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)

        results: list[dict[str, Any]] = []
        for idx in top_indices:
            score = float(doc_scores[idx])
            if score <= 0.0:
                break

            record = self._corpus_chunks[idx]

            # Apply metadata filters
            if filters and not self._matches_filter(record.get("metadata", {}), filters):
                continue

            results.append(
                {
                    "chunk_id": record["chunk_id"],
                    "document_id": record["document_id"],
                    "content": record["content"],
                    "section_title": record.get("section_title"),
                    "score": score,
                    "metadata": record.get("metadata", {}),
                }
            )

            if len(results) >= top_k:
                break

        return results

    def _matches_filter(self, meta: dict[str, Any], filters: dict[str, Any]) -> bool:
        for k, v in filters.items():
            if k not in meta:
                return False
            if isinstance(v, list):
                if meta[k] not in v:
                    return False
            elif meta[k] != v:
                return False
        return True

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        with open(f"{self.index_path}.pkl", "wb") as f:
            pickle.dump((self._corpus_chunks, self._tokenized_corpus), f)
        logger.info("bm25_index_saved", path=self.index_path)

    def load(self) -> None:
        file_path = f"{self.index_path}.pkl"
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                self._corpus_chunks, self._tokenized_corpus = pickle.load(f)
            if self._tokenized_corpus:
                self._bm25 = BM25Okapi(self._tokenized_corpus, k1=self.k1, b=self.b)
            logger.info("bm25_index_loaded", path=file_path, count=len(self._corpus_chunks))
        else:
            logger.warning("bm25_index_file_missing", path=file_path)
