"""Event publisher / handler ports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import TypeVar

from profile_intelligence.domain.events.base import DomainEvent

E = TypeVar("E", bound=DomainEvent)

EventHandler = Callable[[DomainEvent], None]


class IEventPublisher(ABC):
    """Port for publishing domain events."""

    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publish a single domain event to subscribers."""

    @abstractmethod
    def publish_many(self, events: Sequence[DomainEvent]) -> None:
        """Publish events in order."""


class IEventBus(IEventPublisher, ABC):
    """Port for subscribe + publish domain events."""

    @abstractmethod
    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: EventHandler,
    ) -> None:
        """Register *handler* for *event_type* (and subclasses)."""

    @abstractmethod
    def history(self) -> Sequence[DomainEvent]:
        """Return published events in order (testing / audit)."""

    @abstractmethod
    def clear_history(self) -> None:
        """Clear the published-event history."""
