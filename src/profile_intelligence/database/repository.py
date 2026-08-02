"""Repository pattern implementations for persistence access."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from profile_intelligence.core.exceptions import RepositoryError
from profile_intelligence.database.connection import Database
from profile_intelligence.database.models import Profile


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
