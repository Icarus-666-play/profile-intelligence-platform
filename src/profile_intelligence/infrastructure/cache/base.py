"""Shared helpers for cache backends."""

from __future__ import annotations

import json
import time


def now_seconds() -> float:
    """Return the current unix timestamp in seconds."""
    return time.time()


def is_expired(expires_at: float | None, *, now: float | None = None) -> bool:
    """Return True when *expires_at* is in the past."""
    if expires_at is None:
        return False
    return (now if now is not None else now_seconds()) >= expires_at


def encode_value(value: object) -> str:
    """Serialize a JSON-compatible value for durable backends."""
    return json.dumps(value, ensure_ascii=True, default=str, separators=(",", ":"))


def decode_value(payload: str) -> object:
    """Deserialize a JSON payload from a durable backend."""
    return json.loads(payload)


def resolve_ttl(
    ttl_seconds: float | None,
    *,
    default_ttl: float | None,
) -> float | None:
    """Pick an effective TTL; ``0`` or negative means no expiry."""
    effective = default_ttl if ttl_seconds is None else ttl_seconds
    if effective is None:
        return None
    if effective <= 0:
        return None
    return float(effective)


def expires_at_from_ttl(ttl_seconds: float | None) -> float | None:
    """Convert a TTL into an absolute expiry timestamp."""
    if ttl_seconds is None or ttl_seconds <= 0:
        return None
    return now_seconds() + float(ttl_seconds)
