"""
Graph Service syncing extracted entities & relationships into Neo4j.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.domain.entities.chunk import Chunk
from app.domain.entities.document import Document
from app.graph.extractor import EntityExtractor, ExtractedNode, ExtractedRelationship
from app.infrastructure.database.neo4j_driver import Neo4jClient, get_neo4j_client

logger = get_logger(__name__, component="graph_service")


class GraphService:
    """
    Manages Knowledge Graph persistence, sync, and graph query execution in Neo4j.
    """

    def __init__(self, neo4j_client: Neo4jClient | None = None) -> None:
        self.client = neo4j_client or get_neo4j_client()
        self.extractor = EntityExtractor()

    async def sync_document_to_graph(self, document: Document, chunks: list[Chunk] | None = None) -> dict[str, int]:
        """
        Extract entities from document and chunks, then merge them into Neo4j.
        """
        nodes, rels = self.extractor.extract_from_document(document)

        # 1. Create Document Node
        doc_cypher = """
        MERGE (d:DocumentNode {id: $doc_id})
        SET d.title = $title,
            d.document_type = $doc_type,
            d.source_system = $source_system,
            d.updated_at = timestamp()
        """
        await self.client.execute_query(
            doc_cypher,
            parameters={
                "doc_id": document.id,
                "title": document.title,
                "doc_type": document.document_type.value,
                "source_system": document.metadata.source_system.value,
            },
            write=True,
        )

        nodes_created = 0
        rels_created = 0

        # 2. Merge Extracted Nodes & link to Document
        for node in nodes:
            # Dynamic label Cypher MERGE
            cypher = f"""
            MERGE (n:{node.label} {{id: $id}})
            SET n.name = $name, n += $props
            WITH n
            MATCH (d:DocumentNode {{id: $doc_id}})
            MERGE (d)-[:MENTIONS]->(n)
            """
            await self.client.execute_query(
                cypher,
                parameters={
                    "id": node.id,
                    "name": node.name,
                    "props": node.properties,
                    "doc_id": document.id,
                },
                write=True,
            )
            nodes_created += 1

        # 3. Merge Extracted Relationships
        for rel in rels:
            cypher = f"""
            MATCH (s:{rel.source_label} {{id: $source_id}})
            MATCH (t:{rel.target_label} {{id: $target_id}})
            MERGE (s)-[r:{rel.rel_type}]->(t)
            SET r += $props
            """
            await self.client.execute_query(
                cypher,
                parameters={
                    "source_id": rel.source_id,
                    "target_id": rel.target_id,
                    "props": rel.properties,
                },
                write=True,
            )
            rels_created += 1

        # 4. Link Chunk Nodes if provided
        if chunks:
            for chunk in chunks:
                chunk_cypher = """
                MERGE (c:ChunkNode {id: $chunk_id})
                SET c.document_id = $doc_id,
                    c.section_title = $section_title,
                    c.token_count = $token_count
                WITH c
                MATCH (d:DocumentNode {id: $doc_id})
                MERGE (d)-[:HAS_CHUNK]->(c)
                """
                await self.client.execute_query(
                    chunk_cypher,
                    parameters={
                        "chunk_id": chunk.id,
                        "doc_id": document.id,
                        "section_title": chunk.section_title or "",
                        "token_count": chunk.token_count,
                    },
                    write=True,
                )

        logger.info(
            "graph_sync_completed",
            doc_id=document.id,
            nodes_created=nodes_created,
            rels_created=rels_created,
        )
        return {"nodes_synced": nodes_created, "relationships_synced": rels_created}

    async def get_graph_stats(self) -> dict[str, Any]:
        """Return aggregate statistics of the Neo4j Knowledge Graph."""
        node_query = "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count"
        rel_query = "MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count"

        node_counts = await self.client.execute_query(node_query)
        rel_counts = await self.client.execute_query(rel_query)

        return {
            "nodes": {r["label"]: r["count"] for r in node_counts if r.get("label")},
            "relationships": {r["rel_type"]: r["count"] for r in rel_counts if r.get("rel_type")},
            "total_nodes": sum(r["count"] for r in node_counts),
            "total_relationships": sum(r["count"] for r in rel_counts),
        }
