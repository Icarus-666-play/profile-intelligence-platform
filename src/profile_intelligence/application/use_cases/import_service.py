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

import time
from dataclasses import dataclass, field
from pathlib import Path

from profile_intelligence.application.use_cases.import_pipeline import ImportPipeline
from profile_intelligence.application.use_cases.import_stats import (
    ImportStats,
    aggregate_stats,
)
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.entities.profile import ProfileExtractor
from profile_intelligence.domain.interfaces.importers import ImporterPlugin
from profile_intelligence.domain.value_objects.documents import (
    ParsedDocument,
    RawDocument,
)
from profile_intelligence.domain.value_objects.importing import ImportResult
from profile_intelligence.infrastructure.database.repository import SQLiteRepository
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
    stats: ImportStats = field(default_factory=ImportStats)

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

    def render_report(self) -> str:
        """Render the Imported: profiles / services / rates / … block."""
        return self.stats.render()


class ImportService:
    """Facade for the File → … → SQLite import pipeline."""

    def __init__(
        self,
        registry: ImporterRegistry,
        repository: SQLiteRepository,
        extractor: ProfileExtractor | None = None,
        scorer: CompletenessScorer | None = None,
        pipeline: ImportPipeline | None = None,
    ) -> None:
        self._registry = registry
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
        """Run File → RawDocument → … → SQLite for a file or directory."""
        resolved = Path(path)
        if resolved.is_dir():
            return self.import_directory(
                resolved,
                source=source,
                plugin_name=plugin_name,
            )

        result = self._pipeline.process(
            resolved,
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
            stats=result.stats,
        )
        logger.info(
            "Import complete: profiles=%d services=%d rates=%d images=%d "
            "duplicates=%d time=%.1fs",
            summary.stats.profiles,
            summary.stats.services,
            summary.stats.rates,
            summary.stats.images,
            summary.stats.duplicates,
            summary.stats.execution_seconds,
        )
        return summary

    def import_directory(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
        recursive: bool = False,
    ) -> ImportSummary:
        """Import every supported file under *path* and aggregate stats."""
        started = time.perf_counter()
        directory = Path(path).expanduser().resolve()
        if not directory.is_dir():
            raise NotADirectoryError(f"Import path is not a directory: {directory}")

        files = self._discover_files(directory, recursive=recursive)
        created = updated = skipped = records_read = 0
        errors: list[str] = []
        stats_parts: list[ImportStats] = []
        plugin_names: set[str] = set()

        for file_path in files:
            try:
                result = self._pipeline.process(
                    file_path,
                    source=source,
                    plugin_name=plugin_name,
                )
            except Exception as exc:
                errors.append(f"{file_path}: {exc}")
                logger.exception("Directory import failed for %s", file_path)
                continue
            created += result.created
            updated += result.updated
            skipped += result.skipped
            records_read += result.records_read
            errors.extend(result.errors)
            stats_parts.append(result.stats)
            plugin_names.add(result.plugin)

        combined = aggregate_stats(stats_parts)
        # Recompute wall-clock for the whole directory run.
        combined = ImportStats(
            profiles=combined.profiles,
            services=combined.services,
            rates=combined.rates,
            images=combined.images,
            duplicates=combined.duplicates,
            execution_seconds=time.perf_counter() - started,
        )
        plugin = (
            next(iter(plugin_names))
            if len(plugin_names) == 1
            else ("mixed" if plugin_names else "none")
        )
        summary = ImportSummary(
            path=str(directory),
            plugin=plugin,
            records_read=records_read,
            created=created,
            updated=updated,
            skipped=skipped,
            errors=tuple(errors),
            stats=combined,
        )
        logger.info(
            "Directory import complete: files=%d profiles=%d services=%d "
            "rates=%d images=%d duplicates=%d time=%.1fs",
            len(files),
            summary.stats.profiles,
            summary.stats.services,
            summary.stats.rates,
            summary.stats.images,
            summary.stats.duplicates,
            summary.stats.execution_seconds,
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
        """Normalizer → Validator → Profile Entity → SQLiteRepository → SQLite."""
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
            stats=result.stats,
        )

    def _discover_files(
        self,
        directory: Path,
        *,
        recursive: bool,
    ) -> list[Path]:
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        candidates = sorted(
            path
            for path in iterator
            if path.is_file() and not path.name.startswith(".")
        )
        if not self._registry.list_plugins():
            return candidates
        return [
            path
            for path in candidates
            if self._registry.find_handler(path) is not None
        ]
