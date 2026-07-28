"""
Knowledge Graph REST API endpoints for schema, node search, traversal, and 3D visualization.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.graph.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])
logger = get_logger(__name__, component="graph_api")


class CypherQueryRequest(BaseModel):
    cypher: str = Field(..., description="Read-only Cypher query string")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Query parameters")


class GraphStatsResponse(BaseModel):
    nodes: dict[str, int]
    relationships: dict[str, int]
    total_nodes: int
    total_relationships: int


# Shared graph service instance
_graph_service = GraphService()


@router.get(
    "/stats",
    response_model=GraphStatsResponse,
    summary="Get Knowledge Graph Statistics",
)
async def get_graph_stats() -> GraphStatsResponse:
    """Return aggregate node and relationship counts from Neo4j."""
    try:
        stats = await _graph_service.get_graph_stats()
        return GraphStatsResponse(**stats)
    except Exception as exc:
        logger.warning("graph_stats_fallback", error=str(exc))
        return GraphStatsResponse(
            nodes={"Service": 0, "Team": 0, "Employee": 0, "Repository": 0},
            relationships={"OWNS": 0, "DEPENDS_ON": 0},
            total_nodes=0,
            total_relationships=0,
        )


@router.get(
    "/nodes",
    response_model=dict,
    summary="Search & List Knowledge Graph Nodes",
)
async def get_graph_nodes(
    label: str | None = Query(None, description="Filter by node label (Service, Team, Employee, etc.)"),
    search: str | None = Query(None, description="Search query string for node names"),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    """Return nodes for graph visualization."""
    lbl_clause = f":{label}" if label else ""
    where_clauses = []
    params: dict[str, Any] = {"limit": limit}

    if search:
        where_clauses.append("toLower(n.name) CONTAINS toLower($search)")
        params["search"] = search

    where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    cypher = f"MATCH (n{lbl_clause}) {where_str} RETURN id(n) AS node_id, labels(n)[0] AS label, n.id AS name_id, n.name AS name, properties(n) AS props LIMIT $limit"

    try:
        nodes = await _graph_service.client.execute_query(cypher, parameters=params)
        return {"nodes": nodes, "total": len(nodes)}
    except Exception as exc:
        logger.warning("graph_nodes_query_failed", error=str(exc))
        return {"nodes": [], "total": 0, "message": "Neo4j unavailable or empty"}


@router.get(
    "/neighbors/{node_id}",
    response_model=dict,
    summary="Get Connected Subgraph Neighbors",
)
async def get_node_neighbors(
    node_id: str,
    depth: int = Query(default=1, ge=1, le=3),
) -> dict:
    """Return connected neighbors of a specific node for graph exploration."""
    cypher = """
    MATCH (n {id: $node_id})-[r]-(neighbor)
    RETURN id(n) AS source_id, n.name AS source_name, labels(n)[0] AS source_label,
           type(r) AS rel_type,
           id(neighbor) AS target_id, neighbor.name AS target_name, labels(neighbor)[0] AS target_label
    LIMIT 100
    """
    try:
        edges = await _graph_service.client.execute_query(cypher, parameters={"node_id": node_id})
        return {"center_node": node_id, "subgraph_edges": edges}
    except Exception as exc:
        logger.warning("graph_neighbors_query_failed", error=str(exc))
        return {"center_node": node_id, "subgraph_edges": []}


@router.post(
    "/cypher",
    response_model=dict,
    summary="Execute Read-Only Cypher Query",
)
async def execute_cypher(request: CypherQueryRequest) -> dict:
    """Execute arbitrary read-only Cypher queries for advanced graph queries."""
    clean_cypher = request.cypher.strip()
    if any(kw in clean_cypher.upper() for kw in ["CREATE", "DELETE", "SET", "REMOVE", "MERGE", "DROP"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only read-only (MATCH / RETURN) Cypher queries are permitted on this endpoint",
        )

    try:
        records = await _graph_service.client.execute_query(clean_cypher, parameters=request.parameters)
        return {"records": records, "total": len(records)}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
