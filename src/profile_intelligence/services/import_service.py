"""Importer → Database pipeline.

```
ProfileImporter.import_file()
        ↓  raw row records
ProfileExtractor + CompletenessScorer
        ↓  ProfileDraft
ProfileRepository.upsert_draft()
        ↓
    SQLite Database
```
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.database.repository import ProfileRepository
from profile_intelligence.extractors.profile import ProfileExtractor
from profile_intelligence.importers.base import ImporterPlugin, ImportResult
from profile_intelligence.importers.registry import ImporterRegistry
from profile_intelligence.scoring.completeness import CompletenessScorer

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
    """Orchestrates the Importer → Database pipeline.

    1. Resolve a ``ProfileImporter`` / ``ImporterPlugin``
    2. Parse the file into raw records
    3. Extract / score profile drafts
    4. Upsert into SQLite via ``ProfileRepository``
    """

    def __init__(
        self,
        registry: ImporterRegistry,
        repository: ProfileRepository,
        extractor: ProfileExtractor | None = None,
        scorer: CompletenessScorer | None = None,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self._extractor = extractor or ProfileExtractor()
        self._scorer = scorer or CompletenessScorer()

    def import_path(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
    ) -> ImportSummary:
        """Run Importer → Database for a single file path."""
        resolved = Path(path).expanduser().resolve()
        plugin = self.resolve_importer(resolved, plugin_name=plugin_name)
        parse_result = self.run_importer(plugin, resolved)
        return self.write_to_database(
            parse_result,
            path=resolved,
            plugin_name=plugin.name,
            source=source or plugin.name,
        )

    def resolve_importer(
        self,
        path: PathLike,
        *,
        plugin_name: str | None = None,
    ) -> ImporterPlugin:
        """Resolve the importer plugin for *path* (or an explicit plugin name)."""
        if plugin_name:
            return self._registry.get(plugin_name)
        found = self._registry.find_handler(path)
        if found is None:
            raise ImporterError(f"No importer plugin can handle file: {path}")
        return found

    def run_importer(
        self,
        plugin: ImporterPlugin,
        path: PathLike,
        **options: object,
    ) -> ImportResult:
        """Importer stage: parse *path* into an :class:`ImportResult`."""
        resolved = Path(path).expanduser().resolve()
        logger.info("Importer stage: %s via '%s'", resolved, plugin.name)
        parse_result = plugin.import_file(resolved, **options)
        if not parse_result.success:
            message = "; ".join(parse_result.errors) or "Import failed"
            raise ImporterError(message)
        logger.debug(
            "Importer stage complete: records_read=%d skipped=%d",
            parse_result.records_read,
            parse_result.records_skipped,
        )
        return parse_result

    def write_to_database(
        self,
        parse_result: ImportResult,
        *,
        path: PathLike,
        plugin_name: str,
        source: str,
    ) -> ImportSummary:
        """Database stage: extract, score, and upsert parsed records."""
        resolved = Path(path).expanduser().resolve()
        logger.info(
            "Database stage: persisting %d record(s) from '%s' (source=%s)",
            len(parse_result.records),
            plugin_name,
            source,
        )

        drafts, extract_errors = self._extractor.extract_many(
            list(parse_result.records),
            source_override=source,
        )

        created = 0
        updated = 0
        persist_errors: list[str] = []
        for draft in drafts:
            draft.score = self._scorer.score(draft)
            try:
                _, was_created = self._repository.upsert_draft(draft)
            except Exception as exc:
                persist_errors.append(str(exc))
                logger.exception(
                    "Database stage failed for draft %r",
                    draft.display_name,
                )
                continue
            if was_created:
                created += 1
            else:
                updated += 1

        errors = tuple(extract_errors + persist_errors + list(parse_result.errors))
        summary = ImportSummary(
            path=str(resolved),
            plugin=plugin_name,
            records_read=parse_result.records_read,
            created=created,
            updated=updated,
            skipped=parse_result.records_skipped + len(extract_errors),
            errors=errors,
        )
        logger.info(
            "Importer → Database complete: created=%d updated=%d skipped=%d errors=%d",
            summary.created,
            summary.updated,
            summary.skipped,
            len(summary.errors),
        )
        return summary
