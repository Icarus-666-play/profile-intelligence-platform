"""Lightweight dependency injection container.

Services are registered as factories (callables) or instances and resolved
lazily. This keeps wiring explicit without requiring a heavy DI framework.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, MutableMapping
from typing import Any, TypeVar

from profile_intelligence.core.exceptions import PipError
from profile_intelligence.core.logging import get_logger

T = TypeVar("T")

logger = get_logger(__name__)


class ContainerError(PipError):
    """Raised when the DI container cannot resolve or register a service."""


class Container:
    """Simple typed service container with singleton resolution."""

    def __init__(self) -> None:
        self._factories: MutableMapping[type[Any], Callable[[], Any]] = {}
        self._singletons: MutableMapping[type[Any], Any] = {}
        self._aliases: MutableMapping[str, type[Any]] = {}

    def register(
        self,
        service_type: type[object],
        factory: Callable[[], object],
        *,
        name: str | None = None,
    ) -> None:
        """Register a factory that produces ``service_type`` instances.

        ``service_type`` may be a concrete class or an abstract port (ABC).
        """
        if service_type in self._factories or service_type in self._singletons:
            raise ContainerError(
                f"Service already registered: {service_type.__name__}"
            )
        self._factories[service_type] = factory
        if name is not None:
            self._aliases[name] = service_type
        logger.debug("Registered factory for %s", service_type.__name__)

    def register_instance(
        self,
        service_type: type[object],
        instance: object,
        *,
        name: str | None = None,
    ) -> None:
        """Register a pre-built singleton instance."""
        if service_type in self._factories or service_type in self._singletons:
            raise ContainerError(
                f"Service already registered: {service_type.__name__}"
            )
        self._singletons[service_type] = instance
        if name is not None:
            self._aliases[name] = service_type
        logger.debug("Registered instance for %s", service_type.__name__)

    def resolve(self, service_type: type[object]) -> Any:  # noqa: ANN401
        """Resolve a service by type, creating a singleton on first use.

        Returns ``Any`` so abstract ports (Protocols / ABCs) can be resolved
        without mypy ``type-abstract`` errors at call sites.
        """
        if service_type in self._singletons:
            return self._singletons[service_type]
        if service_type not in self._factories:
            raise ContainerError(
                f"No service registered for type: {service_type.__name__}"
            )
        instance = self._factories[service_type]()
        self._singletons[service_type] = instance
        return instance

    def resolve_by_name(self, name: str) -> object:
        """Resolve a service by optional registration name."""
        if name not in self._aliases:
            raise ContainerError(f"No service registered with name: {name}")
        return self.resolve(self._aliases[name])

    def has(self, service_type: type[Any]) -> bool:
        """Return whether a service type is registered."""
        return service_type in self._factories or service_type in self._singletons

    def clear(self) -> None:
        """Remove all registrations (primarily for tests)."""
        self._factories.clear()
        self._singletons.clear()
        self._aliases.clear()

    def registered_types(self) -> Iterator[type[Any]]:
        """Iterate registered service types."""
        seen: set[type[Any]] = set()
        for service_type in (*self._singletons.keys(), *self._factories.keys()):
            if service_type not in seen:
                seen.add(service_type)
                yield service_type
