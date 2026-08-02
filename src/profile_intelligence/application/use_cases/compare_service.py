"""Compare profiles side-by-side."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from profile_intelligence.core.exceptions import ValidationError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.infrastructure.database.models import Profile
from profile_intelligence.infrastructure.database.repository import ProfileRepository

logger = get_logger(__name__)

_COMPARE_FIELDS: tuple[str, ...] = (
    "display_name",
    "external_id",
    "email",
    "phone",
    "title",
    "organization",
    "location",
    "tags",
    "source",
    "notes",
    "score",
)


@dataclass(frozen=True, slots=True)
class FieldDiff:
    """One compared field between two profiles."""

    field: str
    left: str
    right: str
    equal: bool


@dataclass(frozen=True, slots=True)
class ProfileComparison:
    """Result of comparing two profile entities."""

    left_id: int
    right_id: int
    left_name: str
    right_name: str
    fields: tuple[FieldDiff, ...]

    @property
    def differences(self) -> tuple[FieldDiff, ...]:
        """Fields that differ."""
        return tuple(item for item in self.fields if not item.equal)

    @property
    def matches(self) -> tuple[FieldDiff, ...]:
        """Fields that match."""
        return tuple(item for item in self.fields if item.equal)


class CompareService:
    """Build structured comparisons between stored profiles."""

    def __init__(self, repository: ProfileRepository) -> None:
        self._repository = repository

    def compare_ids(self, left_id: int, right_id: int) -> ProfileComparison:
        """Compare two profiles by primary key."""
        if left_id == right_id:
            raise ValidationError("Cannot compare a profile to itself")
        left = self._repository.get_by_id(left_id)
        right = self._repository.get_by_id(right_id)
        if left is None:
            raise ValidationError(f"Profile not found: id={left_id}")
        if right is None:
            raise ValidationError(f"Profile not found: id={right_id}")
        return self.compare_profiles(left, right)

    def compare_profiles(
        self,
        left: Profile,
        right: Profile,
    ) -> ProfileComparison:
        """Compare two profile entities field-by-field."""
        if left.id is None or right.id is None:
            raise ValidationError("Both profiles must have persisted ids")

        fields: list[FieldDiff] = []
        for name in _COMPARE_FIELDS:
            left_value = _fmt(getattr(left, name))
            right_value = _fmt(getattr(right, name))
            fields.append(
                FieldDiff(
                    field=name,
                    left=left_value,
                    right=right_value,
                    equal=left_value == right_value,
                )
            )

        comparison = ProfileComparison(
            left_id=left.id,
            right_id=right.id,
            left_name=left.display_name,
            right_name=right.display_name,
            fields=tuple(fields),
        )
        logger.debug(
            "Compared profiles %s vs %s: %d difference(s)",
            left.id,
            right.id,
            len(comparison.differences),
        )
        return comparison

    def compare_sources(self, left_source: str, right_source: str) -> Sequence[str]:
        """Return a short textual summary comparing two sources."""
        left = left_source.strip()
        right = right_source.strip()
        if not left or not right:
            raise ValidationError("Both source names are required")
        if left == right:
            raise ValidationError("Cannot compare a source to itself")

        profiles = self._repository.list_all(limit=100_000, offset=0)
        left_rows = [row for row in profiles if (row.source or "") == left]
        right_rows = [row for row in profiles if (row.source or "") == right]

        left_emails = {
            (row.email or "").lower() for row in left_rows if row.email
        }
        right_emails = {
            (row.email or "").lower() for row in right_rows if row.email
        }
        overlap = left_emails & right_emails

        left_avg = _avg_score(left_rows)
        right_avg = _avg_score(right_rows)

        lines = [
            f"Source '{left}': {len(left_rows)} profile(s), avg score={left_avg}",
            f"Source '{right}': {len(right_rows)} profile(s), avg score={right_avg}",
            f"Shared emails: {len(overlap)}",
        ]
        return lines


def _fmt(value: object) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    return text or "-"


def _avg_score(profiles: Sequence[Profile]) -> str:
    scores = [row.score for row in profiles if row.score is not None]
    if not scores:
        return "-"
    return str(round(sum(scores) / len(scores), 1))
