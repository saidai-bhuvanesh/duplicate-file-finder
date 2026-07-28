"""
EvidenceScore value object.

Represents the output of the Evidence Sufficiency Gate —
a multi-dimensional scoring of retrieved context quality
before allowing the LLM to generate an answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EvidenceVerdict(str, Enum):
    """Final verdict from the Evidence Sufficiency Gate."""

    SUFFICIENT = "sufficient"       # Proceed to generation
    BORDERLINE = "borderline"       # Retry with expanded query
    INSUFFICIENT = "insufficient"   # Do not generate; return error


@dataclass(frozen=True)
class EvidenceScore:
    """
    Multi-dimensional quality score for retrieved evidence.

    This value object is produced by the Evidence Gate before
    LLM answer generation. If verdict is INSUFFICIENT after
    max retries, the system returns InsufficientEvidenceError
    instead of hallucinating.

    Dimensions:
        coverage:       0-1  How much of the query is covered by retrieved context
        confidence:     0-1  Average retrieval confidence score
        source_diversity: 0-1  Proportion of unique source documents
        freshness:      0-1  Recency of sources (1=very recent, 0=very old)
        authority:      0-1  Authority score of source systems
        completeness:   0-1  Whether all sub-questions are addressed

    Aggregated:
        overall_score:  Weighted average of the six dimensions
    """

    coverage: float
    confidence: float
    source_diversity: float
    freshness: float
    authority: float
    completeness: float

    # Dimension weights (must sum to 1.0)
    _WEIGHTS: dict[str, float] = field(
        default_factory=lambda: {
            "coverage": 0.30,
            "confidence": 0.25,
            "source_diversity": 0.15,
            "freshness": 0.10,
            "authority": 0.10,
            "completeness": 0.10,
        },
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Validate all scores are in [0, 1]."""
        for attr in ("coverage", "confidence", "source_diversity", "freshness",
                     "authority", "completeness"):
            value = getattr(self, attr)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"EvidenceScore.{attr} must be in [0, 1], got {value}")

    @property
    def overall_score(self) -> float:
        """Weighted average evidence score."""
        weights = self._WEIGHTS
        return round(
            self.coverage * weights["coverage"]
            + self.confidence * weights["confidence"]
            + self.source_diversity * weights["source_diversity"]
            + self.freshness * weights["freshness"]
            + self.authority * weights["authority"]
            + self.completeness * weights["completeness"],
            4,
        )

    @property
    def verdict(self) -> EvidenceVerdict:
        """
        Determine verdict based on overall score thresholds.

        Thresholds:
            >= 0.65  → SUFFICIENT (proceed to generation)
            >= 0.40  → BORDERLINE (retry with query reformulation)
            < 0.40   → INSUFFICIENT (refuse to answer)
        """
        score = self.overall_score
        if score >= 0.65:
            return EvidenceVerdict.SUFFICIENT
        if score >= 0.40:
            return EvidenceVerdict.BORDERLINE
        return EvidenceVerdict.INSUFFICIENT

    @property
    def weakest_dimension(self) -> str:
        """Return the name of the lowest-scoring dimension."""
        dimensions = {
            "coverage": self.coverage,
            "confidence": self.confidence,
            "source_diversity": self.source_diversity,
            "freshness": self.freshness,
            "authority": self.authority,
            "completeness": self.completeness,
        }
        return min(dimensions, key=lambda k: dimensions[k])

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API response and logging."""
        return {
            "coverage": self.coverage,
            "confidence": self.confidence,
            "source_diversity": self.source_diversity,
            "freshness": self.freshness,
            "authority": self.authority,
            "completeness": self.completeness,
            "overall_score": self.overall_score,
            "verdict": self.verdict.value,
            "weakest_dimension": self.weakest_dimension,
        }

    @classmethod
    def from_chunks(
        cls,
        chunks: list[Any],
        query_keywords: list[str] | None = None,
        max_age_days: int = 365,
    ) -> "EvidenceScore":
        """
        Compute EvidenceScore from a list of retrieved Chunk objects.

        This is a factory method that extracts scoring signals from
        actual retrieved chunks. Each dimension is computed from
        observable chunk properties.

        Args:
            chunks: List of Chunk domain entities with retrieval scores.
            query_keywords: Keywords from the original query (for coverage).
            max_age_days: Max age in days for freshness computation.

        Returns:
            EvidenceScore value object.
        """
        from datetime import datetime, timezone

        if not chunks:
            return cls(
                coverage=0.0,
                confidence=0.0,
                source_diversity=0.0,
                freshness=0.0,
                authority=0.0,
                completeness=0.0,
            )

        # ── Confidence: average of final retrieval scores ─────────────────────
        scores = [c.final_score for c in chunks if c.final_score is not None]
        confidence = float(sum(scores) / len(scores)) if scores else 0.0
        confidence = min(1.0, confidence)  # Normalize to [0,1]

        # ── Source diversity: unique docs / total chunks ──────────────────────
        unique_docs = len({c.document_id for c in chunks})
        source_diversity = min(1.0, unique_docs / max(len(chunks), 1))

        # ── Coverage: keyword overlap between query and chunks ────────────────
        if query_keywords:
            all_content = " ".join(c.content.lower() for c in chunks)
            matched = sum(1 for kw in query_keywords if kw.lower() in all_content)
            coverage = matched / len(query_keywords) if query_keywords else 0.5
        else:
            coverage = min(1.0, confidence * 1.2)  # Fallback estimate

        # ── Freshness: recency of source documents ────────────────────────────
        freshness_scores = []
        now = datetime.now(timezone.utc)
        for chunk in chunks:
            updated = chunk.metadata.get("updated_at")
            if updated:
                try:
                    if isinstance(updated, str):
                        from dateutil.parser import parse
                        updated = parse(updated)
                    if updated.tzinfo is None:
                        updated = updated.replace(tzinfo=timezone.utc)
                    age_days = (now - updated).days
                    freshness_scores.append(max(0.0, 1.0 - age_days / max_age_days))
                except Exception:
                    freshness_scores.append(0.5)
            else:
                freshness_scores.append(0.5)  # Unknown age — neutral
        freshness = float(sum(freshness_scores) / len(freshness_scores))

        # ── Authority: source system authority scores ─────────────────────────
        authority_map = {
            "confluence": 0.9,
            "github": 0.85,
            "jira": 0.8,
            "notion": 0.7,
            "slack": 0.5,
            "teams": 0.5,
            "local_file": 0.6,
        }
        auth_scores = []
        for chunk in chunks:
            source = chunk.metadata.get("source_system", "local_file").lower()
            auth_scores.append(authority_map.get(source, 0.6))
        authority = float(sum(auth_scores) / len(auth_scores))

        # ── Completeness: chunk count relative to top-k ──────────────────────
        # More chunks retrieved = more likely complete coverage
        target_k = 5
        completeness = min(1.0, len(chunks) / target_k)

        return cls(
            coverage=round(min(1.0, coverage), 4),
            confidence=round(confidence, 4),
            source_diversity=round(source_diversity, 4),
            freshness=round(freshness, 4),
            authority=round(authority, 4),
            completeness=round(completeness, 4),
        )
