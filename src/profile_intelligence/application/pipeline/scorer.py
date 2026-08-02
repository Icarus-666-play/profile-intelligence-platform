"""Scorer stage for the import pipeline — Confidence Score (0-100)."""

from __future__ import annotations

from collections.abc import Sequence

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.infrastructure.scoring.completeness import CompletenessScorer
from profile_intelligence.infrastructure.scoring.confidence import ConfidenceScorer

logger = get_logger(__name__)


class ProfileScorer:
    """Assign Confidence Scores (0-100) to validated profile drafts."""

    def __init__(
        self,
        scorer: ConfidenceScorer | CompletenessScorer | None = None,
    ) -> None:
        if isinstance(scorer, ConfidenceScorer):
            self._scorer = scorer
        elif isinstance(scorer, CompletenessScorer):
            self._scorer = ConfidenceScorer(engine=scorer)
        else:
            self._scorer = ConfidenceScorer()

    def score_many(self, drafts: Sequence[ProfileDraft]) -> tuple[ProfileDraft, ...]:
        """Score each draft in place and return them."""
        scored: list[ProfileDraft] = []
        for draft in drafts:
            draft.score = self._scorer.score(draft)
            scored.append(draft)
        logger.info("Scorer stage: confidence scores assigned=%d", len(scored))
        return tuple(scored)
