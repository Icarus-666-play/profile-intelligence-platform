"""Confidence Score value object.

```
Confidence Score

0-100
```
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from profile_intelligence.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class ConfidenceScore:
    """Profile confidence score on a fixed 0-100 scale."""

    MIN: ClassVar[int] = 0
    MAX: ClassVar[int] = 100

    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise ValidationError(
                f"Confidence Score must be an int, got {type(self.value).__name__}"
            )
        if self.value < self.MIN or self.value > self.MAX:
            raise ValidationError(
                f"Confidence Score must be between {self.MIN} and {self.MAX}, "
                f"got {self.value}"
            )

    @classmethod
    def clamp(cls, raw: int | float) -> ConfidenceScore:
        """Build a score, clamping *raw* into ``[0, 100]``."""
        try:
            numeric = round(float(raw))
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"Confidence Score must be numeric, got {raw!r}",
                cause=exc,
            ) from exc
        return cls(max(cls.MIN, min(cls.MAX, numeric)))

    @classmethod
    def from_ratio(cls, earned: int | float, maximum: int | float) -> ConfidenceScore:
        """Scale *earned* / *maximum* onto the 0-100 confidence scale."""
        try:
            top = float(maximum)
            got = float(earned)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Confidence Score ratio inputs must be numeric",
                cause=exc,
            ) from exc
        if top <= 0:
            return cls(cls.MIN)
        return cls.clamp((got / top) * cls.MAX)

    def __int__(self) -> int:
        return self.value

    def __str__(self) -> str:
        return str(self.value)

    @property
    def label(self) -> str:
        """Human-readable band for dashboards."""
        if self.value >= 80:
            return "high"
        if self.value >= 50:
            return "medium"
        return "low"
