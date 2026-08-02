"""Local filesystem storage rooted at configured data directories.

```
… → Repository Layer → SQLite
                     ↘ File Storage
```

SQLite holds structured profile rows; this adapter owns blobs and operator
artifacts under ``data/`` (media, inbox, cache) and ``exports/``.
"""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.types import PathLike


class FileStorage:
    """Resolve and ensure local file-storage roots."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @property
    def data_dir(self) -> Path:
        return self._config.data_dir

    @property
    def media_dir(self) -> Path:
        return self._config.media_dir

    @property
    def inbox_dir(self) -> Path:
        return self.data_dir / "inbox"

    @property
    def cache_dir(self) -> Path:
        return self._config.cache_dir

    @property
    def exports_dir(self) -> Path:
        return self._config.exports_dir

    def ensure_directories(self) -> None:
        """Create storage roots used by the stack."""
        self._config.ensure_directories()
        for path in (
            self.media_dir,
            self._config.thumbnails_dir,
            self._config.media_downloads_dir,
            self.inbox_dir,
            self.inbox_dir / "downloads",
            self.cache_dir,
            self.exports_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative: PathLike) -> Path:
        """Resolve a path relative to ``data_dir`` (no escape above root)."""
        root = self.data_dir.resolve()
        candidate = (root / Path(relative)).resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError(f"Path escapes data_dir: {relative}")
        return candidate


__all__ = ["FileStorage"]
