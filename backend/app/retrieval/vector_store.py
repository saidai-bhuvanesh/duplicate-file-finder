"""
FAISS Vector Store implementation using SentenceTransformers.
"""

from __future__ import annotations

import os
import pickle
from typing import Any

import numpy as np

from app.core.config import get_settings
from app.core.exceptions import IndexNotReadyError, RetrievalError
from app.core.logging import get_logger
from app.domain.interfaces.vector_store import VectorSearchResult, VectorStore

logger = get_logger(__name__, component="faiss_vector_store")


class FAISSVectorStore(VectorStore):
    """
    FAISS-backed vector store implementing VectorStore domain interface.
    Uses SentenceTransformers for embedding generation and FAISS for ANN search.
    """

    def __init__(self, index_path: str | None = None, model_name: str | None = None) -> None:
        settings = get_settings()
        self.index_path = index_path or settings.retrieval.faiss_index_path
        self.model_name = model_name or settings.embedding.model
        self.dimension = settings.embedding.dimension

        self._encoder: Any = None
        self._index: Any = None
        self._metadata_store: list[dict[str, Any]] = []
        self._chunk_id_to_idx: dict[str, int] = {}

    def _get_encoder(self) -> Any:
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            logger.info("loading_embedding_model", model_name=self.model_name)
            self._encoder = SentenceTransformer(self.model_name, device=get_settings().embedding.device)
        return self._encoder

    def _get_index(self) -> Any:
        if self._index is None:
            import faiss
            # Create IndexFlatIP for Inner Product (Cosine similarity when vectors are L2 normalized)
            self._index = faiss.IndexFlatIP(self.dimension)
        return self._index

    def encode_text(self, text: str | list[str]) -> np.ndarray:
        """Encode text or list of texts into L2 normalized embeddings."""
        encoder = self._get_encoder()
        embeddings = encoder.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.astype(np.float32)

    async def add_embeddings(
        self,
        chunk_ids: list[str],
        embeddings: list[list[float]],
        document_ids: list[str],
        contents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> int:
        if not chunk_ids:
            return 0

        import faiss
        index = self._get_index()
        vecs = np.array(embeddings, dtype=np.float32)

        # Normalize vectors for cosine similarity
        faiss.normalize_L2(vecs)

        start_idx = index.ntotal
        index.add(vecs)

        for offset, (cid, did, content, meta) in enumerate(zip(chunk_ids, document_ids, contents, metadatas)):
            flat_idx = start_idx + offset
            record = {
                "chunk_id": cid,
                "document_id": did,
                "content": content,
                "metadata": meta,
            }
            self._metadata_store.append(record)
            self._chunk_id_to_idx[cid] = flat_idx

        logger.info("faiss_embeddings_added", count=len(chunk_ids), total_in_index=index.ntotal)
        await self.save()
        return len(chunk_ids)

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[VectorSearchResult]:
        if self._index is None or self._index.ntotal == 0:
            # Attempt to load from disk
            if os.path.exists(f"{self.index_path}.index"):
                await self.load()
            else:
                logger.warning("faiss_index_empty")
                return []

        import faiss
        q_vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(q_vec)

        # Search top_k * 3 candidates to leave room for metadata filtering
        candidate_k = min(top_k * 3, self._index.ntotal)
        distances, indices = self._index.search(q_vec, candidate_k)

        results: list[VectorSearchResult] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1 or idx >= len(self._metadata_store):
                continue

            record = self._metadata_store[idx]

            # Metadata filtering
            if filters and not self._matches_filter(record["metadata"], filters):
                continue

            results.append(
                VectorSearchResult(
                    chunk_id=record["chunk_id"],
                    document_id=record["document_id"],
                    score=float(dist),
                    content=record["content"],
                    metadata=record["metadata"],
                )
            )
            if len(results) >= top_k:
                break

        return results

    def _matches_filter(self, meta: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if metadata matches search filters."""
        for k, v in filters.items():
            if k not in meta:
                return False
            if isinstance(v, list):
                if meta[k] not in v:
                    return False
            elif meta[k] != v:
                return False
        return True

    async def delete_by_document_id(self, document_id: str) -> int:
        # Rebuild index without document_id
        if not self._metadata_store:
            return 0

        new_store = []
        new_vecs = []

        for idx, rec in enumerate(self._metadata_store):
            if rec["document_id"] != document_id:
                new_store.append(rec)
                # Extract vector from index
                vec = np.zeros((1, self.dimension), dtype=np.float32)
                self._index.reconstruct(idx, vec[0])
                new_vecs.append(vec[0])

        removed = len(self._metadata_store) - len(new_store)
        self._metadata_store = new_store
        import faiss
        self._index = faiss.IndexFlatIP(self.dimension)
        self._chunk_id_to_idx.clear()

        if new_vecs:
            mat = np.array(new_vecs, dtype=np.float32)
            self._index.add(mat)
            for i, r in enumerate(self._metadata_store):
                self._chunk_id_to_idx[r["chunk_id"]] = i

        await self.save()
        return removed

    async def delete_by_chunk_ids(self, chunk_ids: list[str]) -> int:
        chunk_set = set(chunk_ids)
        new_store = []
        new_vecs = []

        for idx, rec in enumerate(self._metadata_store):
            if rec["chunk_id"] not in chunk_set:
                new_store.append(rec)
                vec = np.zeros((1, self.dimension), dtype=np.float32)
                self._index.reconstruct(idx, vec[0])
                new_vecs.append(vec[0])

        removed = len(self._metadata_store) - len(new_store)
        self._metadata_store = new_store
        import faiss
        self._index = faiss.IndexFlatIP(self.dimension)
        self._chunk_id_to_idx.clear()

        if new_vecs:
            mat = np.array(new_vecs, dtype=np.float32)
            self._index.add(mat)
            for i, r in enumerate(self._metadata_store):
                self._chunk_id_to_idx[r["chunk_id"]] = i

        await self.save()
        return removed

    async def get_index_stats(self) -> dict[str, Any]:
        return {
            "total_vectors": self._index.ntotal if self._index else 0,
            "dimension": self.dimension,
            "metadata_count": len(self._metadata_store),
            "model_name": self.model_name,
        }

    async def save(self) -> None:
        import faiss
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        if self._index:
            faiss.write_index(self._index, f"{self.index_path}.index")
        with open(f"{self.index_path}.meta", "wb") as f:
            pickle.dump((self._metadata_store, self._chunk_id_to_idx), f)
        logger.info("faiss_index_saved", path=self.index_path)

    async def load(self) -> None:
        import faiss
        idx_file = f"{self.index_path}.index"
        meta_file = f"{self.index_path}.meta"
        if os.path.exists(idx_file) and os.path.exists(meta_file):
            self._index = faiss.read_index(idx_file)
            with open(meta_file, "rb") as f:
                self._metadata_store, self._chunk_id_to_idx = pickle.load(f)
            logger.info("faiss_index_loaded", path=self.index_path, count=self._index.ntotal)
        else:
            logger.warning("faiss_index_file_missing", path=self.index_path)
