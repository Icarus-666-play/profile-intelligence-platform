"""Validate extracted EuroGirls profiles.

```
Downloader
 ↓
Parser
 ↓
Extractor
 ↓
Normalizer
 ↓
Validator
 ↓
Importer
```
"""

from __future__ import annotations

from dataclasses import dataclass, field

from eurogirls.extractor import ExtractedProfile
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.plugin_pipeline import (
    StageValidationResult,
)
from profile_intelligence.domain.value_objects.importing import RawRecord

logger = get_logger("importers.external.eurogirls.validator")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """EuroGirls validation outcome (plugin-local alias)."""

    ok: bool
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)


class EuroGirlsValidator:
    """Reject incomplete EuroGirls extracts (name required)."""

    def validate_extracted(self, profile: ExtractedProfile) -> ValidationResult:
        """Validate an extracted profile before/with normalization."""
        errors: list[str] = []
        warnings = list(profile.warnings)
        if not profile.is_complete:
            errors.append(
                "Rejected incomplete EuroGirls document (name is required)"
            )
        return ValidationResult(
            ok=not errors,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def validate(
        self,
        record: RawRecord,
        *,
        extracted: object | None = None,
    ) -> StageValidationResult:
        """ISourceValidator entrypoint used by :class:`PluginPipeline`."""
        if isinstance(extracted, ExtractedProfile):
            result = self.validate_extracted(extracted)
            return StageValidationResult(
                ok=result.ok,
                errors=result.errors,
                warnings=result.warnings,
            )
        name = str(record.get("display_name") or record.get("name") or "").strip()
        if not name:
            return StageValidationResult(
                ok=False,
                errors=(
                    "Rejected incomplete EuroGirls document (name is required)",
                ),
            )
        return StageValidationResult(ok=True)
