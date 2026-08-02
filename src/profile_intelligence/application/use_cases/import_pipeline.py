"""End-to-end import pipeline.

```
pipeline:
  - parser
  - normalizer
  - validator
  - duplicate_detector
  - scorer
  - repository
```

Flow:

```
File
 ↓
RawDocument
 ↓
ProcessingChain (configured stages)
 ↓
SQLite
```
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from profile_intelligence.application.pipeline import (
    DocumentParser,
    ProcessingChain,
    ProcessingResult,
    ProfileNormalizer,
    ProfileValidator,
)
from profile_intelligence.application.pipeline.duplicate_detector import (
    DuplicateDetector,
)
from profile_intelligence.application.pipeline.scorer import ProfileScorer
from profile_intelligence.core.config import DEFAULT_PIPELINE_STAGES
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.entities.profile import ProfileExtractor
from profile_intelligence.domain.interfaces.importers import ImporterPlugin
from profile_intelligence.domain.value_objects.documents import (
    ParsedDocument,
    RawDocument,
)
from profile_intelligence.domain.value_objects.importing import ImportResult
from profile_intelligence.infrastructure.database.models import Profile
from profile_intelligence.infrastructure.database.repository import ProfileRepository
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.infrastructure.scoring.completeness import CompletenessScorer

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    """Outcome of a full File → SQLite pipeline run."""

    path: str
    plugin: str
    records_read: int
    created: int
    updated: int
    skipped: int
    errors: tuple[str, ...] = field(default_factory=tuple)
    entities: tuple[Profile, ...] = field(default_factory=tuple)
    stages_run: tuple[str, ...] = field(default_factory=tuple)

    @property
    def success(self) -> bool:
        """True when at least one profile entity was written."""
        return (self.created + self.updated) > 0

    @property
    def written(self) -> int:
        """Total profile entities written (created + updated)."""
        return self.created + self.updated


class ImportPipeline:
    """Orchestrates File → configured stages → SQLite."""

    def __init__(
        self,
        registry: ImporterRegistry,
        repository: ProfileRepository,
        *,
        stages: Sequence[str] | None = None,
        parser: DocumentParser | None = None,
        normalizer: ProfileNormalizer | None = None,
        validator: ProfileValidator | None = None,
        duplicate_detector: DuplicateDetector | None = None,
        extractor: ProfileExtractor | None = None,
        scorer: CompletenessScorer | ProfileScorer | None = None,
        processing: ProcessingChain | None = None,
    ) -> None:
        self._registry = registry
        self._repository = repository
        if stages is not None:
            resolved_stages = tuple(stages)
        else:
            resolved_stages = DEFAULT_PIPELINE_STAGES

        self.processing = processing or ProcessingChain(
            registry,
            repository,
            stages=resolved_stages,
            parser=parser,
            normalizer=normalizer,
            validator=validator,
            duplicate_detector=duplicate_detector,
            extractor=extractor,
            scorer=scorer,
        )
        if processing is not None:
            self.processing.set_repository(repository)

        self.parser = self.processing.parser
        self.normalizer = self.processing.normalizer
        self.validator = self.processing.validator

    def process(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
        plugin: ImporterPlugin | None = None,
    ) -> PipelineResult:
        """Run the full configured pipeline for a single file."""
        document = RawDocument.from_path(
            path,
            source=source,
            plugin_name=plugin_name,
        )
        logger.info(
            "Pipeline start: %s stages=%s",
            document.path,
            " → ".join(self.processing.stages),
        )
        processed = self.processing.run(
            document,
            source=source,
            plugin=plugin,
        )
        return self._to_result(processed)

    def load_document(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
    ) -> RawDocument:
        """File → RawDocument."""
        return RawDocument.from_path(
            path, source=source, plugin_name=plugin_name
        )

    def parse_document(
        self,
        document: RawDocument,
        *,
        plugin: ImporterPlugin | None = None,
    ) -> ParsedDocument:
        """RawDocument → Parser output."""
        return self.parser.parse(document, plugin=plugin)

    def process_document(
        self,
        document: RawDocument,
        *,
        source: str | None = None,
        plugin: ImporterPlugin | None = None,
    ) -> ProcessingResult:
        """Run stages through scorer (no repository persistence)."""
        return self.processing.run(
            document,
            source=source,
            plugin=plugin,
            exclude_stages=("repository",),
        )

    def parse_file(
        self,
        path: PathLike,
        *,
        plugin_name: str | None = None,
        plugin: ImporterPlugin | None = None,
    ) -> tuple[ImporterPlugin, ImportResult]:
        """Compatibility helper: resolve plugin and return ImportResult."""
        document = RawDocument.from_path(path, plugin_name=plugin_name)
        resolved = self.parser.resolve_plugin(document, plugin=plugin)
        parsed = self.parser.parse(document, plugin=resolved)
        result = ImportResult.from_records(
            parsed.records,
            skipped=parsed.records_skipped,
            errors=parsed.errors,
            metadata=dict(parsed.metadata),
        )
        return resolved, result

    def persist_parsed(
        self,
        parsed: ParsedDocument,
        *,
        source: str | None = None,
    ) -> PipelineResult:
        """Run post-parser stages (including repository) for *parsed*."""
        processed = self.processing.run_from_parsed(parsed, source=source)
        return self._to_result(processed)

    def _to_result(self, processed: ProcessingResult) -> PipelineResult:
        """Map a :class:`ProcessingResult` into a :class:`PipelineResult`."""
        result = PipelineResult(
            path=str(processed.parsed.path),
            plugin=processed.parsed.plugin_name,
            records_read=processed.parsed.records_read,
            created=processed.created,
            updated=processed.updated,
            skipped=processed.skipped,
            errors=processed.errors,
            entities=processed.entities,
            stages_run=processed.stages_run,
        )
        logger.info(
            "Pipeline complete: created=%d updated=%d skipped=%d errors=%d",
            result.created,
            result.updated,
            result.skipped,
            len(result.errors),
        )
        return result
