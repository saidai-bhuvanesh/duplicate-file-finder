"""
GraphRAG Retrieval Engine performing multi-hop Cypher graph traversals.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger
from app.domain.entities.chunk import Chunk, ChunkType
from app.domain.entities.query import Query, RetrievedContext
from app.infrastructure.database.neo4j_driver import Neo4jClient, get_neo4j_client

logger = get_logger(__name__, component="graph_rag")


class GraphRAGEngine:
    """
    Innovation 5: GraphRAG Engine.
    Executes multi-hop Cypher graph traversals to resolve complex enterprise dependencies
    (e.g., Team -> Service -> Infrastructure -> Document Chunks).
    """

    def __init__(self, neo4j_client: Neo4jClient | None = None) -> None:
        self.client = neo4j_client or get_neo4j_client()

    async def retrieve_graph_context(self, query_text: str, top_k: int = 5) -> list[Chunk]:
        """
        Perform GraphRAG multi-hop retrieval for the given query text.

        Returns:
            List of Chunk entities synthesized from graph traversal paths.
        """
        keywords = [w.lower() for w in re.findall(r"\b\w+\b", query_text) if len(w) > 2]
        if not keywords:
            return []

        # 1. Multi-hop Cypher Graph Traversal Query
        cypher = """
        MATCH (n)
        WHERE any(kw IN $keywords WHERE toLower(n.name) CONTAINS kw OR toLower(n.id) CONTAINS kw)
        OPTIONAL MATCH path = (n)-[r:OWNS|DEPENDS_ON|CAUSED_BY|MEMBER_OF|EXPOSES_API*1..3]-(target)
        OPTIONAL MATCH (target)<-[:MENTIONS|HAS_CHUNK]-(d:DocumentNode)
        RETURN n.id AS entity_id,
               labels(n)[0] AS entity_label,
               n.name AS entity_name,
               target.id AS connected_id,
               labels(target)[0] AS connected_label,
               d.id AS doc_id,
               d.title AS doc_title,
               length(path) AS hop_distance
        LIMIT 20
        """

        try:
            records = await self.client.execute_query(cypher, parameters={"keywords": keywords})
        except Exception as exc:
            logger.warning("graph_rag_traversal_skipped", error=str(exc))
            return []

        if not records:
            return []

        # 2. Synthesize Graph Traversal Paths into Graph Chunks
        chunks: list[Chunk] = []
        for idx, rec in enumerate(records):
            entity_name = rec.get("entity_name") or rec.get("entity_id", "Entity")
            conn_name = rec.get("connected_id") or "Connected Asset"
            doc_title = rec.get("doc_title") or "Graph Knowledge Base"
            doc_id = rec.get("doc_id") or "graph-doc-000"

            graph_path_str = f"[{rec.get('entity_label', 'Entity')}: {entity_name}] ──▶ [{rec.get('connected_label', 'Asset')}: {conn_name}]"
            content = f"Knowledge Graph Relationship:\n{graph_path_str}\nDocument Reference: {doc_title}"

            chunk = Chunk(
                id=f"graph-chunk-{idx}",
                document_id=doc_id,
                content=content,
                chunk_type=ChunkType.SEMANTIC,
                chunk_index=idx,
                final_score=round(1.0 / (1.0 + (rec.get("hop_distance") or 1)), 4),
                section_title=f"Graph Path: {entity_name}",
                section_path=graph_path_str,
                token_count=len(content.split()),
                metadata={
                    "source_system": "neo4j_graph",
                    "entity_id": rec.get("entity_id"),
                    "graph_path": graph_path_str,
                    "hop_distance": rec.get("hop_distance"),
                },
            )
            chunks.append(chunk)

        chunks.sort(key=lambda c: c.final_score or 0.0, reverse=True)
        logger.info("graph_rag_retrieval_completed", count=len(chunks))
        return chunks[:top_k]
