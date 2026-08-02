"""End-to-end import pipeline.

```
File
 ↓
RawDocument
 ↓
Parser
 ↓
Normalizer
 ↓
Validator
 ↓
Profile Entity
 ↓
Repository
 ↓
SQLite
```
"""

from __future__ import annotations

from dataclasses import dataclass, field

from profile_intelligence.core.exceptions import RepositoryError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.database.models import Profile
from profile_intelligence.database.repository import ProfileRepository
from profile_intelligence.extractors.profile import ProfileExtractor
from profile_intelligence.importers.base import ImporterPlugin, ImportResult
from profile_intelligence.importers.registry import ImporterRegistry
from profile_intelligence.pipeline.documents import ParsedDocument, RawDocument
from profile_intelligence.pipeline.normalizer import ProfileNormalizer
from profile_intelligence.pipeline.parser import DocumentParser
from profile_intelligence.pipeline.validator import ProfileValidator
from profile_intelligence.scoring.completeness import CompletenessScorer

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

    @property
    def success(self) -> bool:
        """True when at least one profile entity was written."""
        return (self.created + self.updated) > 0 and not (
            self.created == 0 and self.updated == 0 and self.errors
        )

    @property
    def written(self) -> int:
        """Total profile entities written (created + updated)."""
        return self.created + self.updated


class ImportPipeline:
    """Orchestrates File → … → SQLite through explicit pipeline stages."""

    def __init__(
        self,
        registry: ImporterRegistry,
        repository: ProfileRepository,
        *,
        parser: DocumentParser | None = None,
        normalizer: ProfileNormalizer | None = None,
        validator: ProfileValidator | None = None,
        extractor: ProfileExtractor | None = None,
        scorer: CompletenessScorer | None = None,
    ) -> None:
        self._registry = registry
        self._repository = repository
        self.parser = parser or DocumentParser(registry)
        self.normalizer = normalizer or ProfileNormalizer(extractor)
        self.validator = validator or ProfileValidator()
        self._scorer = scorer or CompletenessScorer()

    def process(
        self,
        path: PathLike,
        *,
        source: str | None = None,
        plugin_name: str | None = None,
        plugin: ImporterPlugin | None = None,
    ) -> PipelineResult:
        """Run the full pipeline for a single file."""
        # File → RawDocument
        document = RawDocument.from_path(
            path,
            source=source,
            plugin_name=plugin_name,
        )
        logger.info("Pipeline start: %s", document.path)

        # RawDocument → Parser
        parsed = self.parser.parse(document, plugin=plugin)
        source_name = source or parsed.plugin_name

        # Parser → Normalizer
        drafts, normalize_errors = self.normalizer.normalize_many(
            parsed.records,
            source_override=source_name,
        )

        # Normalizer → Validator
        validated, validation_errors = self.validator.validate_many(drafts)

        # Validator → Profile Entity → Repository → SQLite
        created = 0
        updated = 0
        persist_errors: list[str] = []
        entities: list[Profile] = []
        for draft in validated:
            draft.score = self._scorer.score(draft)
            try:
                entity, was_created = self._repository.upsert_draft(draft)
            except RepositoryError as exc:
                persist_errors.append(str(exc))
                logger.exception(
                    "Repository stage failed for draft %r",
                    draft.display_name,
                )
                continue
            entities.append(entity)
            if was_created:
                created += 1
            else:
                updated += 1

        errors = tuple(
            list(parsed.errors)
            + normalize_errors
            + validation_errors
            + persist_errors
        )
        result = PipelineResult(
            path=str(parsed.path),
            plugin=parsed.plugin_name,
            records_read=parsed.records_read,
            created=created,
            updated=updated,
            skipped=parsed.records_skipped
            + len(normalize_errors)
            + len(validation_errors),
            errors=errors,
            entities=tuple(entities),
        )
        logger.info(
            "Pipeline complete: created=%d updated=%d skipped=%d errors=%d",
            result.created,
            result.updated,
            result.skipped,
            len(result.errors),
        )
        return result

    # --- Stage helpers (usable independently) ---

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
        """Run Normalizer → Validator → Repository → SQLite for *parsed*."""
        source_name = source or parsed.document.source or parsed.plugin_name
        drafts, normalize_errors = self.normalizer.normalize_many(
            parsed.records,
            source_override=source_name,
        )
        validated, validation_errors = self.validator.validate_many(drafts)

        created = 0
        updated = 0
        persist_errors: list[str] = []
        entities: list[Profile] = []
        for draft in validated:
            draft.score = self._scorer.score(draft)
            try:
                entity, was_created = self._repository.upsert_draft(draft)
            except RepositoryError as exc:
                persist_errors.append(str(exc))
                continue
            entities.append(entity)
            if was_created:
                created += 1
            else:
                updated += 1

        return PipelineResult(
            path=str(parsed.path),
            plugin=parsed.plugin_name,
            records_read=parsed.records_read,
            created=created,
            updated=updated,
            skipped=parsed.records_skipped
            + len(normalize_errors)
            + len(validation_errors),
            errors=tuple(
                list(parsed.errors)
                + normalize_errors
                + validation_errors
                + persist_errors
            ),
            entities=tuple(entities),
        )
