"""In-process memory cache backend."""

from __future__ import annotations

from dataclasses import dataclass

from profile_intelligence.domain.interfaces.cache import ICache
from profile_intelligence.infrastructure.cache.base import (
    expires_at_from_ttl,
    is_expired,
    resolve_ttl,
)


@dataclass(slots=True)
class _Entry:
    value: object
    expires_at: float | None


class MemoryCache(ICache):
    """Thread-unsafe in-memory cache (sufficient for single-process desktop use)."""

    def __init__(self, *, default_ttl_seconds: float | None = None) -> None:
        self._default_ttl = default_ttl_seconds
        self._store: dict[str, _Entry] = {}

    @property
    def backend(self) -> str:
        return "memory"

    def get(self, key: str) -> object | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if is_expired(entry.expires_at):
            del self._store[key]
            return None
        return entry.value

    def set(
        self,
        key: str,
        value: object,
        *,
        ttl_seconds: float | None = None,
    ) -> None:
        ttl = resolve_ttl(ttl_seconds, default_ttl=self._default_ttl)
        self._store[key] = _Entry(
            value=value,
            expires_at=expires_at_from_ttl(ttl),
        )

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        self._store.clear()

    def has(self, key: str) -> bool:
        return self.get(key) is not None
