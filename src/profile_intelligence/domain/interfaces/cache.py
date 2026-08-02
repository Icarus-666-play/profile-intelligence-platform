"""Cache port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T")


class ICache(ABC):
    """Port for key/value caching with optional TTL."""

    @abstractmethod
    def get(self, key: str) -> object | None:
        """Return a cached value, or ``None`` when missing / expired."""

    @abstractmethod
    def set(
        self,
        key: str,
        value: object,
        *,
        ttl_seconds: float | None = None,
    ) -> None:
        """Store *value* under *key*, optionally expiring after *ttl_seconds*."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove *key*. Returns True when a value was deleted."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all entries from this cache."""

    @abstractmethod
    def has(self, key: str) -> bool:
        """Return whether *key* is present and not expired."""

    @property
    @abstractmethod
    def backend(self) -> str:
        """Backend name (``memory``, ``file``, ``sqlite``, ``redis``)."""
