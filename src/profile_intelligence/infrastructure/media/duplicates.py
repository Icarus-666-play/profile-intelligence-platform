"""Detect duplicate media files by content hash."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.media.hashing import (
    DEFAULT_ALGORITHM,
    hash_file,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DuplicateImageGroup:
    """A set of paths that share the same content hash."""

    content_hash: str
    paths: tuple[Path, ...]

    @property
    def count(self) -> int:
        """Number of files in the group."""
        return len(self.paths)

    @property
    def extras(self) -> tuple[Path, ...]:
        """Paths beyond the first (canonical) member."""
        return self.paths[1:]


@dataclass(frozen=True, slots=True)
class DuplicateScanResult:
    """Outcome of a duplicate media scan."""

    groups: tuple[DuplicateImageGroup, ...] = field(default_factory=tuple)
    hashed: int = 0
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def duplicate_count(self) -> int:
        """Total duplicate files beyond one keeper per group."""
        return sum(len(group.extras) for group in self.groups)


class ImageDuplicateFinder:
    """Group image files that share an identical content hash."""

    def __init__(self, *, algorithm: str = DEFAULT_ALGORITHM) -> None:
        self.algorithm = algorithm

    def find(
        self,
        paths: Iterable[PathLike],
    ) -> DuplicateScanResult:
        """Hash *paths* and return groups with more than one member."""
        hashes: dict[Path, str] = {}
        errors: list[str] = []
        for raw in paths:
            path = Path(raw)
            try:
                hashes[path.resolve()] = hash_file(
                    path, algorithm=self.algorithm
                )
            except Exception as exc:  # noqa: BLE001 - collect and continue
                errors.append(f"{path}: {exc}")
                logger.warning("Skipping unreadable media path %s: %s", path, exc)

        groups = self.group_by_hash(hashes)
        result = DuplicateScanResult(
            groups=groups,
            hashed=len(hashes),
            errors=tuple(errors),
        )
        logger.info(
            "Duplicate scan: hashed=%d groups=%d extras=%d errors=%d",
            result.hashed,
            len(result.groups),
            result.duplicate_count,
            len(result.errors),
        )
        return result

    @staticmethod
    def group_by_hash(
        hashes: Mapping[str, str] | Mapping[Path, str],
    ) -> tuple[DuplicateImageGroup, ...]:
        """Build duplicate groups from an existing path→hash mapping."""
        buckets: dict[str, list[Path]] = defaultdict(list)
        for path, digest in hashes.items():
            buckets[digest].append(Path(path))

        groups: list[DuplicateImageGroup] = []
        for digest, members in sorted(buckets.items(), key=lambda item: item[0]):
            if len(members) < 2:
                continue
            ordered = tuple(sorted(members, key=lambda item: str(item)))
            groups.append(
                DuplicateImageGroup(content_hash=digest, paths=ordered)
            )
        return tuple(groups)

    def keepers(
        self,
        groups: Sequence[DuplicateImageGroup],
    ) -> dict[str, Path]:
        """Return the canonical (first) path for each duplicate group."""
        return {group.content_hash: group.paths[0] for group in groups}
