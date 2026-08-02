"""Profile similarity scoring.

```
analysis/
  similarity.py
```
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from profile_intelligence.core.logging import get_logger

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)

_DEFAULT_WEIGHTS: Mapping[str, float] = {
    "display_name": 0.30,
    "email": 0.25,
    "phone": 0.15,
    "organization": 0.10,
    "location": 0.10,
    "tags": 0.10,
}


class SimilarableProfile(Protocol):
    """Minimal profile shape for similarity analysis."""

    display_name: str
    email: str | None
    phone: str | None
    organization: str | None
    location: str | None
    tags: str | None
    external_id: str | None
    source: str | None


@dataclass(frozen=True, slots=True)
class SimilarityScore:
    """Similarity between two profiles on a 0.0-1.0 scale."""

    value: float
    left_id: int | None = None
    right_id: int | None = None
    matched_fields: tuple[str, ...] = ()

    @property
    def percent(self) -> int:
        """Integer percent in ``[0, 100]``."""
        return round(max(0.0, min(1.0, self.value)) * 100)


class ProfileSimilarityAnalyzer:
    """Compute heuristic field/token similarity between profiles."""

    def __init__(self, *, weights: Mapping[str, float] | None = None) -> None:
        self._weights = dict(weights or _DEFAULT_WEIGHTS)

    def score(
        self,
        left: SimilarableProfile,
        right: SimilarableProfile,
        *,
        left_id: int | None = None,
        right_id: int | None = None,
    ) -> SimilarityScore:
        """Return a weighted similarity score for *left* vs *right*."""
        total_weight = 0.0
        earned = 0.0
        matched: list[str] = []

        for field_name, weight in self._weights.items():
            left_value = getattr(left, field_name, None)
            right_value = getattr(right, field_name, None)
            field_score = self._field_score(left_value, right_value)
            if field_score is None:
                continue
            total_weight += float(weight)
            earned += float(weight) * field_score
            if field_score >= 0.99:
                matched.append(field_name)

        # Exact external_id match is a strong signal.
        if _norm(getattr(left, "external_id", None)) and _norm(
            getattr(left, "external_id", None)
        ) == _norm(getattr(right, "external_id", None)):
            earned = total_weight
            matched = sorted(set(matched) | {"external_id"})

        value = (earned / total_weight) if total_weight > 0 else 0.0
        result = SimilarityScore(
            value=round(value, 4),
            left_id=left_id,
            right_id=right_id,
            matched_fields=tuple(matched),
        )
        logger.debug(
            "Similarity %.2f left=%s right=%s matched=%s",
            result.value,
            left_id,
            right_id,
            result.matched_fields,
        )
        return result

    def _field_score(self, left: object | None, right: object | None) -> float | None:
        left_text = _norm(left)
        right_text = _norm(right)
        if not left_text or not right_text:
            return None
        if left_text == right_text:
            return 1.0
        left_tokens = _tokens(left_text)
        right_tokens = _tokens(right_text)
        if not left_tokens or not right_tokens:
            return 0.0
        overlap = left_tokens & right_tokens
        union = left_tokens | right_tokens
        return len(overlap) / len(union) if union else 0.0


def _norm(value: object | None) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def _tokens(text: str) -> set[str]:
    return {match.group(0).lower() for match in _TOKEN_RE.finditer(text)}
