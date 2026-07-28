"""
Unit tests for EvidenceScore value object.
"""

import pytest

from app.domain.value_objects.evidence_score import EvidenceScore, EvidenceVerdict
from app.domain.entities.chunk import Chunk


@pytest.mark.unit
class TestEvidenceScore:
    def test_valid_score_creation(self):
        score = EvidenceScore(
            coverage=0.8,
            confidence=0.7,
            source_diversity=0.6,
            freshness=0.9,
            authority=0.85,
            completeness=0.75,
        )
        assert score.coverage == 0.8
        assert 0.0 <= score.overall_score <= 1.0

    def test_invalid_score_raises_error(self):
        with pytest.raises(ValueError, match="must be in"):
            EvidenceScore(
                coverage=1.5,  # Invalid: > 1.0
                confidence=0.7,
                source_diversity=0.6,
                freshness=0.9,
                authority=0.85,
                completeness=0.75,
            )

    def test_negative_score_raises_error(self):
        with pytest.raises(ValueError):
            EvidenceScore(
                coverage=-0.1,  # Invalid: < 0.0
                confidence=0.7,
                source_diversity=0.6,
                freshness=0.9,
                authority=0.85,
                completeness=0.75,
            )

    def test_sufficient_verdict(self):
        score = EvidenceScore(
            coverage=0.9,
            confidence=0.9,
            source_diversity=0.8,
            freshness=0.9,
            authority=0.9,
            completeness=0.9,
        )
        assert score.verdict == EvidenceVerdict.SUFFICIENT

    def test_insufficient_verdict(self):
        score = EvidenceScore(
            coverage=0.1,
            confidence=0.1,
            source_diversity=0.1,
            freshness=0.1,
            authority=0.1,
            completeness=0.1,
        )
        assert score.verdict == EvidenceVerdict.INSUFFICIENT

    def test_borderline_verdict(self):
        score = EvidenceScore(
            coverage=0.5,
            confidence=0.5,
            source_diversity=0.4,
            freshness=0.5,
            authority=0.5,
            completeness=0.5,
        )
        assert score.verdict == EvidenceVerdict.BORDERLINE

    def test_overall_score_between_zero_and_one(self):
        """Overall score must always be in [0, 1]."""
        for val in [0.0, 0.3, 0.5, 0.8, 1.0]:
            score = EvidenceScore(
                coverage=val,
                confidence=val,
                source_diversity=val,
                freshness=val,
                authority=val,
                completeness=val,
            )
            assert 0.0 <= score.overall_score <= 1.0

    def test_weakest_dimension(self):
        score = EvidenceScore(
            coverage=0.9,
            confidence=0.9,
            source_diversity=0.9,
            freshness=0.1,  # Weakest
            authority=0.9,
            completeness=0.9,
        )
        assert score.weakest_dimension == "freshness"

    def test_to_dict_contains_all_fields(self):
        score = EvidenceScore(
            coverage=0.7,
            confidence=0.7,
            source_diversity=0.6,
            freshness=0.8,
            authority=0.75,
            completeness=0.65,
        )
        d = score.to_dict()
        required_keys = [
            "coverage", "confidence", "source_diversity",
            "freshness", "authority", "completeness",
            "overall_score", "verdict", "weakest_dimension",
        ]
        for key in required_keys:
            assert key in d, f"Missing key: {key}"

    def test_from_chunks_empty_returns_zero_score(self):
        score = EvidenceScore.from_chunks([])
        assert score.coverage == 0.0
        assert score.confidence == 0.0
        assert score.verdict == EvidenceVerdict.INSUFFICIENT

    def test_from_chunks_with_chunks(self):
        chunks = [
            Chunk(
                document_id="doc-1",
                content="Kubernetes is a container orchestration platform.",
                final_score=0.85,
                metadata={"source_system": "confluence", "updated_at": "2024-06-01T00:00:00"},
            ),
            Chunk(
                document_id="doc-2",
                content="K8s supports horizontal pod autoscaling.",
                final_score=0.75,
                metadata={"source_system": "github", "updated_at": "2024-07-01T00:00:00"},
            ),
        ]
        score = EvidenceScore.from_chunks(
            chunks,
            query_keywords=["kubernetes", "container"],
        )
        assert score.confidence > 0.0
        assert score.source_diversity > 0.0  # 2 unique docs
        assert 0.0 <= score.overall_score <= 1.0

    def test_from_chunks_single_source_diversity(self):
        """Single document source should have low diversity."""
        chunks = [
            Chunk(document_id="doc-1", content="A", final_score=0.8, metadata={}),
            Chunk(document_id="doc-1", content="B", final_score=0.7, metadata={}),
            Chunk(document_id="doc-1", content="C", final_score=0.6, metadata={}),
        ]
        score = EvidenceScore.from_chunks(chunks)
        # 1 unique doc out of 3 chunks → diversity = 1/3 ≈ 0.33
        assert score.source_diversity < 0.5

    def test_evidence_score_is_frozen(self):
        """EvidenceScore is immutable (frozen dataclass)."""
        score = EvidenceScore(
            coverage=0.7,
            confidence=0.7,
            source_diversity=0.6,
            freshness=0.8,
            authority=0.75,
            completeness=0.65,
        )
        with pytest.raises((AttributeError, TypeError)):
            score.coverage = 0.9  # type: ignore
