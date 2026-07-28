"""
Evidence Sufficiency Gate evaluating context quality before LLM answer generation.
"""

from __future__ import annotations

import re
from typing import Any, Callable

from app.core.config import get_settings
from app.core.exceptions import InsufficientEvidenceError
from app.core.logging import get_logger
from app.domain.entities.chunk import Chunk
from app.domain.value_objects.evidence_score import EvidenceScore, EvidenceVerdict

logger = get_logger(__name__, component="evidence_gate")


class EvidenceSufficiencyGate:
    """
    Innovation 2: Evidence Sufficiency Gate.
    Scores retrieved context before generation. Refuses weak context to prevent hallucinations.
    """

    def __init__(self, max_retries: int | None = None) -> None:
        settings = get_settings()
        self.max_retries = max_retries or settings.retrieval.evidence_max_retries
        self.min_coverage = settings.retrieval.evidence_min_coverage
        self.min_confidence = settings.retrieval.evidence_min_confidence
        self.min_sources = settings.retrieval.evidence_min_sources

    def evaluate_evidence(self, query: str, chunks: list[Chunk]) -> EvidenceScore:
        """
        Compute multi-dimensional EvidenceScore from retrieved chunks.
        """
        query_keywords = [w for w in re.findall(r"\b\w+\b", query.lower()) if len(w) > 2]
        score = EvidenceScore.from_chunks(chunks=chunks, query_keywords=query_keywords)

        logger.info(
            "evidence_evaluated",
            overall_score=score.overall_score,
            verdict=score.verdict.value,
            weakest=score.weakest_dimension,
            chunks_count=len(chunks),
        )
        return score

    async def verify_or_retry(
        self,
        query: str,
        chunks: list[Chunk],
        retrieval_fn: Callable[[str], Any],
    ) -> tuple[list[Chunk], EvidenceScore]:
        """
        Evaluate context. If BORDERLINE, reformulate query and retry.
        If still INSUFFICIENT, raise InsufficientEvidenceError.

        Returns:
            Tuple of (Verified Chunks, Final EvidenceScore)
        """
        current_query = query
        current_chunks = chunks
        score = self.evaluate_evidence(current_query, current_chunks)

        if score.verdict == EvidenceVerdict.SUFFICIENT:
            return current_chunks, score

        # Automated retry loop for BORDERLINE evidence
        for attempt in range(1, self.max_retries + 1):
            if score.verdict == EvidenceVerdict.SUFFICIENT:
                break
            if score.verdict == EvidenceVerdict.INSUFFICIENT and attempt > 1:
                break

            logger.info("evidence_borderline_retrying", attempt=attempt, query=current_query)

            # Reformulate query (expand with synonyms / keywords)
            reformulated_query = self._reformulate_query(current_query, score.weakest_dimension)
            new_chunks = await retrieval_fn(reformulated_query)

            # Combine unique chunks from retry
            combined_chunks = self._merge_chunks(current_chunks, new_chunks)
            new_score = self.evaluate_evidence(current_query, combined_chunks)

            if new_score.overall_score > score.overall_score:
                current_chunks = combined_chunks
                score = new_score

        if score.verdict == EvidenceVerdict.INSUFFICIENT:
            logger.warning(
                "insufficient_evidence_gate_failed",
                query=query,
                score=score.overall_score,
            )
            raise InsufficientEvidenceError(
                coverage=score.coverage,
                confidence=score.confidence,
                sources_found=len({c.document_id for c in current_chunks}),
                query=query,
            )

        return current_chunks, score

    def _reformulate_query(self, query: str, weakest_dimension: str) -> str:
        """Simple rule-based query expansion for retries."""
        if weakest_dimension == "coverage":
            return f"{query} architecture design guide overview"
        elif weakest_dimension == "freshness":
            return f"{query} recent latest updated"
        else:
            return f"{query} technical documentation details"

    def _merge_chunks(self, existing: list[Chunk], new_chunks: list[Chunk]) -> list[Chunk]:
        seen = {c.id for c in existing}
        merged = list(existing)
        for nc in new_chunks:
            if nc.id not in seen:
                seen.add(nc.id)
                merged.append(nc)
        return merged
