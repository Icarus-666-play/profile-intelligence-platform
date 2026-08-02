"""Repository stage for the import pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from profile_intelligence.core.exceptions import RepositoryError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import (
    IProfileRepository,
    ProfileEntity,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RepositoryStageResult:
    """Outcome of persisting scored drafts."""

    entities: tuple[ProfileEntity, ...] = field(default_factory=tuple)
    created: int = 0
    updated: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)


class RepositoryStage:
    """Persist scored profile drafts through :class:`IProfileRepository`."""

    def __init__(self, repository: IProfileRepository) -> None:
        self._repository = repository

    def persist_many(
        self,
        drafts: Sequence[ProfileDraft],
    ) -> RepositoryStageResult:
        """Upsert drafts and return created/updated counts."""
        created = 0
        updated = 0
        errors: list[str] = []
        entities: list[ProfileEntity] = []

        for draft in drafts:
            try:
                entity, was_created = self._repository.upsert_draft(draft)
            except RepositoryError as exc:
                errors.append(str(exc))
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

        logger.info(
            "Repository stage: created=%d updated=%d errors=%d",
            created,
            updated,
            len(errors),
        )
        return RepositoryStageResult(
            entities=tuple(entities),
            created=created,
            updated=updated,
            errors=tuple(errors),
        )
