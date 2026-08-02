"""Redis cache backend (future).

```
cache/
  SQLite
  Memory
  File
  Redis (future)
```
"""

from __future__ import annotations

from profile_intelligence.core.exceptions import CacheError
from profile_intelligence.domain.interfaces.cache import ICache


class RedisCache(ICache):
    """Placeholder Redis adapter — not implemented yet."""

    def __init__(
        self,
        url: str | None = None,
        *,
        default_ttl_seconds: float | None = None,
    ) -> None:
        self._url = url
        self._default_ttl = default_ttl_seconds
        raise CacheError(
            "Redis cache backend is not implemented yet. "
            "Use backend: memory | file | sqlite, or wait for the Redis milestone."
        )

    @property
    def backend(self) -> str:
        return "redis"

    def get(self, key: str) -> object | None:
        raise CacheError("Redis cache backend is not implemented yet")

    def set(
        self,
        key: str,
        value: object,
        *,
        ttl_seconds: float | None = None,
    ) -> None:
        raise CacheError("Redis cache backend is not implemented yet")

    def delete(self, key: str) -> bool:
        raise CacheError("Redis cache backend is not implemented yet")

    def clear(self) -> None:
        raise CacheError("Redis cache backend is not implemented yet")

    def has(self, key: str) -> bool:
        raise CacheError("Redis cache backend is not implemented yet")
