"""Content hashing helpers for media files."""

from __future__ import annotations

import hashlib
from pathlib import Path

from profile_intelligence.core.exceptions import MediaError
from profile_intelligence.core.types import PathLike

DEFAULT_ALGORITHM = "sha256"
DEFAULT_CHUNK_SIZE = 65_536

_SUPPORTED = frozenset(hashlib.algorithms_available)


def normalize_algorithm(algorithm: str | None = None) -> str:
    """Return a supported hashlib algorithm name."""
    name = (algorithm or DEFAULT_ALGORITHM).strip().lower()
    if name not in _SUPPORTED:
        raise MediaError(f"Unsupported hash algorithm: {algorithm!r}")
    return name


def hash_bytes(
    data: bytes,
    *,
    algorithm: str | None = None,
) -> str:
    """Return the hex digest for *data*."""
    algo = normalize_algorithm(algorithm)
    return hashlib.new(algo, data).hexdigest()


def hash_file(
    path: PathLike,
    *,
    algorithm: str | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str:
    """Return the hex digest for the contents of *path*."""
    if chunk_size < 1:
        raise MediaError("chunk_size must be >= 1")
    resolved = Path(path)
    if not resolved.is_file():
        raise MediaError(f"Media file not found: {resolved}")

    algo = normalize_algorithm(algorithm)
    digest = hashlib.new(algo)
    try:
        with resolved.open("rb") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                digest.update(chunk)
    except OSError as exc:
        raise MediaError(
            f"Unable to read media file: {resolved}",
            cause=exc,
        ) from exc
    return digest.hexdigest()


def short_hash(digest: str, *, length: int = 16) -> str:
    """Return a shortened prefix of *digest* for display / filenames."""
    if length < 1:
        raise MediaError("length must be >= 1")
    cleaned = digest.strip().lower()
    if not cleaned:
        raise MediaError("digest must not be empty")
    return cleaned[:length]
