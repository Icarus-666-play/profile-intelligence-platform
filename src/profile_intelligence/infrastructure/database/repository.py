"""Repository pattern implementations for persistence access."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from profile_intelligence.core.exceptions import RepositoryError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import Repository
from profile_intelligence.domain.value_objects.profile_children import (
    Availability,
    Photo,
    Rate,
    Review,
    Service,
)
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.database.models import Profile
from profile_intelligence.infrastructure.database.models_profile_children import (
    ProfileAvailability,
    ProfilePhoto,
    ProfileRate,
    ProfileReview,
    ProfileService,
)

logger = get_logger(__name__)


class DatabaseRepository[T](Repository[T]):
    """SQLAlchemy-backed repository base for SQLite persistence."""

    def __init__(self, database: Database) -> None:
        self._database = database


class SQLiteRepository(DatabaseRepository[Profile]):
    """SQLite repository for the Profile aggregate.

    Persists ``Profile`` and child collections::

        Profile → Rate → Service → Review → Photo → Availability
    """

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

    def find_existing(self, draft: ProfileDraft) -> Profile | None:
        """Return an existing profile matching *draft*, if any.

        Match order: ``external_id``, then ``display_name`` + ``source``.
        """
        try:
            with self._database.session() as session:
                existing = self._find_existing(session, draft)
                if existing is None:
                    return None
                session.expunge(existing)
                return existing
        except Exception as exc:
            raise RepositoryError(
                "Failed to look up existing profile",
                cause=exc,
            ) from exc

    def upsert_draft(self, draft: ProfileDraft) -> tuple[Profile, bool]:
        """Insert or update a profile and replace its child collections.

        Match order: ``external_id``, then ``display_name`` + ``source``.
        Returns ``(profile, created)`` where *created* is True on insert.
        """
        try:
            with self._database.session() as session:
                existing = self._find_existing(session, draft)
                created = existing is None
                if existing is None:
                    profile = Profile(**_draft_to_columns(draft))
                    session.add(profile)
                    session.flush()
                else:
                    profile = existing
                    for key, value in _draft_to_columns(draft).items():
                        setattr(profile, key, value)
                    session.flush()

                self._replace_children(session, profile.id, draft)
                session.flush()
                session.refresh(profile)
                session.expunge(profile)
                if created:
                    logger.debug(
                        "Created profile %r (source=%s)",
                        profile.display_name,
                        profile.source,
                    )
                else:
                    logger.debug(
                        "Updated profile id=%s (%r)",
                        profile.id,
                        profile.display_name,
                    )
                return profile, created
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

    @staticmethod
    def _replace_children(
        session: Session,
        profile_id: int,
        draft: ProfileDraft,
    ) -> None:
        """Delete existing children and insert draft children in one session."""
        session.execute(
            delete(ProfileRate).where(ProfileRate.profile_id == profile_id)
        )
        session.execute(
            delete(ProfileService).where(ProfileService.profile_id == profile_id)
        )
        session.execute(
            delete(ProfileReview).where(ProfileReview.profile_id == profile_id)
        )
        session.execute(
            delete(ProfilePhoto).where(ProfilePhoto.profile_id == profile_id)
        )
        session.execute(
            delete(ProfileAvailability).where(
                ProfileAvailability.profile_id == profile_id
            )
        )

        for rate in draft.rates:
            session.add(_rate_to_model(profile_id, rate))
        for service in draft.services:
            session.add(_service_to_model(profile_id, service))
        for review in draft.reviews:
            session.add(_review_to_model(profile_id, review))
        for photo in draft.photos:
            session.add(_photo_to_model(profile_id, photo))
        for slot in draft.availability:
            session.add(_availability_to_model(profile_id, slot))


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


def _rate_to_model(profile_id: int, rate: Rate) -> ProfileRate:
    return ProfileRate(
        profile_id=profile_id,
        duration=rate.duration,
        price=rate.price,
        currency=rate.currency,
        incall=rate.incall,
        outcall=rate.outcall,
    )


def _service_to_model(profile_id: int, service: Service) -> ProfileService:
    return ProfileService(
        profile_id=profile_id,
        name=service.name,
        available=service.available,
    )


def _review_to_model(profile_id: int, review: Review) -> ProfileReview:
    return ProfileReview(
        profile_id=profile_id,
        text=review.text,
        author=review.author,
        rating=review.rating,
        reviewed_at=review.reviewed_at,
        source_url=review.source_url,
    )


def _photo_to_model(profile_id: int, photo: Photo) -> ProfilePhoto:
    return ProfilePhoto(
        profile_id=profile_id,
        original_url=photo.original_url,
        sha256=photo.sha256,
        role=photo.role,
        content_type=photo.content_type,
    )


def _availability_to_model(
    profile_id: int,
    slot: Availability,
) -> ProfileAvailability:
    return ProfileAvailability(
        profile_id=profile_id,
        day_of_week=slot.day_of_week,
        start_time=slot.start_time,
        end_time=slot.end_time,
        status=slot.status,
        notes=slot.notes,
    )


# Backward-compatible alias.
ProfileRepository = SQLiteRepository
