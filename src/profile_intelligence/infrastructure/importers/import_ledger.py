"""Ledger of previously imported inbox files for Daily detect-new-files."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

from profile_intelligence.core.exceptions import RepositoryError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.media.hashing import hash_file

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    """One recorded import-file fingerprint."""

    path: str
    content_hash: str
    file_size: int
    imported_at: str | None = None


class ImportFileLedger:
    """Track imported files by content hash so Daily can detect new files."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def content_hash(self, path: PathLike) -> str:
        """Return the content hash used for ledger identity."""
        return hash_file(path)

    def has_hash(self, content_hash: str) -> bool:
        """Return True when *content_hash* was imported before."""
        try:
            with self._database.session() as session:
                row = session.execute(
                    text(
                        "SELECT 1 FROM import_file_ledger "
                        "WHERE content_hash = :digest LIMIT 1"
                    ),
                    {"digest": content_hash},
                ).first()
                return row is not None
        except Exception as exc:
            raise RepositoryError(
                "Failed to query import file ledger",
                cause=exc,
            ) from exc

    def is_new(self, path: PathLike) -> bool:
        """Return True when *path* content has not been imported yet."""
        return not self.has_hash(self.content_hash(path))

    def detect_new(self, paths: Sequence[PathLike]) -> tuple[Path, ...]:
        """Filter *paths* down to files whose content is not in the ledger."""
        new_files: list[Path] = []
        for raw in paths:
            path = Path(raw)
            try:
                if self.is_new(path):
                    new_files.append(path)
            except Exception as exc:  # noqa: BLE001 - continue scanning
                logger.warning("Ledger skip unreadable file %s: %s", path, exc)
        logger.info(
            "Detect new files: candidates=%d new=%d",
            len(paths),
            len(new_files),
        )
        return tuple(new_files)

    def mark_imported(self, path: PathLike) -> LedgerEntry:
        """Record *path* as imported (upsert by content hash)."""
        resolved = Path(path).resolve()
        digest = self.content_hash(resolved)
        size = resolved.stat().st_size
        try:
            with self._database.session() as session:
                session.execute(
                    text(
                        """
                        INSERT INTO import_file_ledger
                            (path, content_hash, file_size)
                        VALUES
                            (:path, :digest, :size)
                        ON CONFLICT(content_hash) DO UPDATE SET
                            path = excluded.path,
                            file_size = excluded.file_size,
                            imported_at = CURRENT_TIMESTAMP
                        """
                    ),
                    {
                        "path": str(resolved),
                        "digest": digest,
                        "size": size,
                    },
                )
            entry = LedgerEntry(
                path=str(resolved),
                content_hash=digest,
                file_size=size,
            )
            logger.debug("Ledger marked imported: %s", resolved)
            return entry
        except Exception as exc:
            raise RepositoryError(
                f"Failed to mark import file in ledger: {resolved}",
                cause=exc,
            ) from exc

    def list_recent(self, *, limit: int = 10) -> tuple[LedgerEntry, ...]:
        """Return the most recently imported ledger rows."""
        try:
            with self._database.session() as session:
                rows = session.execute(
                    text(
                        """
                        SELECT path, content_hash, file_size, imported_at
                        FROM import_file_ledger
                        ORDER BY imported_at DESC, id DESC
                        LIMIT :limit
                        """
                    ),
                    {"limit": max(1, int(limit))},
                ).all()
        except Exception as exc:
            raise RepositoryError(
                "Failed to list recent import ledger rows",
                cause=exc,
            ) from exc
        return tuple(
            LedgerEntry(
                path=str(row[0]),
                content_hash=str(row[1]),
                file_size=int(row[2] or 0),
                imported_at=str(row[3]) if row[3] is not None else None,
            )
            for row in rows
        )
