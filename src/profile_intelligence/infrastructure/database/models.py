"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from profile_intelligence.infrastructure.database.models_profile_children import (
        ProfileAvailability,
        ProfilePhoto,
        ProfileRate,
        ProfileReview,
        ProfileService,
    )


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class SchemaMigration(Base):
    """Tracks applied database migrations."""

    __tablename__ = "schema_migrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Profile(Base):
    """Core profile aggregate root.

    Child collections follow:

    Profile → Rate → Service → Review → Photo → Availability
    """

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    rates: Mapped[list[ProfileRate]] = relationship(
        "ProfileRate",
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    services: Mapped[list[ProfileService]] = relationship(
        "ProfileService",
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reviews: Mapped[list[ProfileReview]] = relationship(
        "ProfileReview",
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    photos: Mapped[list[ProfilePhoto]] = relationship(
        "ProfilePhoto",
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    availability: Mapped[list[ProfileAvailability]] = relationship(
        "ProfileAvailability",
        back_populates="profile",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"Profile(id={self.id!r}, display_name={self.display_name!r}, "
            f"source={self.source!r}, score={self.score!r})"
        )


class MediaAsset(Base):
    """Stored media file metadata (content-addressed on disk)."""

    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    original_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extension: Mapped[str | None] = mapped_column(String(32), nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"MediaAsset(id={self.id!r}, content_hash={self.content_hash!r}, "
            f"profile_id={self.profile_id!r})"
        )


# Register Profile child mappers for relationship resolution.
from profile_intelligence.infrastructure.database.models_profile_children import (  # noqa: E402
    ProfileAvailability,
    ProfilePhoto,
    ProfileRate,
    ProfileReview,
    ProfileService,
)

__all__ = [
    "Base",
    "MediaAsset",
    "Profile",
    "ProfileAvailability",
    "ProfilePhoto",
    "ProfileRate",
    "ProfileReview",
    "ProfileService",
    "SchemaMigration",
]
