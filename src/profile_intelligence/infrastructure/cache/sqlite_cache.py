"""SQLite-backed cache backend."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from profile_intelligence.core.exceptions import CacheError
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.interfaces.cache import ICache
from profile_intelligence.infrastructure.cache.base import (
    decode_value,
    encode_value,
    expires_at_from_ttl,
    is_expired,
    resolve_ttl,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache_entries (
    key TEXT PRIMARY KEY NOT NULL,
    value TEXT NOT NULL,
    expires_at REAL
)
"""


class SQLiteCache(ICache):
    """Durable cache stored in a dedicated SQLite file."""

    def __init__(
        self,
        database_path: PathLike,
        *,
        default_ttl_seconds: float | None = None,
    ) -> None:
        self._path = Path(database_path)
        self._default_ttl = default_ttl_seconds
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._connect() as connection:
                connection.execute(_SCHEMA)
                connection.commit()
        except sqlite3.Error as exc:
            raise CacheError(
                f"Failed to initialize SQLite cache at {self._path}",
                cause=exc,
            ) from exc

    @property
    def backend(self) -> str:
        return "sqlite"

    @property
    def database_path(self) -> Path:
        """Path to the cache SQLite file."""
        return self._path

    def get(self, key: str) -> object | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT value, expires_at FROM cache_entries WHERE key = ?",
                    (key,),
                ).fetchone()
                if row is None:
                    return None
                value, expires_at = row
                if is_expired(expires_at):
                    connection.execute(
                        "DELETE FROM cache_entries WHERE key = ?",
                        (key,),
                    )
                    connection.commit()
                    return None
                return decode_value(str(value))
        except (sqlite3.Error, json.JSONDecodeError) as exc:
            raise CacheError(f"Failed to read cache key {key!r}", cause=exc) from exc

    def set(
        self,
        key: str,
        value: object,
        *,
        ttl_seconds: float | None = None,
    ) -> None:
        ttl = resolve_ttl(ttl_seconds, default_ttl=self._default_ttl)
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO cache_entries (key, value, expires_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        expires_at = excluded.expires_at
                    """,
                    (key, encode_value(value), expires_at_from_ttl(ttl)),
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise CacheError(f"Failed to write cache key {key!r}", cause=exc) from exc

    def delete(self, key: str) -> bool:
        try:
            with self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM cache_entries WHERE key = ?",
                    (key,),
                )
                connection.commit()
                return int(cursor.rowcount or 0) > 0
        except sqlite3.Error as exc:
            raise CacheError(f"Failed to delete cache key {key!r}", cause=exc) from exc

    def clear(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute("DELETE FROM cache_entries")
                connection.commit()
        except sqlite3.Error as exc:
            raise CacheError("Failed to clear SQLite cache", cause=exc) from exc

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.execute("PRAGMA foreign_keys=ON")
        return connection
