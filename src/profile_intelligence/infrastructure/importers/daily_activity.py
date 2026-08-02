"""In-memory progress for the Daily automation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class DailyActivityStore:
    """Track the latest daily run progress for the UI."""

    _lock: Lock = field(default_factory=Lock, repr=False)
    _progress: dict[str, Any] | None = None
    _last_result: dict[str, Any] | None = None

    def set_progress(
        self,
        *,
        stage: str,
        message: str,
        percent: int,
        stages_run: list[str],
        pipeline: list[str],
    ) -> None:
        with self._lock:
            self._progress = {
                "stage": stage,
                "message": message,
                "percent": percent,
                "stages_run": list(stages_run),
                "pipeline": list(pipeline),
                "status": "running",
            }

    def record_result(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._last_result = dict(payload)
            self._progress = {
                "stage": payload.get("stage", "dashboard"),
                "message": payload.get("message", "Finished"),
                "percent": int(payload.get("percent", 100)),
                "stages_run": list(payload.get("stages_run") or []),
                "pipeline": list(payload.get("pipeline") or []),
                "status": "ok" if payload.get("success", True) else "error",
            }

    def clear_progress(self) -> None:
        with self._lock:
            self._progress = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "progress": dict(self._progress) if self._progress else None,
                "last_result": (
                    dict(self._last_result) if self._last_result else None
                ),
            }


__all__ = ["DailyActivityStore"]
