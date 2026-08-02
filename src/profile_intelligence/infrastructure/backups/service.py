"""Local database backup helpers for Settings → Backups."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.exceptions import PipError
from profile_intelligence.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class BackupItem:
    """One backup file under the backups directory."""

    name: str
    path: str
    size_bytes: int
    created_at: str | None


class BackupService:
    """Copy the configured SQLite database into ``exports/backups/``."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @property
    def backup_dir(self) -> Path:
        """Directory that stores database backups."""
        path = self._config.exports_dir / "backups"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_backups(self, *, limit: int = 50) -> tuple[BackupItem, ...]:
        """Return recent backup files, newest first."""
        items: list[BackupItem] = []
        for path in sorted(
            self.backup_dir.glob("pip-*.sqlite3"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            try:
                stat = path.stat()
            except OSError:
                continue
            items.append(
                BackupItem(
                    name=path.name,
                    path=str(path),
                    size_bytes=int(stat.st_size),
                    created_at=datetime.fromtimestamp(
                        stat.st_mtime, tz=UTC
                    ).isoformat(),
                )
            )
            if len(items) >= max(1, limit):
                break
        return tuple(items)

    def create_backup(self) -> BackupItem:
        """Create a timestamped copy of the active SQLite database file."""
        source = self._config.database_path
        if not source.is_file():
            raise PipError(f"Database file not found: {source}")
        stamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
        target = self.backup_dir / f"pip-{stamp}.sqlite3"
        try:
            shutil.copy2(source, target)
        except OSError as exc:
            raise PipError(f"Failed to create backup: {exc}") from exc
        logger.info("Created database backup %s", target)
        stat = target.stat()
        return BackupItem(
            name=target.name,
            path=str(target),
            size_bytes=int(stat.st_size),
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
        )


__all__ = ["BackupItem", "BackupService"]
