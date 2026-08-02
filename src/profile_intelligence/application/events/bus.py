"""In-memory domain event bus."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.events.base import DomainEvent
from profile_intelligence.domain.interfaces.events import EventHandler, IEventBus

logger = get_logger(__name__)


class InMemoryEventBus(IEventBus):
    """Synchronous in-process event bus with optional history."""

    def __init__(self, *, record_history: bool = True) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(
            list
        )
        self._history: list[DomainEvent] = []
        self._record_history = record_history

    def subscribe(
        self,
        event_type: type[DomainEvent],
        handler: EventHandler,
    ) -> None:
        self._handlers[event_type].append(handler)
        logger.debug(
            "Subscribed %s to %s",
            getattr(handler, "__name__", repr(handler)),
            event_type.__name__,
        )

    def publish(self, event: DomainEvent) -> None:
        if self._record_history:
            self._history.append(event)
        logger.info("Event published: %s", event.name)
        for event_type, handlers in self._handlers.items():
            if isinstance(event, event_type):
                for handler in handlers:
                    handler(event)

    def publish_many(self, events: Sequence[DomainEvent]) -> None:
        for event in events:
            self.publish(event)

    def history(self) -> Sequence[DomainEvent]:
        return tuple(self._history)

    def clear_history(self) -> None:
        self._history.clear()
