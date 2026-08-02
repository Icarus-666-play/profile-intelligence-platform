"""ORM models for Profile aggregate children.

```
Profile
 ↓
Rate
 ↓
Service
 ↓
Review
 ↓
Photo
 ↓
Availability
```
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from profile_intelligence.infrastructure.database.models import Base

if TYPE_CHECKING:
    from profile_intelligence.infrastructure.database.models import Profile


class ProfileRate(Base):
    """Persisted rate row owned by a profile."""

    __tablename__ = "profile_rates"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "duration",
            "incall",
            "outcall",
            name="uq_profile_rate",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duration: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    price: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")
    incall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    outcall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    profile: Mapped[Profile] = relationship("Profile", back_populates="rates")


class ProfileService(Base):
    """Persisted service row owned by a profile."""

    __tablename__ = "profile_services"
    __table_args__ = (
        UniqueConstraint("profile_id", "name", name="uq_profile_service"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    profile: Mapped[Profile] = relationship("Profile", back_populates="services")


class ProfileReview(Base):
    """Persisted review row owned by a profile."""

    __tablename__ = "profile_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rating: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    profile: Mapped[Profile] = relationship("Profile", back_populates="reviews")


class ProfilePhoto(Base):
    """Persisted photo metadata owned by a profile."""

    __tablename__ = "profile_photos"
    __table_args__ = (
        UniqueConstraint("profile_id", "original_url", name="uq_profile_photo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="gallery")
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)

    profile: Mapped[Profile] = relationship("Profile", back_populates="photos")


class ProfileAvailability(Base):
    """Persisted availability window owned by a profile."""

    __tablename__ = "profile_availability"
    __table_args__ = (
        UniqueConstraint(
            "profile_id",
            "day_of_week",
            "start_time",
            "end_time",
            name="uq_profile_availability",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day_of_week: Mapped[str | None] = mapped_column(String(16), nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    end_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped[Profile] = relationship(
        "Profile", back_populates="availability"
    )
