"""Repository pattern implementations for persistence access."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from profile_intelligence.core.exceptions import RepositoryError
from profile_intelligence.database.connection import Database
from profile_intelligence.database.models import Profile
from profile_intelligence.extractors.profile import ProfileDraft


class Repository[T](ABC):
    """Abstract repository interface."""

    def __init__(self, database: Database) -> None:
        self._database = database

    @abstractmethod
    def get_by_id(self, entity_id: int) -> T | None:
        """Fetch an entity by primary key."""

    @abstractmethod
    def list_all(self, *, limit: int = 100, offset: int = 0) -> Sequence[T]:
        """List entities with pagination."""

    @abstractmethod
    def add(self, entity: T) -> T:
        """Persist a new entity and return it with identity assigned."""

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete an entity by id. Returns True if a row was deleted."""


class ProfileRepository(Repository[Profile]):
    """Repository for :class:`Profile` entities."""

    def get_by_id(self, entity_id: int) -> Profile | None:
        try:
            with self._database.session() as session:
                return session.get(Profile, entity_id)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to load profile id={entity_id}",
                cause=exc,
            ) from exc

    def list_all(self, *, limit: int = 100, offset: int = 0) -> Sequence[Profile]:
        if limit < 0 or offset < 0:
            raise RepositoryError("limit and offset must be non-negative")
        try:
            with self._database.session() as session:
                statement = (
                    select(Profile)
                    .order_by(Profile.id)
                    .offset(offset)
                    .limit(limit)
                )
                return list(session.scalars(statement).all())
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError("Failed to list profiles", cause=exc) from exc

    def count(self) -> int:
        """Return total number of profiles."""
        try:
            with self._database.session() as session:
                total = session.scalar(select(func.count()).select_from(Profile))
                return int(total or 0)
        except Exception as exc:
            raise RepositoryError("Failed to count profiles", cause=exc) from exc

    def add(self, entity: Profile) -> Profile:
        try:
            with self._database.session() as session:
                session.add(entity)
                session.flush()
                session.refresh(entity)
                session.expunge(entity)
                return entity
        except Exception as exc:
            raise RepositoryError("Failed to add profile", cause=exc) from exc

    def delete(self, entity_id: int) -> bool:
        try:
            with self._database.session() as session:
                profile = session.get(Profile, entity_id)
                if profile is None:
                    return False
                session.delete(profile)
                return True
        except Exception as exc:
            raise RepositoryError(
                f"Failed to delete profile id={entity_id}",
                cause=exc,
            ) from exc

    def find_by_display_name(
        self,
        display_name: str,
        *,
        session: Session | None = None,
    ) -> Sequence[Profile]:
        """Find profiles matching an exact display name."""
        statement = select(Profile).where(Profile.display_name == display_name)
        try:
            if session is not None:
                return list(session.scalars(statement).all())
            with self._database.session() as owned:
                return list(owned.scalars(statement).all())
        except Exception as exc:
            raise RepositoryError(
                "Failed to find profiles by display name",
                cause=exc,
            ) from exc

    def upsert_draft(self, draft: ProfileDraft) -> tuple[Profile, bool]:
        """Insert or update a profile from a draft.

        Match order: ``external_id``, then ``display_name`` + ``source``.
        Returns ``(profile, created)`` where *created* is True on insert.
        """
        try:
            with self._database.session() as session:
                existing = self._find_existing(session, draft)
                if existing is None:
                    profile = Profile(**_draft_to_columns(draft))
                    session.add(profile)
                    session.flush()
                    session.refresh(profile)
                    session.expunge(profile)
                    return profile, True

                for key, value in _draft_to_columns(draft).items():
                    setattr(existing, key, value)
                session.flush()
                session.refresh(existing)
                session.expunge(existing)
                return existing, False
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError("Failed to upsert profile", cause=exc) from exc

    def update_scores(self, scores: dict[int, int]) -> int:
        """Bulk-assign scores by profile id. Returns number of rows updated."""
        if not scores:
            return 0
        updated = 0
        try:
            with self._database.session() as session:
                for profile_id, score in scores.items():
                    profile = session.get(Profile, profile_id)
                    if profile is None:
                        continue
                    profile.score = score
                    updated += 1
            return updated
        except Exception as exc:
            raise RepositoryError("Failed to update profile scores", cause=exc) from exc

    @staticmethod
    def _find_existing(session: Session, draft: ProfileDraft) -> Profile | None:
        if draft.external_id:
            found = session.scalar(
                select(Profile).where(Profile.external_id == draft.external_id)
            )
            if found is not None:
                return found
        conditions = [Profile.display_name == draft.display_name]
        if draft.source is None:
            conditions.append(Profile.source.is_(None))
        else:
            conditions.append(Profile.source == draft.source)
        return session.scalar(select(Profile).where(*conditions))


def _draft_to_columns(draft: ProfileDraft) -> dict[str, object | None]:
    return {
        "external_id": draft.external_id,
        "display_name": draft.display_name,
        "email": draft.email,
        "phone": draft.phone,
        "title": draft.title,
        "organization": draft.organization,
        "location": draft.location,
        "tags": draft.tags,
        "source": draft.source,
        "notes": draft.notes,
        "raw_json": draft.raw_json,
        "score": draft.score,
    }
