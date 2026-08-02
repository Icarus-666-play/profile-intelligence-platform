"""Importer → Database facade over the staged import pipeline.

```
pipeline:
  - parser
  - normalizer
  - validator
  - duplicate_detector
  - scorer
  - repository
```
"""

from __future__ import annotations

from dataclasses import dataclass, field

from profile_intelligence.application.use_cases.import_pipeline import ImportPipeline
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.entities.profile import ProfileExtractor
from profile_intelligence.domain.interfaces.importers import ImporterPlugin
from profile_intelligence.domain.value_objects.documents import (
    ParsedDocument,
    RawDocument,
)
from profile_intelligence.domain.value_objects.importing import ImportResult
from profile_intelligence.infrastructure.database.repository import ProfileRepository
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.infrastructure.scoring.completeness import CompletenessScorer

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ImportSummary:
    """High-level outcome of a persisted import run."""

    path: str
    plugin: str
    records_read: int
    created: int
    updated: int
    skipped: int
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def success(self) -> bool:
        """True when at least one profile was created or updated."""
        return (self.created + self.updated) > 0 and not (
            self.created == 0 and self.updated == 0 and self.errors
        )

    @property
    def written(self) -> int:
        """Total profiles written (created + updated)."""
        return self.created + self.updated


class ImportService:
    """Facade for the File → … → SQLite import pipeline."""

    def __init__(
        self,
        registry: ImporterRegistry,
        repository: ProfileRepository,
        extractor: ProfileExtractor | None = None,
        scorer: CompletenessScorer | None = None,
        pipeline: ImportPipeline | None = None,
    ) -> None:
        self._pipeline = pipeline or ImportPipeline(
            registry,
            repository,
            extractor=extractor,
            scorer=scorer,
        )

    @property
    def pipeline(self) -> ImportPipeline:
        """Underlying staged pipeline."""
        return self._pipeline

    def import_path(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
    ) -> ImportSummary:
        """Run File → RawDocument → … → SQLite for a single path."""
        result = self._pipeline.process(
            path,
            source=source,
            plugin_name=plugin_name,
        )
        summary = ImportSummary(
            path=result.path,
            plugin=result.plugin,
            records_read=result.records_read,
            created=result.created,
            updated=result.updated,
            skipped=result.skipped,
            errors=result.errors,
        )
        logger.info(
            "Import complete: created=%d updated=%d skipped=%d errors=%d",
            summary.created,
            summary.updated,
            summary.skipped,
            len(summary.errors),
        )
        return summary

    def resolve_importer(
        self,
        path: PathLike,
        *,
        plugin_name: str | None = None,
    ) -> ImporterPlugin:
        """Resolve the importer plugin for *path*."""
        document = RawDocument.from_path(path, plugin_name=plugin_name)
        return self._pipeline.parser.resolve_plugin(document)

    def run_importer(
        self,
        plugin: ImporterPlugin,
        path: PathLike,
        **options: object,
    ) -> ImportResult:
        """Parser stage helper: File/RawDocument → ImportResult."""
        document = RawDocument.from_path(path)
        parsed = self._pipeline.parser.parse(
            document, plugin=plugin, **options
        )
        return ImportResult.from_records(
            parsed.records,
            skipped=parsed.records_skipped,
            errors=parsed.errors,
            metadata=dict(parsed.metadata),
        )

    def write_to_database(
        self,
        parse_result: ImportResult,
        *,
        path: PathLike,
        plugin_name: str,
        source: str,
    ) -> ImportSummary:
        """Normalizer → Validator → Profile Entity → Repository → SQLite."""
        document = RawDocument.reference(
            path,
            source=source,
            plugin_name=plugin_name,
        )
        parsed = ParsedDocument(
            document=document,
            plugin_name=plugin_name,
            records=tuple(dict(record) for record in parse_result.records),
            records_read=parse_result.records_read,
            records_skipped=parse_result.records_skipped,
            errors=tuple(parse_result.errors),
            metadata=dict(parse_result.metadata),
        )
        result = self._pipeline.persist_parsed(parsed, source=source)
        return ImportSummary(
            path=result.path,
            plugin=result.plugin,
            records_read=result.records_read,
            created=result.created,
            updated=result.updated,
            skipped=result.skipped,
            errors=result.errors,
        )
