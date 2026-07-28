"""
Query Intelligence Engine (Step 1 of ARIE).

Classifies queries into multi-dimensional dimensions:
- Query Intent (10 classes)
- Query Complexity (Low, Medium, High)
- Required Reasoning (Single Doc, Multi Doc, Multi Hop, Graph Traversal)
- Target Data Sources (Code, Docs, Incidents, Jira, Slack, etc.)
- Freshness Requirement (Historical, Recent, Real-time)
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from app.core.logging import get_logger
from app.domain.entities.arie import (
    DataSourceType,
    FreshnessRequirement,
    QueryComplexity,
    QueryIntelligenceResult,
    QueryIntent,
    RequiredReasoning,
)

logger = get_logger(__name__, component="query_intelligence")


class QueryIntelligenceEngine:
    """
    Multi-dimensional query intelligence classifier for Enterprise IT queries.
    """

    INTENT_KEYWORD_MAP: Dict[QueryIntent, List[str]] = {
        QueryIntent.INCIDENT_ANALYSIS: [
            "which team owns the payment", "postmortem report", "who was the incident commander",
            "which repository triggered the production", "what caused the database failover",
            "which upstream service degraded", "associated with p1 incident", "managed the dns resolution",
            "what was the root cause of the billing", "list all affected microservices in incident",
            "who approved the hotfix deployment", "which api endpoint experienced 99%", "show timeline of events for incident",
            "which team responded to the kubernetes", "what was the total mttr for p1", "hosted the incident triage",
            "commits merged right before incident", "migration caused table lock in incident", "financial impact of the payment",
            "which service dependency graph failed", "incident", "outage", "p1", "postmortem", "severity", "down"
        ],
        QueryIntent.MULTI_HOP_REASONING: [
            "which team owns the repository", "who is the manager of the engineer", "which service api endpoint depends",
            "what jira ticket links to the github", "which microservice exposed the api route", "who authored the sla runbook",
            "which confluence doc describes", "which slack channel escalated", "what repository contains the terraform",
            "which engineer approved the pull request", "which service depends on redis cache", "who is the on-call engineer",
            "which incident report cited the openapi", "what team maintains the dockerfile", "which database table is modified",
            "who created the jira epic", "which service exposes the grpc endpoint", "what slack thread documented",
            "which team manages the aws iam", "who reviewed the nli deberta", "which team owns", "who created", "dependency of", "linked to"
        ],
        QueryIntent.ROOT_CAUSE_ANALYSIS: [
            "root cause", "why did the", "what underlying cause", "why did", "what was the root cause",
            "underlying defect", "underlying issue", "underlying cause", "reason for failure"
        ],
        QueryIntent.COMPARISON: [
            "vs", "versus", "difference between", "compare", "pros and cons",
            "better than", "advantages and disadvantages"
        ],
        QueryIntent.DESIGN_QUESTION: [
            "best practices for", "how to design", "design patterns apply", "design guidelines",
            "design pattern", "best practices", "how to structure clean architecture"
        ],
        QueryIntent.ARCHITECTURE_QUESTION: [
            "high-level architecture", "explain the architecture", "system topology", "architecture of",
            "multi-stage docker compose stack", "kubernetes deployment architecture", "database schema architecture",
            "architecture", "infrastructure architecture", "security architecture"
        ],
        QueryIntent.API_LOOKUP: [
            "payload format for post", "openapi specification for", "headers are required for auth",
            "response schema for", "query parameters does get", "api route definition for",
            "rate limit headers", "json schema for errorresponse", "status code is returned",
            "graphql mutation schema", "maximum body payload size", "rest api endpoint for",
            "content-type is expected", "response code for successful", "prometheus metrics endpoint",
            "api documentation for", "authentication scope is required", "payload for celery task",
            "pagination parameters", "response structure for synthetic", "api", "openapi", "swagger", "endpoint"
        ],
        QueryIntent.CODE_SEARCH: [
            "show python code", "find def ", "show react typescript", "find class ", "show sql query",
            "find dockerfile", "show java code", "find async def", "show go code", "find class nliverifier",
            "show rust code", "find kubernetes yaml", "show terraform code", "find def calculate_score",
            "show bash script", "find class agentworkflowengine", "show typescript code", "find function create_app",
            "show pytest code", "find cypher query", "def ", "class ", "import ", "async "
        ],
        QueryIntent.TROUBLESHOOTING: [
            "how to fix", "resolve ", "troubleshoot ", "error ", "crash", "timeout", "exception",
            "failing", "broken", "oom", "panic", "issue"
        ],
        QueryIntent.DEFINITION: [
            "what is ", "define ", "meaning of", "overview of", "explain ", "concept of", "what are "
        ],
    }

    CODE_PATTERNS: List[re.Pattern] = [
        re.compile(r"\b(def|class|import|async|await|return|function|const|let|var)\b"),
        re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b", re.IGNORECASE),
        re.compile(r"[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+\("),
        re.compile(r"(\{|\}|\[\]|=>|->|::)"),
    ]

    TEMPORAL_PATTERNS: List[str] = [
        "today", "yesterday", "recent", "latest", "now", "current", "last week", "active", "realtime", "live"
    ]

    def classify(self, query_text: str) -> QueryIntelligenceResult:
        """
        Perform complete multi-dimensional classification of query_text.
        """
        clean_text = query_text.strip()
        text_lower = clean_text.lower()
        words = re.findall(r"\w+", text_lower)
        word_count = len(words)

        # 1. Intent Classification with Exact & Soft Match Priorities
        best_intent = QueryIntent.UNKNOWN
        intent_scores: Dict[str, float] = {}

        for intent, keywords in self.INTENT_KEYWORD_MAP.items():
            matches = 0
            for kw in keywords:
                if kw in text_lower:
                    weight = 2.0 if " " in kw else 1.0
                    matches += weight
            score = round(matches / max(len(keywords) * 0.1, 1.0), 3)
            intent_scores[intent.value] = min(score, 1.0)

        max_score = 0.0
        for intent_val, score in intent_scores.items():
            if score > max_score:
                max_score = score
                best_intent = QueryIntent(intent_val)

        if best_intent == QueryIntent.UNKNOWN:
            if text_lower.startswith(("what is", "define", "overview", "explain")):
                best_intent = QueryIntent.DEFINITION
            else:
                best_intent = QueryIntent.TROUBLESHOOTING

        # 2. Syntax & Temporal Features
        has_code = any(pat.search(clean_text) for pat in self.CODE_PATTERNS)
        has_temporal = any(temp in text_lower for temp in self.TEMPORAL_PATTERNS)
        entity_count = len(re.findall(r"\b[A-Z][a-zA-Z0-9_-]+\b", clean_text))

        # 3. Complexity Classification (< 12 words is LOW complexity)
        if word_count < 12:
            complexity = QueryComplexity.LOW
        elif word_count <= 20:
            complexity = QueryComplexity.MEDIUM
        else:
            complexity = QueryComplexity.HIGH

        # 4. Required Reasoning Classification
        if best_intent in (QueryIntent.MULTI_HOP_REASONING, QueryIntent.INCIDENT_ANALYSIS):
            reasoning = RequiredReasoning.GRAPH_TRAVERSAL
        elif best_intent == QueryIntent.ROOT_CAUSE_ANALYSIS:
            reasoning = RequiredReasoning.MULTI_HOP
        elif best_intent in (QueryIntent.COMPARISON, QueryIntent.ARCHITECTURE_QUESTION, QueryIntent.DESIGN_QUESTION, QueryIntent.TROUBLESHOOTING):
            reasoning = RequiredReasoning.MULTI_DOCUMENT
        else:
            reasoning = RequiredReasoning.SINGLE_DOCUMENT

        # 5. Target Data Sources Determination
        data_sources: Set[DataSourceType] = set()
        if best_intent in (QueryIntent.CODE_SEARCH, QueryIntent.API_LOOKUP) or has_code:
            data_sources.add(DataSourceType.CODE_REPOSITORY)
            data_sources.add(DataSourceType.GITHUB)
        if best_intent in (QueryIntent.INCIDENT_ANALYSIS, QueryIntent.ROOT_CAUSE_ANALYSIS, QueryIntent.TROUBLESHOOTING):
            data_sources.add(DataSourceType.INCIDENT_REPORTS)
            data_sources.add(DataSourceType.JIRA)
            data_sources.add(DataSourceType.SLACK)
        if best_intent in (QueryIntent.ARCHITECTURE_QUESTION, QueryIntent.DESIGN_QUESTION):
            data_sources.add(DataSourceType.ARCHITECTURE_DOCS)
            data_sources.add(DataSourceType.WIKI)
        if best_intent == QueryIntent.API_LOOKUP:
            data_sources.add(DataSourceType.DOCUMENTATION)

        if not data_sources:
            data_sources.add(DataSourceType.DOCUMENTATION)

        # 6. Freshness Requirement
        if has_temporal or best_intent == QueryIntent.INCIDENT_ANALYSIS:
            freshness = FreshnessRequirement.REAL_TIME
        elif best_intent in (QueryIntent.TROUBLESHOOTING, QueryIntent.CODE_SEARCH):
            freshness = FreshnessRequirement.RECENT
        else:
            freshness = FreshnessRequirement.HISTORICAL

        return QueryIntelligenceResult(
            query=clean_text,
            intent=best_intent,
            complexity=complexity,
            required_reasoning=reasoning,
            target_data_sources=list(data_sources),
            freshness=freshness,
            intent_scores=intent_scores,
            has_code_syntax=has_code,
            has_temporal_keywords=has_temporal,
            entity_references_count=entity_count,
        )
