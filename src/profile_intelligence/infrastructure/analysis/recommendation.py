"""Profile recommendations based on similarity.

```
analysis/
  recommendation.py
```
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.repositories import ProfileEntity
from profile_intelligence.infrastructure.analysis.similarity import (
    ProfileSimilarityAnalyzer,
    SimilarityScore,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ProfileRecommendation:
    """One recommended profile relative to a seed profile."""

    profile_id: int
    display_name: str
    score: SimilarityScore
    reason: str


class ProfileRecommender:
    """Recommend similar profiles from a candidate set."""

    def __init__(
        self,
        similarity: ProfileSimilarityAnalyzer | None = None,
        *,
        min_score: float = 0.35,
    ) -> None:
        self._similarity = similarity or ProfileSimilarityAnalyzer()
        self._min_score = min_score

    def recommend(
        self,
        seed: ProfileEntity,
        candidates: Sequence[ProfileEntity],
        *,
        limit: int = 5,
    ) -> tuple[ProfileRecommendation, ...]:
        """Return up to *limit* recommendations for *seed*."""
        if seed.id is None:
            return ()

        scored: list[ProfileRecommendation] = []
        for candidate in candidates:
            if candidate.id is None or candidate.id == seed.id:
                continue
            score = self._similarity.score(
                seed,
                candidate,
                left_id=seed.id,
                right_id=candidate.id,
            )
            if score.value < self._min_score:
                continue
            reason = (
                f"matched {', '.join(score.matched_fields)}"
                if score.matched_fields
                else f"similarity {score.percent}%"
            )
            scored.append(
                ProfileRecommendation(
                    profile_id=candidate.id,
                    display_name=candidate.display_name,
                    score=score,
                    reason=reason,
                )
            )

        scored.sort(key=lambda item: (-item.score.value, item.display_name.lower()))
        result = tuple(scored[: max(0, limit)])
        logger.info(
            "Recommendations for id=%s: candidates=%d returned=%d",
            seed.id,
            len(candidates),
            len(result),
        )
        return result
