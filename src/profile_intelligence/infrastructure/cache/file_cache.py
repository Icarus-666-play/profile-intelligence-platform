"""Filesystem cache backend (one file per key)."""

from __future__ import annotations

import hashlib
import json
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


class FileCache(ICache):
    """Durable cache storing JSON envelopes under a directory."""

    def __init__(
        self,
        root_dir: PathLike,
        *,
        default_ttl_seconds: float | None = None,
    ) -> None:
        self._root = Path(root_dir)
        self._default_ttl = default_ttl_seconds
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def backend(self) -> str:
        return "file"

    @property
    def root_dir(self) -> Path:
        """Directory containing cache entry files."""
        return self._root

    def get(self, key: str) -> object | None:
        path = self._path_for(key)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CacheError(f"Failed to read cache key {key!r}", cause=exc) from exc
        expires_at = payload.get("expires_at")
        if is_expired(expires_at if isinstance(expires_at, (int, float)) else None):
            path.unlink(missing_ok=True)
            return None
        raw = payload.get("value")
        if not isinstance(raw, str):
            return None
        return decode_value(raw)

    def set(
        self,
        key: str,
        value: object,
        *,
        ttl_seconds: float | None = None,
    ) -> None:
        ttl = resolve_ttl(ttl_seconds, default_ttl=self._default_ttl)
        envelope = {
            "key": key,
            "value": encode_value(value),
            "expires_at": expires_at_from_ttl(ttl),
        }
        path = self._path_for(key)
        try:
            path.write_text(
                json.dumps(envelope, ensure_ascii=True, separators=(",", ":")),
                encoding="utf-8",
            )
        except OSError as exc:
            raise CacheError(f"Failed to write cache key {key!r}", cause=exc) from exc

    def delete(self, key: str) -> bool:
        path = self._path_for(key)
        if not path.is_file():
            return False
        path.unlink(missing_ok=True)
        return True

    def clear(self) -> None:
        for path in self._root.glob("*.json"):
            path.unlink(missing_ok=True)

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self._root / f"{digest}.json"
