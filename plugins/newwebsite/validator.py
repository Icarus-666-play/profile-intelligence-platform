"""Validate extracted NewWebsite profiles before normalization.

```
plugins/
  newwebsite/
    validator.py
```
"""

from __future__ import annotations

from dataclasses import dataclass, field

from newwebsite.extractor import ExtractedProfile
from profile_intelligence.core.logging import get_logger

logger = get_logger("importers.external.newwebsite.validator")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Outcome of NewWebsite profile validation."""

    ok: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        """Alias for :attr:`ok`."""
        return self.ok


class NewWebsiteValidator:
    """Reject incomplete NewWebsite extracts (name required)."""

    def validate(self, profile: ExtractedProfile) -> ValidationResult:
        """Return whether *profile* may proceed to normalization."""
        errors: list[str] = []
        warnings = list(profile.warnings)

        if not profile.is_complete:
            errors.append("name is required")

        if profile.email is None and profile.phone is None:
            warnings.append("profile has neither email nor phone")

        result = ValidationResult(
            ok=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )
        if not result.ok:
            logger.warning(
                "NewWebsite validation failed: %s",
                "; ".join(result.errors),
            )
        return result
