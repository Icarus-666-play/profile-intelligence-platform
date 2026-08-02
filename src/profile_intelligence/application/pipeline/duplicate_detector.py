"""Duplicate detector stage for the import pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.infrastructure.database.repository import SQLiteRepository

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DuplicateMatch:
    """A draft identified as a duplicate."""

    draft: ProfileDraft
    reason: str
    existing_id: int | None = None


@dataclass(frozen=True, slots=True)
class DuplicateFilterResult:
    """Outcome of duplicate detection."""

    unique: tuple[ProfileDraft, ...]
    duplicates: tuple[DuplicateMatch, ...] = field(default_factory=tuple)
    updates: tuple[DuplicateMatch, ...] = field(default_factory=tuple)

    @property
    def skipped(self) -> int:
        """Number of drafts removed as in-batch duplicates."""
        return len(self.duplicates)


class DuplicateDetector:
    """Detect in-batch duplicates and existing database matches.

    In-batch duplicates (same ``external_id``, email, or display_name+source)
    are skipped. Existing database matches are annotated as updates but still
    forwarded to the repository stage for upsert.
    """

    def __init__(
        self,
        repository: SQLiteRepository | None = None,
        *,
        check_database: bool = True,
    ) -> None:
        self._repository = repository
        self._check_database = check_database

    def detect(self, drafts: Sequence[ProfileDraft]) -> DuplicateFilterResult:
        """Filter *drafts* and report duplicates / update candidates."""
        unique: list[ProfileDraft] = []
        duplicates: list[DuplicateMatch] = []
        updates: list[DuplicateMatch] = []
        seen_keys: set[str] = set()

        for draft in drafts:
            key = self._identity_key(draft)
            if key in seen_keys:
                duplicates.append(
                    DuplicateMatch(
                        draft=draft,
                        reason=f"duplicate in batch ({key})",
                    )
                )
                continue
            seen_keys.add(key)

            if self._check_database and self._repository is not None:
                existing = self._repository.find_existing(draft)
                if existing is not None and existing.id is not None:
                    updates.append(
                        DuplicateMatch(
                            draft=draft,
                            reason="matches existing profile",
                            existing_id=existing.id,
                        )
                    )

            unique.append(draft)

        result = DuplicateFilterResult(
            unique=tuple(unique),
            duplicates=tuple(duplicates),
            updates=tuple(updates),
        )
        logger.info(
            "Duplicate detector: unique=%d batch_duplicates=%d db_updates=%d",
            len(result.unique),
            len(result.duplicates),
            len(result.updates),
        )
        return result

    @staticmethod
    def _identity_key(draft: ProfileDraft) -> str:
        if draft.external_id:
            return f"external_id:{draft.external_id.strip().lower()}"
        if draft.email:
            return f"email:{draft.email.strip().lower()}"
        source = (draft.source or "").strip().lower()
        name = draft.display_name.strip().lower()
        return f"name_source:{name}|{source}"
