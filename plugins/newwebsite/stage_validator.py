"""Adapt NewWebsiteValidator to the platform ISourceValidator port."""

from __future__ import annotations

from newwebsite.extractor import ExtractedProfile
from newwebsite.validator import NewWebsiteValidator
from profile_intelligence.domain.interfaces.plugin_pipeline import (
    StageValidationResult,
)
from profile_intelligence.domain.value_objects.importing import RawRecord


class NewWebsiteStageValidator:
    """Bridge plugin ValidationResult → StageValidationResult."""

    def __init__(self, inner: NewWebsiteValidator | None = None) -> None:
        self._inner = inner or NewWebsiteValidator()

    def validate(
        self,
        record: RawRecord,
        *,
        extracted: object | None = None,
    ) -> StageValidationResult:
        if isinstance(extracted, ExtractedProfile):
            result = self._inner.validate(extracted)
            return StageValidationResult(
                ok=result.ok,
                errors=result.errors,
                warnings=result.warnings,
            )
        name = str(record.get("display_name") or record.get("name") or "").strip()
        if not name:
            return StageValidationResult(ok=False, errors=("name is required",))
        return StageValidationResult(ok=True)
