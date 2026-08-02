"""Confidence Score scorer (0-100).

```
Confidence Score

0-100
```

Computed via weighted field completeness (:class:`CompletenessScorer`) and
normalized onto the fixed 0-100 confidence scale.
"""

from __future__ import annotations

from collections.abc import Mapping

from profile_intelligence.core.config import ScoringSection
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.value_objects.confidence import ConfidenceScore
from profile_intelligence.infrastructure.scoring.completeness import (
    CompletenessScorer,
    ScoreableProfile,
)

logger = get_logger(__name__)


class ConfidenceScorer:
    """Assign a Confidence Score (0-100) to a profile."""

    def __init__(
        self,
        scoring: ScoringSection | None = None,
        *,
        engine: CompletenessScorer | None = None,
        weights: Mapping[str, int] | None = None,
        max_score: int | None = None,
    ) -> None:
        self._engine = engine or CompletenessScorer(
            scoring,
            weights=weights,
            max_score=max_score,
        )
        logger.debug(
            "ConfidenceScorer ready (scale=%d-%d, method=completeness)",
            ConfidenceScore.MIN,
            ConfidenceScore.MAX,
        )

    @property
    def engine(self) -> CompletenessScorer:
        """Underlying completeness scoring engine."""
        return self._engine

    def confidence(self, profile: ScoreableProfile) -> ConfidenceScore:
        """Return a :class:`ConfidenceScore` in ``[0, 100]``."""
        raw = self._engine.score(profile)
        maximum = self._engine.max_score
        if maximum == ConfidenceScore.MAX:
            return ConfidenceScore.clamp(raw)
        return ConfidenceScore.from_ratio(raw, maximum)

    def score(self, profile: ScoreableProfile) -> int:
        """Return the confidence score as an ``int`` in ``[0, 100]``."""
        return int(self.confidence(profile))

    def apply(self, profile: ScoreableProfile) -> int:
        """Compute confidence and assign ``profile.score`` when mutable."""
        value = self.score(profile)
        try:
            profile.score = value  # type: ignore[attr-defined]
        except AttributeError:
            pass
        return value
