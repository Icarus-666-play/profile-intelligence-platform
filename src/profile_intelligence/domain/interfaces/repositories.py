"""Repository ports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, TypeVar, runtime_checkable

from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.value_objects.profile_children import (
    Photo,
    Rate,
    Review,
    Service,
)

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


class ProfileEntity(Protocol):
    """Structural type for a persisted profile record."""

    id: int | None
    external_id: str | None
    display_name: str
    email: str | None
    phone: str | None
    title: str | None
    organization: str | None
    location: str | None
    tags: str | None
    source: str | None
    notes: str | None
    raw_json: str | None
    score: int | None
    created_at: datetime | None
    updated_at: datetime | None


@runtime_checkable
class IProfileRepository(Protocol):
    """Port for Profile aggregate persistence.

    Implemented by infrastructure ``SQLiteRepository``.
    """

    def get_by_id(self, entity_id: int) -> ProfileEntity | None:
        """Fetch a profile by id."""

    def list_all(
        self, *, limit: int = 100, offset: int = 0
    ) -> Sequence[ProfileEntity]:
        """List profiles."""

    def count(self) -> int:
        """Return total profile count."""

    def find_existing(self, draft: ProfileDraft) -> ProfileEntity | None:
        """Return an existing profile matching *draft*, if any."""

    def upsert_draft(self, draft: ProfileDraft) -> tuple[ProfileEntity, bool]:
        """Insert or update from a domain draft."""

    def update_scores(self, scores: dict[int, int]) -> int:
        """Bulk-assign scores by profile id."""

    def delete(self, entity_id: int) -> bool:
        """Delete a profile (and cascaded children) by id."""


@runtime_checkable
class IRateRepository(Protocol):
    """Port for profile Rate child persistence."""

    def list_for_profile(self, profile_id: int) -> Sequence[Rate]:
        """Return rates owned by *profile_id*."""

    def replace_for_profile(
        self,
        profile_id: int,
        rates: Sequence[Rate],
    ) -> None:
        """Replace all rates for *profile_id*."""

    def delete_for_profile(self, profile_id: int) -> int:
        """Delete all rates for *profile_id*. Returns rows removed."""


@runtime_checkable
class IServiceRepository(Protocol):
    """Port for profile Service child persistence."""

    def list_for_profile(self, profile_id: int) -> Sequence[Service]:
        """Return services owned by *profile_id*."""

    def replace_for_profile(
        self,
        profile_id: int,
        services: Sequence[Service],
    ) -> None:
        """Replace all services for *profile_id*."""

    def delete_for_profile(self, profile_id: int) -> int:
        """Delete all services for *profile_id*. Returns rows removed."""


@runtime_checkable
class IReviewRepository(Protocol):
    """Port for profile Review child persistence."""

    def list_for_profile(self, profile_id: int) -> Sequence[Review]:
        """Return reviews owned by *profile_id*."""

    def replace_for_profile(
        self,
        profile_id: int,
        reviews: Sequence[Review],
    ) -> None:
        """Replace all reviews for *profile_id*."""

    def delete_for_profile(self, profile_id: int) -> int:
        """Delete all reviews for *profile_id*. Returns rows removed."""


@runtime_checkable
class IPhotoRepository(Protocol):
    """Port for profile Photo child persistence."""

    def list_for_profile(self, profile_id: int) -> Sequence[Photo]:
        """Return photos owned by *profile_id*."""

    def replace_for_profile(
        self,
        profile_id: int,
        photos: Sequence[Photo],
    ) -> None:
        """Replace all photos for *profile_id*."""

    def delete_for_profile(self, profile_id: int) -> int:
        """Delete all photos for *profile_id*. Returns rows removed."""


# Backward-compatible alias.
ProfileRepositoryPort = IProfileRepository
