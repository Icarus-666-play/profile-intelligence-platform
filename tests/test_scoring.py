"""Tests for Confidence Score (0-100) and completeness engine."""

from __future__ import annotations

import pytest

from profile_intelligence.core.config import ScoringSection
from profile_intelligence.core.exceptions import ValidationError
from profile_intelligence.domain.entities import ProfileDraft
from profile_intelligence.domain.value_objects import ConfidenceScore
from profile_intelligence.infrastructure.scoring import (
    CompletenessScorer,
    ConfidenceScorer,
)


def test_confidence_score_bounds() -> None:
    assert ConfidenceScore.MIN == 0
    assert ConfidenceScore.MAX == 100
    assert int(ConfidenceScore(0)) == 0
    assert int(ConfidenceScore(100)) == 100
    assert ConfidenceScore.clamp(-5).value == 0
    assert ConfidenceScore.clamp(150).value == 100
    assert ConfidenceScore.clamp(72.6).value == 73
    assert ConfidenceScore.from_ratio(25, 50).value == 50
    assert ConfidenceScore(90).label == "high"
    assert ConfidenceScore(55).label == "medium"
    assert ConfidenceScore(10).label == "low"


def test_confidence_score_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError, match="between 0 and 100"):
        ConfidenceScore(101)
    with pytest.raises(ValidationError, match="must be an int"):
        ConfidenceScore(True)  # type: ignore[arg-type]


def test_score_emptyish_profile() -> None:
    scorer = ConfidenceScorer()
    draft = ProfileDraft(display_name="Only Name")
    assert scorer.score(draft) == 25
    assert scorer.confidence(draft).value == 25


def test_score_full_profile() -> None:
    scorer = ConfidenceScorer()
    draft = ProfileDraft(
        display_name="Ada",
        email="ada@example.com",
        phone="1",
        title="Analyst",
        organization="AE",
        location="London",
        tags="math",
        notes="note",
        external_id="p-1",
    )
    assert scorer.score(draft) == 100
    assert scorer.apply(draft) == 100
    assert draft.score == 100
    assert scorer.confidence(draft).value == 100


def test_score_uses_config_weights_normalized_to_100() -> None:
    scoring = ScoringSection(
        max_score=50,
        weights={"display_name": 40, "email": 10},
    )
    scorer = ConfidenceScorer(scoring)
    draft = ProfileDraft(display_name="Ada", email="ada@example.com")
    # Engine total is 50/50 → confidence 100
    assert scorer.engine.score(draft) == 50
    assert scorer.score(draft) == 100


def test_completeness_engine_still_works() -> None:
    scorer = CompletenessScorer()
    draft = ProfileDraft(display_name="Only Name")
    assert scorer.score(draft) == 25
