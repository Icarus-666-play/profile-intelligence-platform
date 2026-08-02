"""Ordered import processing chain.

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

from collections.abc import Sequence
from dataclasses import dataclass, field

from profile_intelligence.application.pipeline.duplicate_detector import (
    DuplicateDetector,
    DuplicateMatch,
)
from profile_intelligence.application.pipeline.normalizer import ProfileNormalizer
from profile_intelligence.application.pipeline.parser import DocumentParser
from profile_intelligence.application.pipeline.repository_stage import (
    RepositoryStage,
    RepositoryStageResult,
)
from profile_intelligence.application.pipeline.scorer import ProfileScorer
from profile_intelligence.application.pipeline.validator import ProfileValidator
from profile_intelligence.core.config import (
    DEFAULT_PIPELINE_STAGES as DEFAULT_PIPELINE_STAGES,
)
from profile_intelligence.core.exceptions import ConfigurationError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.entities.profile import ProfileDraft, ProfileExtractor
from profile_intelligence.domain.interfaces.importers import ImporterPlugin
from profile_intelligence.domain.interfaces.repositories import (
    IProfileRepository,
    ProfileEntity,
)
from profile_intelligence.domain.value_objects.documents import (
    ParsedDocument,
    RawDocument,
)
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.infrastructure.scoring.completeness import CompletenessScorer

logger = get_logger(__name__)

_REQUIRES_REPOSITORY = frozenset({"duplicate_detector", "repository"})


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    """Output of the configured processing chain."""

    parsed: ParsedDocument
    normalized: tuple[ProfileDraft, ...]
    validated: tuple[ProfileDraft, ...]
    unique: tuple[ProfileDraft, ...]
    scored: tuple[ProfileDraft, ...]
    entities: tuple[ProfileEntity, ...] = ()
    created: int = 0
    updated: int = 0
    normalize_errors: tuple[str, ...] = field(default_factory=tuple)
    validation_errors: tuple[str, ...] = field(default_factory=tuple)
    duplicates: tuple[DuplicateMatch, ...] = field(default_factory=tuple)
    update_matches: tuple[DuplicateMatch, ...] = field(default_factory=tuple)
    repository_errors: tuple[str, ...] = field(default_factory=tuple)
    stages_run: tuple[str, ...] = field(default_factory=tuple)

    @property
    def source(self) -> str:
        """Effective source label for processed drafts."""
        return self.parsed.document.source or self.parsed.plugin_name

    @property
    def errors(self) -> tuple[str, ...]:
        """All stage errors."""
        duplicate_msgs = tuple(
            f"duplicate: {item.reason}" for item in self.duplicates
        )
        return tuple(
            list(self.parsed.errors)
            + list(self.normalize_errors)
            + list(self.validation_errors)
            + list(duplicate_msgs)
            + list(self.repository_errors)
        )

    @property
    def skipped(self) -> int:
        """Rows skipped across parse / normalize / validate / duplicates."""
        return (
            self.parsed.records_skipped
            + len(self.normalize_errors)
            + len(self.validation_errors)
            + len(self.duplicates)
        )


class ProcessingChain:
    """Runs the configured import stages in order."""

    def __init__(
        self,
        registry: ImporterRegistry,
        repository: IProfileRepository | None = None,
        *,
        stages: Sequence[str] | None = None,
        parser: DocumentParser | None = None,
        normalizer: ProfileNormalizer | None = None,
        validator: ProfileValidator | None = None,
        duplicate_detector: DuplicateDetector | None = None,
        scorer: ProfileScorer | CompletenessScorer | None = None,
        repository_stage: RepositoryStage | None = None,
        extractor: ProfileExtractor | None = None,
    ) -> None:
        self.stages = self._validate_stages(stages or DEFAULT_PIPELINE_STAGES)
        self._repository = repository
        self.parser = parser or DocumentParser(registry)
        self.normalizer = normalizer or ProfileNormalizer(extractor)
        self.validator = validator or ProfileValidator()

        needs_repo = bool(_REQUIRES_REPOSITORY.intersection(self.stages))
        if needs_repo and repository is None and duplicate_detector is None:
            raise ConfigurationError(
                "pipeline stages duplicate_detector/repository require a repository"
            )

        self.duplicate_detector = duplicate_detector or DuplicateDetector(
            repository,
            check_database=repository is not None,
        )
        if isinstance(scorer, ProfileScorer):
            self.scorer = scorer
        else:
            self.scorer = ProfileScorer(scorer)
        self.repository_stage = repository_stage
        if "repository" in self.stages and self.repository_stage is None:
            if repository is None:
                raise ConfigurationError(
                    "pipeline stage 'repository' requires an IProfileRepository"
                )
            self.repository_stage = RepositoryStage(repository)

    def set_repository(self, repository: IProfileRepository) -> None:
        """Attach or replace the repository used by later stages."""
        self._repository = repository
        self.duplicate_detector = DuplicateDetector(repository)
        if self.repository_stage is None:
            self.repository_stage = RepositoryStage(repository)
        else:
            self.repository_stage = RepositoryStage(repository)

    def run(
        self,
        document: RawDocument,
        *,
        source: str | None = None,
        plugin: ImporterPlugin | None = None,
        exclude_stages: Sequence[str] = (),
    ) -> ProcessingResult:
        """Execute the configured stage chain for *document*."""
        stages = tuple(
            stage for stage in self.stages if stage not in set(exclude_stages)
        )
        return self._execute(
            document=document,
            parsed=None,
            source=source,
            plugin=plugin,
            stages=stages,
        )

    def run_from_parsed(
        self,
        parsed: ParsedDocument,
        *,
        source: str | None = None,
        exclude_stages: Sequence[str] = (),
    ) -> ProcessingResult:
        """Run stages after parser, starting from an already-parsed document."""
        stages = tuple(
            stage
            for stage in self.stages
            if stage != "parser" and stage not in set(exclude_stages)
        )
        return self._execute(
            document=parsed.document,
            parsed=parsed,
            source=source,
            plugin=None,
            stages=stages,
        )

    def _execute(
        self,
        *,
        document: RawDocument,
        parsed: ParsedDocument | None,
        source: str | None,
        plugin: ImporterPlugin | None,
        stages: Sequence[str],
    ) -> ProcessingResult:
        normalized: tuple[ProfileDraft, ...] = ()
        validated: tuple[ProfileDraft, ...] = ()
        unique: tuple[ProfileDraft, ...] = ()
        scored: tuple[ProfileDraft, ...] = ()
        normalize_errors: tuple[str, ...] = ()
        validation_errors: tuple[str, ...] = ()
        duplicates: tuple[DuplicateMatch, ...] = ()
        update_matches: tuple[DuplicateMatch, ...] = ()
        repo_result = RepositoryStageResult()
        stages_run: list[str] = []
        # Working set passed between post-parse stages.
        current: tuple[ProfileDraft, ...] = ()

        for stage in stages:
            if stage == "parser":
                parsed = self.parser.parse(document, plugin=plugin)
                stages_run.append(stage)
                logger.info(
                    "Stage parser complete (%d record(s))",
                    len(parsed.records),
                )
            elif stage == "normalizer":
                if parsed is None:
                    raise ConfigurationError(
                        "pipeline stage 'normalizer' requires 'parser' first"
                    )
                source_name = (
                    source or parsed.document.source or parsed.plugin_name
                )
                drafts, errors = self.normalizer.normalize_many(
                    parsed.records,
                    source_override=source_name,
                )
                normalized = tuple(drafts)
                normalize_errors = tuple(errors)
                current = normalized
                stages_run.append(stage)
                logger.info(
                    "Stage normalizer complete (%d draft(s))",
                    len(normalized),
                )
            elif stage == "validator":
                validated_list, errors = self.validator.validate_many(current)
                validated = tuple(validated_list)
                validation_errors = tuple(errors)
                current = validated
                stages_run.append(stage)
                logger.info(
                    "Stage validator complete (%d accepted)",
                    len(validated),
                )
            elif stage == "duplicate_detector":
                detected = self.duplicate_detector.detect(current)
                unique = detected.unique
                duplicates = detected.duplicates
                update_matches = detected.updates
                current = unique
                stages_run.append(stage)
                logger.info(
                    "Stage duplicate_detector complete (unique=%d)",
                    len(unique),
                )
            elif stage == "scorer":
                scored = self.scorer.score_many(current)
                current = scored
                stages_run.append(stage)
                logger.info("Stage scorer complete (%d scored)", len(scored))
            elif stage == "repository":
                if self.repository_stage is None:
                    raise ConfigurationError(
                        "pipeline stage 'repository' is not configured"
                    )
                repo_result = self.repository_stage.persist_many(current)
                stages_run.append(stage)
            else:  # pragma: no cover - validated earlier
                raise ConfigurationError(f"Unknown pipeline stage: {stage}")

        if parsed is None:
            raise ConfigurationError("pipeline must include a 'parser' stage")

        # Fill forward omitted stage outputs for a stable result shape.
        if not unique and validated:
            unique = validated
        if not scored and unique:
            scored = unique

        return ProcessingResult(
            parsed=parsed,
            normalized=normalized,
            validated=validated,
            unique=unique,
            scored=scored,
            entities=repo_result.entities,
            created=repo_result.created,
            updated=repo_result.updated,
            normalize_errors=normalize_errors,
            validation_errors=validation_errors,
            duplicates=duplicates,
            update_matches=update_matches,
            repository_errors=repo_result.errors,
            stages_run=tuple(stages_run),
        )

    @staticmethod
    def _validate_stages(stages: Sequence[str]) -> tuple[str, ...]:
        allowed = set(DEFAULT_PIPELINE_STAGES)
        cleaned = tuple(str(stage).strip() for stage in stages if str(stage).strip())
        if not cleaned:
            raise ConfigurationError("pipeline stages must not be empty")
        unknown = [stage for stage in cleaned if stage not in allowed]
        if unknown:
            raise ConfigurationError(
                "Unknown pipeline stage(s): " + ", ".join(unknown)
            )
        if "parser" not in cleaned:
            raise ConfigurationError("pipeline must include 'parser'")
        if "repository" in cleaned and "scorer" not in cleaned:
            logger.warning(
                "pipeline includes 'repository' without 'scorer'; "
                "profiles will persist unscored"
            )
        return cleaned
