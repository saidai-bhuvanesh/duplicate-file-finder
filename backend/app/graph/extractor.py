"""
Entity and Relationship Extraction Engine for IT Knowledge Graph.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.domain.entities.document import Document

logger = get_logger(__name__, component="entity_extractor")


@dataclass
class ExtractedNode:
    """Represents a Graph Node extracted from text."""

    label: str          # Employee, Team, Service, Repository, APIEndpoint, Incident, Ticket, Database, CloudResource
    id: str             # Unique identifier name/key
    name: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedRelationship:
    """Represents a Graph Edge extracted between two Nodes."""

    source_label: str
    source_id: str
    target_label: str
    target_id: str
    rel_type: str       # OWNS, DEPENDS_ON, CAUSED_BY, ASSIGNED_TO, DEPLOYS_TO, EXPOSES_API, USES_LIBRARY
    properties: dict[str, Any] = field(default_factory=dict)


class EntityExtractor:
    """
    NLP and pattern-based IT entity and relationship extraction engine.
    Extracts IT infrastructure nodes and dependency edges from document content.
    """

    # Regex patterns for technical assets
    TICKET_REGEX = re.compile(r"\b([A-Z]{2,10}-\d+)\b")
    API_REGEX = re.compile(r"\b(GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9_\-/{}]+)\b", re.IGNORECASE)
    REPO_REGEX = re.compile(r"github\.com/([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+)")
    AWS_S3_REGEX = re.compile(r"s3://([a-zA-Z0-9_\-]+)")
    SERVICE_KEYWORDS = re.compile(r"\b([a-zA-Z0-9_\-]+-(service|api|worker|db|cache|daemon))\b", re.IGNORECASE)

    def extract_from_document(self, document: Document) -> tuple[list[ExtractedNode], list[ExtractedRelationship]]:
        """
        Extract nodes and relationships from a Document entity.
        """
        nodes: list[ExtractedNode] = []
        relationships: list[ExtractedRelationship] = []
        seen_nodes: set[tuple[str, str]] = set()

        content = document.content
        meta = document.metadata

        # 1. Author / Employee Node
        if meta.author:
            author_id = meta.author.lower().replace(" ", "_")
            if ("Employee", author_id) not in seen_nodes:
                nodes.append(ExtractedNode(label="Employee", id=author_id, name=meta.author, properties={"email": meta.author}))
                seen_nodes.add(("Employee", author_id))

        # 2. Team Node
        if meta.team:
            team_id = meta.team.lower().replace(" ", "_")
            if ("Team", team_id) not in seen_nodes:
                nodes.append(ExtractedNode(label="Team", id=team_id, name=meta.team))
                seen_nodes.add(("Team", team_id))
            if meta.author:
                author_id = meta.author.lower().replace(" ", "_")
                relationships.append(
                    ExtractedRelationship(
                        source_label="Employee", source_id=author_id,
                        target_label="Team", target_id=team_id,
                        rel_type="MEMBER_OF"
                    )
                )

        # 3. Repository Node
        if meta.repository:
            repo_id = meta.repository
            if ("Repository", repo_id) not in seen_nodes:
                nodes.append(ExtractedNode(label="Repository", id=repo_id, name=meta.repository))
                seen_nodes.add(("Repository", repo_id))
            if meta.team:
                team_id = meta.team.lower().replace(" ", "_")
                relationships.append(
                    ExtractedRelationship(
                        source_label="Team", source_id=team_id,
                        target_label="Repository", target_id=repo_id,
                        rel_type="OWNS"
                    )
                )

        # 4. Jira Ticket Nodes
        if meta.ticket_key:
            ticket_id = meta.ticket_key
            if ("Ticket", ticket_id) not in seen_nodes:
                nodes.append(ExtractedNode(label="Ticket", id=ticket_id, name=ticket_id))
                seen_nodes.add(("Ticket", ticket_id))

        # Regex scan of document content
        self._extract_tickets_from_content(content, nodes, relationships, seen_nodes)
        self._extract_apis_from_content(content, nodes, relationships, seen_nodes)
        self._extract_services_from_content(content, nodes, relationships, seen_nodes)
        self._extract_s3_from_content(content, nodes, relationships, seen_nodes)

        logger.info(
            "entities_extracted",
            doc_id=document.id,
            nodes_count=len(nodes),
            rel_count=len(relationships),
        )
        return nodes, relationships

    def _extract_tickets_from_content(self, text: str, nodes: list[ExtractedNode], rels: list[ExtractedRelationship], seen: set):
        for match in self.TICKET_REGEX.finditer(text):
            t_key = match.group(1)
            if ("Ticket", t_key) not in seen:
                nodes.append(ExtractedNode(label="Ticket", id=t_key, name=t_key))
                seen.add(("Ticket", t_key))

    def _extract_apis_from_content(self, text: str, nodes: list[ExtractedNode], rels: list[ExtractedRelationship], seen: set):
        for match in self.API_REGEX.finditer(text):
            method = match.group(1).upper()
            path = match.group(2)
            api_id = f"{method} {path}"
            if ("APIEndpoint", api_id) not in seen:
                nodes.append(ExtractedNode(label="APIEndpoint", id=api_id, name=api_id, properties={"method": method, "path": path}))
                seen.add(("APIEndpoint", api_id))

    def _extract_services_from_content(self, text: str, nodes: list[ExtractedNode], rels: list[ExtractedRelationship], seen: set):
        found_services = []
        for match in self.SERVICE_KEYWORDS.finditer(text):
            svc_name = match.group(1).lower()
            found_services.append(svc_name)
            if ("Service", svc_name) not in seen:
                nodes.append(ExtractedNode(label="Service", id=svc_name, name=svc_name))
                seen.add(("Service", svc_name))

        # Infer DEPENDS_ON relationship between co-occurring services
        unique_svcs = list(set(found_services))
        if len(unique_svcs) >= 2:
            s1, s2 = unique_svcs[0], unique_svcs[1]
            rels.append(ExtractedRelationship(source_label="Service", source_id=s1, target_label="Service", target_id=s2, rel_type="DEPENDS_ON"))

    def _extract_s3_from_content(self, text: str, nodes: list[ExtractedNode], rels: list[ExtractedRelationship], seen: set):
        for match in self.AWS_S3_REGEX.finditer(text):
            b_name = match.group(1)
            res_id = f"s3://{b_name}"
            if ("CloudResource", res_id) not in seen:
                nodes.append(ExtractedNode(label="CloudResource", id=res_id, name=res_id, properties={"type": "s3_bucket"}))
                seen.add(("CloudResource", res_id))
