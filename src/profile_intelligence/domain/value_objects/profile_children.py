"""Child value objects owned by a Profile aggregate.

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

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Rate:
    """Pricing entry for a profile."""

    duration: str
    price: str
    currency: str = "EUR"
    incall: bool = False
    outcall: bool = False

    def to_mapping(self) -> dict[str, Any]:
        """Serialize for JSON / ORM mapping."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: object) -> Rate | None:
        """Build from a loose mapping; return None when invalid."""
        if not isinstance(raw, dict):
            return None
        duration = _text(raw.get("duration"))
        price = _text(raw.get("price"))
        if not duration or not price:
            return None
        return cls(
            duration=duration,
            price=price,
            currency=_text(raw.get("currency")) or "EUR",
            incall=_truthy(raw.get("incall")),
            outcall=_truthy(raw.get("outcall")),
        )


@dataclass(frozen=True, slots=True)
class Service:
    """Offered service for a profile."""

    name: str
    available: bool = True

    def to_mapping(self) -> dict[str, Any]:
        """Serialize for JSON / ORM mapping."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: object) -> Service | None:
        """Build from a loose mapping; return None when invalid."""
        if isinstance(raw, str):
            name = raw.strip()
            return cls(name=name) if name else None
        if not isinstance(raw, dict):
            return None
        parsed_name = _text(raw.get("name") or raw.get("service"))
        if not parsed_name:
            return None
        available = raw.get("available", True)
        return cls(
            name=parsed_name,
            available=_truthy(available, default=True),
        )


@dataclass(frozen=True, slots=True)
class Review:
    """Customer or directory review for a profile."""

    text: str | None = None
    author: str | None = None
    rating: str | None = None
    reviewed_at: str | None = None
    source_url: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Serialize for JSON / ORM mapping."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: object) -> Review | None:
        """Build from a loose mapping; return None when empty."""
        if not isinstance(raw, dict):
            return None
        review = cls(
            text=_text(raw.get("text") or raw.get("body") or raw.get("comment")),
            author=_text(raw.get("author") or raw.get("reviewer")),
            rating=_text(raw.get("rating") or raw.get("score")),
            reviewed_at=_text(raw.get("reviewed_at") or raw.get("date")),
            source_url=_text(raw.get("source_url") or raw.get("url")),
        )
        if not any(
            (review.text, review.author, review.rating, review.source_url)
        ):
            return None
        return review


@dataclass(frozen=True, slots=True)
class Photo:
    """Gallery / main photo metadata for a profile."""

    original_url: str
    sha256: str | None = None
    role: str = "gallery"
    content_type: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Serialize for JSON / ORM mapping."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: object) -> Photo | None:
        """Build from a loose mapping; return None when invalid."""
        if isinstance(raw, str):
            stripped = raw.strip()
            return cls(original_url=stripped) if stripped else None
        if not isinstance(raw, dict):
            return None
        parsed_url: str | None = _text(
            raw.get("original_url") or raw.get("url") or raw.get("src")
        )
        if parsed_url is None:
            return None
        role = _text(raw.get("role")) or "gallery"
        return cls(
            original_url=parsed_url,
            sha256=_text(raw.get("sha256") or raw.get("hash")),
            role=role,
            content_type=_text(raw.get("content_type") or raw.get("mime_type")),
        )


@dataclass(frozen=True, slots=True)
class Availability:
    """Availability window for a profile."""

    day_of_week: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    status: str | None = None
    notes: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Serialize for JSON / ORM mapping."""
        return asdict(self)

    @classmethod
    def from_mapping(cls, raw: object) -> Availability | None:
        """Build from a loose mapping; return None when empty."""
        if not isinstance(raw, dict):
            return None
        item = cls(
            day_of_week=_text(
                raw.get("day_of_week") or raw.get("day") or raw.get("weekday")
            ),
            start_time=_text(raw.get("start_time") or raw.get("from")),
            end_time=_text(raw.get("end_time") or raw.get("to")),
            status=_text(raw.get("status") or raw.get("availability")),
            notes=_text(raw.get("notes")),
        )
        if not any(
            (
                item.day_of_week,
                item.start_time,
                item.end_time,
                item.status,
                item.notes,
            )
        ):
            return None
        return item


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _truthy(value: object | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}
