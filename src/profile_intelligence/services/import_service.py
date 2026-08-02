"""Orchestrate file import → extract → score → persist."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.database.repository import ProfileRepository
from profile_intelligence.extractors.profile import ProfileExtractor
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


class ImportService:
    """End-to-end import pipeline for Milestone 1."""

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
        """Import a file, upserting normalized profiles into SQLite."""
        resolved = Path(path).expanduser().resolve()
        if plugin_name:
            plugin = self._registry.get(plugin_name)
        else:
            found = self._registry.find_handler(resolved)
            if found is None:
                raise ImporterError(
                    f"No importer plugin can handle file: {resolved}"
                )
            plugin = found

        logger.info("Importing %s with plugin '%s'", resolved, plugin.name)
        parse_result = plugin.import_file(resolved)
        if not parse_result.success:
            message = "; ".join(parse_result.errors) or "Import failed"
            raise ImporterError(message)

        source_name = source or plugin.name
        drafts, extract_errors = self._extractor.extract_many(
            list(parse_result.records),
            source_override=source_name,
        )

        created = 0
        updated = 0
        persist_errors: list[str] = []
        for draft in drafts:
            draft.score = self._scorer.score(draft)
            try:
                _, was_created = self._repository.upsert_draft(draft)
            except Exception as exc:  # noqa: BLE001
                persist_errors.append(str(exc))
                continue
            if was_created:
                created += 1
            else:
                updated += 1

        errors = tuple(extract_errors + persist_errors + list(parse_result.errors))
        summary = ImportSummary(
            path=str(resolved),
            plugin=plugin.name,
            records_read=parse_result.records_read,
            created=created,
            updated=updated,
            skipped=parse_result.records_skipped + len(extract_errors),
            errors=errors,
        )
        logger.info(
            "Import complete: created=%d updated=%d skipped=%d errors=%d",
            summary.created,
            summary.updated,
            summary.skipped,
            len(summary.errors),
        )
        return summary
