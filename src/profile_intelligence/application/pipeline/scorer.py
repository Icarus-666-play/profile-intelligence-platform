"""Scorer stage for the import pipeline."""

from __future__ import annotations

from collections.abc import Sequence

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.infrastructure.scoring.completeness import CompletenessScorer

logger = get_logger(__name__)


class ProfileScorer:
    """Assign completeness scores to validated profile drafts."""

    def __init__(self, scorer: CompletenessScorer | None = None) -> None:
        self._scorer = scorer or CompletenessScorer()

    def score_many(self, drafts: Sequence[ProfileDraft]) -> tuple[ProfileDraft, ...]:
        """Score each draft in place and return them."""
        scored: list[ProfileDraft] = []
        for draft in drafts:
            draft.score = self._scorer.score(draft)
            scored.append(draft)
        logger.info("Scorer stage: scored=%d", len(scored))
        return tuple(scored)
