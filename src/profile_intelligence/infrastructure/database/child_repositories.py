"""SQLite adapters for Profile child repository ports."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from profile_intelligence.core.exceptions import RepositoryError
from profile_intelligence.domain.value_objects.profile_children import (
    Photo,
    Rate,
    Review,
    Service,
)
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.database.models_profile_children import (
    ProfilePhoto,
    ProfileRate,
    ProfileReview,
    ProfileService,
)


class _ChildRepositoryBase:
    """Shared SQLite session holder for child repositories."""

    def __init__(self, database: Database) -> None:
        self._database = database


class SQLiteRateRepository(_ChildRepositoryBase):
    """SQLite implementation of ``IRateRepository``."""

    def list_for_profile(self, profile_id: int) -> Sequence[Rate]:
        try:
            with self._database.session() as session:
                rows = session.scalars(
                    select(ProfileRate)
                    .where(ProfileRate.profile_id == profile_id)
                    .order_by(ProfileRate.id)
                ).all()
                return tuple(_rate_from_model(row) for row in rows)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to list rates for profile_id={profile_id}",
                cause=exc,
            ) from exc

    def replace_for_profile(
        self,
        profile_id: int,
        rates: Sequence[Rate],
    ) -> None:
        try:
            with self._database.session() as session:
                replace_rates_in_session(session, profile_id, rates)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to replace rates for profile_id={profile_id}",
                cause=exc,
            ) from exc

    def delete_for_profile(self, profile_id: int) -> int:
        try:
            with self._database.session() as session:
                result = session.execute(
                    delete(ProfileRate).where(
                        ProfileRate.profile_id == profile_id
                    )
                )
                return int(getattr(result, "rowcount", 0) or 0)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to delete rates for profile_id={profile_id}",
                cause=exc,
            ) from exc


class SQLiteServiceRepository(_ChildRepositoryBase):
    """SQLite implementation of ``IServiceRepository``."""

    def list_for_profile(self, profile_id: int) -> Sequence[Service]:
        try:
            with self._database.session() as session:
                rows = session.scalars(
                    select(ProfileService)
                    .where(ProfileService.profile_id == profile_id)
                    .order_by(ProfileService.id)
                ).all()
                return tuple(_service_from_model(row) for row in rows)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to list services for profile_id={profile_id}",
                cause=exc,
            ) from exc

    def replace_for_profile(
        self,
        profile_id: int,
        services: Sequence[Service],
    ) -> None:
        try:
            with self._database.session() as session:
                replace_services_in_session(session, profile_id, services)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to replace services for profile_id={profile_id}",
                cause=exc,
            ) from exc

    def delete_for_profile(self, profile_id: int) -> int:
        try:
            with self._database.session() as session:
                result = session.execute(
                    delete(ProfileService).where(
                        ProfileService.profile_id == profile_id
                    )
                )
                return int(getattr(result, "rowcount", 0) or 0)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to delete services for profile_id={profile_id}",
                cause=exc,
            ) from exc


class SQLiteReviewRepository(_ChildRepositoryBase):
    """SQLite implementation of ``IReviewRepository``."""

    def list_for_profile(self, profile_id: int) -> Sequence[Review]:
        try:
            with self._database.session() as session:
                rows = session.scalars(
                    select(ProfileReview)
                    .where(ProfileReview.profile_id == profile_id)
                    .order_by(ProfileReview.id)
                ).all()
                return tuple(_review_from_model(row) for row in rows)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to list reviews for profile_id={profile_id}",
                cause=exc,
            ) from exc

    def replace_for_profile(
        self,
        profile_id: int,
        reviews: Sequence[Review],
    ) -> None:
        try:
            with self._database.session() as session:
                replace_reviews_in_session(session, profile_id, reviews)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to replace reviews for profile_id={profile_id}",
                cause=exc,
            ) from exc

    def delete_for_profile(self, profile_id: int) -> int:
        try:
            with self._database.session() as session:
                result = session.execute(
                    delete(ProfileReview).where(
                        ProfileReview.profile_id == profile_id
                    )
                )
                return int(getattr(result, "rowcount", 0) or 0)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to delete reviews for profile_id={profile_id}",
                cause=exc,
            ) from exc


class SQLitePhotoRepository(_ChildRepositoryBase):
    """SQLite implementation of ``IPhotoRepository``."""

    def list_for_profile(self, profile_id: int) -> Sequence[Photo]:
        try:
            with self._database.session() as session:
                rows = session.scalars(
                    select(ProfilePhoto)
                    .where(ProfilePhoto.profile_id == profile_id)
                    .order_by(ProfilePhoto.id)
                ).all()
                return tuple(_photo_from_model(row) for row in rows)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to list photos for profile_id={profile_id}",
                cause=exc,
            ) from exc

    def replace_for_profile(
        self,
        profile_id: int,
        photos: Sequence[Photo],
    ) -> None:
        try:
            with self._database.session() as session:
                replace_photos_in_session(session, profile_id, photos)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to replace photos for profile_id={profile_id}",
                cause=exc,
            ) from exc

    def delete_for_profile(self, profile_id: int) -> int:
        try:
            with self._database.session() as session:
                result = session.execute(
                    delete(ProfilePhoto).where(
                        ProfilePhoto.profile_id == profile_id
                    )
                )
                return int(getattr(result, "rowcount", 0) or 0)
        except Exception as exc:
            raise RepositoryError(
                f"Failed to delete photos for profile_id={profile_id}",
                cause=exc,
            ) from exc


def replace_rates_in_session(
    session: Session,
    profile_id: int,
    rates: Sequence[Rate],
) -> None:
    """Replace rate rows inside an open session (aggregate upsert)."""
    session.execute(delete(ProfileRate).where(ProfileRate.profile_id == profile_id))
    for rate in rates:
        session.add(
            ProfileRate(
                profile_id=profile_id,
                duration=rate.duration,
                price=rate.price,
                currency=rate.currency,
                incall=rate.incall,
                outcall=rate.outcall,
            )
        )


def replace_services_in_session(
    session: Session,
    profile_id: int,
    services: Sequence[Service],
) -> None:
    """Replace service rows inside an open session (aggregate upsert)."""
    session.execute(
        delete(ProfileService).where(ProfileService.profile_id == profile_id)
    )
    for service in services:
        session.add(
            ProfileService(
                profile_id=profile_id,
                name=service.name,
                available=service.available,
            )
        )


def replace_reviews_in_session(
    session: Session,
    profile_id: int,
    reviews: Sequence[Review],
) -> None:
    """Replace review rows inside an open session (aggregate upsert)."""
    session.execute(
        delete(ProfileReview).where(ProfileReview.profile_id == profile_id)
    )
    for review in reviews:
        session.add(
            ProfileReview(
                profile_id=profile_id,
                text=review.text,
                author=review.author,
                rating=review.rating,
                reviewed_at=review.reviewed_at,
                source_url=review.source_url,
            )
        )


def replace_photos_in_session(
    session: Session,
    profile_id: int,
    photos: Sequence[Photo],
) -> None:
    """Replace photo rows inside an open session (aggregate upsert)."""
    session.execute(
        delete(ProfilePhoto).where(ProfilePhoto.profile_id == profile_id)
    )
    for photo in photos:
        session.add(
            ProfilePhoto(
                profile_id=profile_id,
                original_url=photo.original_url,
                sha256=photo.sha256,
                role=photo.role,
                content_type=photo.content_type,
            )
        )


def _rate_from_model(row: ProfileRate) -> Rate:
    return Rate(
        duration=row.duration,
        price=row.price,
        currency=row.currency,
        incall=row.incall,
        outcall=row.outcall,
    )


def _service_from_model(row: ProfileService) -> Service:
    return Service(name=row.name, available=row.available)


def _review_from_model(row: ProfileReview) -> Review:
    return Review(
        text=row.text,
        author=row.author,
        rating=row.rating,
        reviewed_at=row.reviewed_at,
        source_url=row.source_url,
    )


def _photo_from_model(row: ProfilePhoto) -> Photo:
    return Photo(
        original_url=row.original_url,
        sha256=row.sha256,
        role=row.role,
        content_type=row.content_type,
    )
