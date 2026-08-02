"""Completeness-based profile scoring (Milestone 1)."""

from __future__ import annotations

from typing import Protocol

from profile_intelligence.core.exceptions import ScoringError


class ScoreableProfile(Protocol):
    """Minimal profile shape required by the completeness scorer."""

    display_name: str
    email: str | None
    phone: str | None
    title: str | None
    organization: str | None
    location: str | None
    tags: str | None
    notes: str | None
    external_id: str | None


# Weighted fields summing to 100.
_FIELD_WEIGHTS: tuple[tuple[str, int], ...] = (
    ("display_name", 25),
    ("email", 20),
    ("phone", 10),
    ("title", 10),
    ("organization", 10),
    ("location", 10),
    ("tags", 5),
    ("notes", 5),
    ("external_id", 5),
)


class CompletenessScorer:
    """Score a profile from 0-100 based on populated fields."""

    def score(self, profile: ScoreableProfile) -> int:
        """Return an integer completeness score in ``[0, 100]``."""
        try:
            total = 0
            for field_name, weight in _FIELD_WEIGHTS:
                value = getattr(profile, field_name, None)
                if _has_value(value):
                    total += weight
            return min(total, 100)
        except Exception as exc:
            raise ScoringError(
                "Failed to compute completeness score",
                cause=exc,
            ) from exc

    def apply(self, profile: ScoreableProfile) -> int:
        """Compute score and assign it to ``profile.score`` when mutable."""
        value = self.score(profile)
        try:
            profile.score = value  # type: ignore[attr-defined]
        except AttributeError:
            pass
        return value


def _has_value(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True
