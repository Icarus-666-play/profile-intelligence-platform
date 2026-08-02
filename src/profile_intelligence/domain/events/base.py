"""Base domain event type."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Immutable domain event base."""

    occurred_at: datetime = field(default_factory=_utc_now)
    event_id: str = field(default_factory=lambda: uuid4().hex)

    @property
    def name(self) -> str:
        """Event type name (class name)."""
        return type(self).__name__
