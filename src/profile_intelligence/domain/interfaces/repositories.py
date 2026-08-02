"""Repository ports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Protocol, TypeVar

from profile_intelligence.domain.entities.profile import ProfileDraft

T = TypeVar("T")


class Repository[T](ABC):
    """Abstract repository port."""

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


class ProfileRepositoryPort(Protocol):
    """Port for profile persistence used by application use cases."""

    def get_by_id(self, entity_id: int) -> object | None:
        """Fetch a profile by id."""

    def list_all(self, *, limit: int = 100, offset: int = 0) -> Sequence[object]:
        """List profiles."""

    def count(self) -> int:
        """Return total profile count."""

    def upsert_draft(self, draft: ProfileDraft) -> tuple[object, bool]:
        """Insert or update from a domain draft."""

    def update_scores(self, scores: dict[int, int]) -> int:
        """Bulk-assign scores by profile id."""
