"""Explicit Parser → Normalizer → Validator chain.

```
Parser
 ↓
Normalizer
 ↓
Validator
```
"""

from __future__ import annotations

from dataclasses import dataclass, field

from profile_intelligence.application.pipeline.normalizer import ProfileNormalizer
from profile_intelligence.application.pipeline.parser import DocumentParser
from profile_intelligence.application.pipeline.validator import ProfileValidator
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.entities.profile import ProfileDraft, ProfileExtractor
from profile_intelligence.domain.interfaces.importers import ImporterPlugin
from profile_intelligence.domain.value_objects.documents import (
    ParsedDocument,
    RawDocument,
)
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    """Output of Parser → Normalizer → Validator."""

    parsed: ParsedDocument
    normalized: tuple[ProfileDraft, ...]
    validated: tuple[ProfileDraft, ...]
    normalize_errors: tuple[str, ...] = field(default_factory=tuple)
    validation_errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def source(self) -> str:
        """Effective source label for validated drafts."""
        return (
            self.parsed.document.source
            or self.parsed.plugin_name
        )

    @property
    def errors(self) -> tuple[str, ...]:
        """All stage errors (parse metadata + normalize + validate)."""
        return tuple(
            list(self.parsed.errors)
            + list(self.normalize_errors)
            + list(self.validation_errors)
        )

    @property
    def skipped(self) -> int:
        """Rows skipped across parse / normalize / validate stages."""
        return (
            self.parsed.records_skipped
            + len(self.normalize_errors)
            + len(self.validation_errors)
        )


class ProcessingChain:
    """Runs Parser → Normalizer → Validator as one unit."""

    def __init__(
        self,
        registry: ImporterRegistry,
        *,
        parser: DocumentParser | None = None,
        normalizer: ProfileNormalizer | None = None,
        validator: ProfileValidator | None = None,
        extractor: ProfileExtractor | None = None,
    ) -> None:
        self.parser = parser or DocumentParser(registry)
        self.normalizer = normalizer or ProfileNormalizer(extractor)
        self.validator = validator or ProfileValidator()

    def run(
        self,
        document: RawDocument,
        *,
        source: str | None = None,
        plugin: ImporterPlugin | None = None,
    ) -> ProcessingResult:
        """Execute Parser → Normalizer → Validator for *document*."""
        # Parser
        parsed = self.parser.parse(document, plugin=plugin)
        source_name = source or parsed.document.source or parsed.plugin_name
        logger.info(
            "Processing chain: Parser complete (%d record(s))",
            len(parsed.records),
        )

        # Normalizer
        drafts, normalize_errors = self.normalizer.normalize_many(
            parsed.records,
            source_override=source_name,
        )
        logger.info(
            "Processing chain: Normalizer complete (%d draft(s), %d error(s))",
            len(drafts),
            len(normalize_errors),
        )

        # Validator
        validated, validation_errors = self.validator.validate_many(drafts)
        logger.info(
            "Processing chain: Validator complete (%d accepted, %d rejected)",
            len(validated),
            len(validation_errors),
        )

        return ProcessingResult(
            parsed=parsed,
            normalized=tuple(drafts),
            validated=tuple(validated),
            normalize_errors=tuple(normalize_errors),
            validation_errors=tuple(validation_errors),
        )

    def run_from_parsed(
        self,
        parsed: ParsedDocument,
        *,
        source: str | None = None,
    ) -> ProcessingResult:
        """Run Normalizer → Validator starting from an already-parsed document."""
        source_name = source or parsed.document.source or parsed.plugin_name
        drafts, normalize_errors = self.normalizer.normalize_many(
            parsed.records,
            source_override=source_name,
        )
        validated, validation_errors = self.validator.validate_many(drafts)
        return ProcessingResult(
            parsed=parsed,
            normalized=tuple(drafts),
            validated=tuple(validated),
            normalize_errors=tuple(normalize_errors),
            validation_errors=tuple(validation_errors),
        )
