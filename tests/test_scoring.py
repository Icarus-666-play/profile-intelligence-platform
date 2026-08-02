"""Tests for completeness scoring."""

from __future__ import annotations

from profile_intelligence.core.config import ScoringSection
from profile_intelligence.extractors import ProfileDraft
from profile_intelligence.scoring import CompletenessScorer


def test_score_emptyish_profile() -> None:
    scorer = CompletenessScorer()
    draft = ProfileDraft(display_name="Only Name")
    assert scorer.score(draft) == 25


def test_score_full_profile() -> None:
    scorer = CompletenessScorer()
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


def test_score_uses_config_weights() -> None:
    scoring = ScoringSection(
        max_score=50,
        weights={"display_name": 40, "email": 10},
    )
    scorer = CompletenessScorer(scoring)
    draft = ProfileDraft(display_name="Ada", email="ada@example.com")
    assert scorer.score(draft) == 50
