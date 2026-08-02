"""Cache backend factory."""

from __future__ import annotations

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.exceptions import ConfigurationError
from profile_intelligence.domain.interfaces.cache import ICache
from profile_intelligence.infrastructure.cache.file_cache import FileCache
from profile_intelligence.infrastructure.cache.memory import MemoryCache
from profile_intelligence.infrastructure.cache.redis_cache import RedisCache
from profile_intelligence.infrastructure.cache.sqlite_cache import SQLiteCache


def create_cache(config: AppConfig) -> ICache:
    """Build the configured cache backend.

    Supported backends::

        cache/
          SQLite
          Memory
          File
          Redis (future)
    """
    section = config.cache
    backend = section.backend.strip().lower()
    ttl = section.ttl_seconds

    if backend == "memory":
        return MemoryCache(default_ttl_seconds=ttl)
    if backend == "file":
        return FileCache(
            config.cache_dir,
            default_ttl_seconds=ttl,
        )
    if backend in {"sqlite", "sqlite3"}:
        return SQLiteCache(
            config.cache_sqlite_path,
            default_ttl_seconds=ttl,
        )
    if backend == "redis":
        return RedisCache(
            section.redis_url,
            default_ttl_seconds=ttl,
        )
    raise ConfigurationError(
        f"Unsupported cache backend: {backend!r} "
        "(expected memory, file, sqlite, or redis)"
    )
