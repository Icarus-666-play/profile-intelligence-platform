"""Profile classification.

```
analysis/
  classification.py
```
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.repositories import ProfileEntity
from profile_intelligence.domain.value_objects.confidence import ConfidenceScore

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ProfileClassification:
    """Classification labels for one profile."""

    profile_id: int | None
    display_name: str
    source_class: str
    confidence_band: str
    completeness_class: str
    labels: tuple[str, ...]


class ProfileClassifier:
    """Assign deterministic labels to profiles (no ML required)."""

    def classify(self, profile: ProfileEntity) -> ProfileClassification:
        """Classify a single profile."""
        source_class = (profile.source or "unknown").strip().lower() or "unknown"
        confidence_band = self._confidence_band(profile.score)
        completeness_class = self._completeness_class(profile)
        labels = tuple(
            label
            for label in (
                f"source:{source_class}",
                f"confidence:{confidence_band}",
                f"completeness:{completeness_class}",
            )
        )
        result = ProfileClassification(
            profile_id=profile.id,
            display_name=profile.display_name,
            source_class=source_class,
            confidence_band=confidence_band,
            completeness_class=completeness_class,
            labels=labels,
        )
        logger.debug(
            "Classified id=%s labels=%s",
            profile.id,
            result.labels,
        )
        return result

    def classify_many(
        self,
        profiles: Sequence[ProfileEntity],
    ) -> tuple[ProfileClassification, ...]:
        """Classify many profiles."""
        return tuple(self.classify(profile) for profile in profiles)

    def _confidence_band(self, score: int | None) -> str:
        if score is None:
            return "unscored"
        return ConfidenceScore.clamp(score).label

    def _completeness_class(self, profile: ProfileEntity) -> str:
        filled = 0
        for field_name in (
            "display_name",
            "email",
            "phone",
            "title",
            "organization",
            "location",
            "tags",
            "notes",
            "external_id",
        ):
            value = getattr(profile, field_name, None)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            filled += 1
        if filled >= 7:
            return "rich"
        if filled >= 4:
            return "moderate"
        return "sparse"
