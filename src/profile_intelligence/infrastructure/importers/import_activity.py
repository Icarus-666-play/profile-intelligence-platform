"""Persist operator Import UI activity (recent URLs, progress, errors, completed)."""

from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.logging import get_logger
from profile_intelligence.infrastructure.importers.import_ledger import ImportFileLedger

logger = get_logger(__name__)

_MAX_RECENT = 25
_MAX_ERRORS = 50
_MAX_COMPLETED = 50


@dataclass(slots=True)
class ImportProgress:
    """In-flight URL import/preview job."""

    url: str
    stage: str
    message: str
    started_at: str
    percent: int = 0


@dataclass(slots=True)
class ImportActivitySnapshot:
    """Payload for the Import page side panels."""

    recent_urls: list[dict[str, Any]] = field(default_factory=list)
    import_queue: list[dict[str, Any]] = field(default_factory=list)
    progress: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    completed: list[dict[str, Any]] = field(default_factory=list)


class ImportActivityStore:
    """JSON-backed activity log under ``data/import_activity.json``."""

    def __init__(
        self,
        config: AppConfig,
        *,
        ledger: ImportFileLedger | None = None,
    ) -> None:
        self._config = config
        self._ledger = ledger
        self._path = config.data_dir / "import_activity.json"
        self._lock = threading.Lock()

    def snapshot(self) -> ImportActivitySnapshot:
        """Return recent URLs, queue, progress, errors, and completed jobs."""
        with self._lock:
            raw = self._load_unlocked()
        return ImportActivitySnapshot(
            recent_urls=list(raw.get("recent_urls") or []),
            import_queue=self._queue_items(),
            progress=raw.get("progress"),
            errors=list(raw.get("errors") or []),
            completed=list(raw.get("completed") or []),
        )

    def remember_url(self, url: str) -> None:
        """Push *url* to the Recent URLs list."""
        cleaned = url.strip()
        if not cleaned:
            return
        with self._lock:
            raw = self._load_unlocked()
            recent = [
                item
                for item in list(raw.get("recent_urls") or [])
                if str(item.get("url") or "") != cleaned
            ]
            recent.insert(
                0,
                {"url": cleaned, "at": _now()},
            )
            raw["recent_urls"] = recent[:_MAX_RECENT]
            self._save_unlocked(raw)

    def set_progress(
        self,
        *,
        url: str,
        stage: str,
        message: str,
        percent: int = 0,
    ) -> None:
        """Mark an in-flight job for the Progress panel."""
        with self._lock:
            raw = self._load_unlocked()
            raw["progress"] = asdict(
                ImportProgress(
                    url=url,
                    stage=stage,
                    message=message,
                    started_at=_now(),
                    percent=max(0, min(100, int(percent))),
                )
            )
            self._save_unlocked(raw)

    def clear_progress(self) -> None:
        """Clear the Progress panel."""
        with self._lock:
            raw = self._load_unlocked()
            raw["progress"] = None
            self._save_unlocked(raw)

    def record_error(self, *, url: str, message: str) -> None:
        """Append an error row and clear progress."""
        with self._lock:
            raw = self._load_unlocked()
            errors = list(raw.get("errors") or [])
            errors.insert(
                0,
                {"url": url, "message": message, "at": _now()},
            )
            raw["errors"] = errors[:_MAX_ERRORS]
            raw["progress"] = None
            self._save_unlocked(raw)

    def record_completed(
        self,
        *,
        url: str,
        path: str | None = None,
        plugin: str | None = None,
        created: int = 0,
        updated: int = 0,
        success: bool = True,
        message: str | None = None,
    ) -> None:
        """Append a completed import and clear progress."""
        with self._lock:
            raw = self._load_unlocked()
            completed = list(raw.get("completed") or [])
            completed.insert(
                0,
                {
                    "url": url,
                    "path": path,
                    "plugin": plugin,
                    "created": created,
                    "updated": updated,
                    "success": success,
                    "message": message,
                    "at": _now(),
                },
            )
            raw["completed"] = completed[:_MAX_COMPLETED]
            raw["progress"] = None
            self._save_unlocked(raw)

    def _queue_items(self) -> list[dict[str, Any]]:
        if self._ledger is None:
            return []
        inbox = self._config.daily_import_dir
        if not inbox.is_dir():
            return []
        candidates = sorted(
            path
            for path in inbox.rglob("*")
            if path.is_file() and not path.name.startswith(".")
        )
        try:
            new_files = self._ledger.detect_new(candidates)[:20]
        except Exception as exc:  # noqa: BLE001 — activity panel stays soft
            logger.debug("Import queue scan failed: %s", exc)
            return []
        items: list[dict[str, Any]] = []
        for path in new_files:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            items.append(
                {"path": str(path), "name": path.name, "file_size": size}
            )
        return items

    def _load_unlocked(self) -> dict[str, Any]:
        if not self._path.is_file():
            return {
                "recent_urls": [],
                "progress": None,
                "errors": [],
                "completed": [],
            }
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Corrupt import activity file %s: %s", self._path, exc)
            return {
                "recent_urls": [],
                "progress": None,
                "errors": [],
                "completed": [],
            }
        if not isinstance(payload, dict):
            return {
                "recent_urls": [],
                "progress": None,
                "errors": [],
                "completed": [],
            }
        return payload

    def _save_unlocked(self, payload: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self._path)


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


__all__ = ["ImportActivitySnapshot", "ImportActivityStore", "ImportProgress"]
