"""Daily automation operator progress stages.

```
Every Day
 ↓
Check Import Queue
 ↓
Import
 ↓
Statistics
 ↓
Excel
 ↓
Dashboard
```
"""

from __future__ import annotations

DAILY_STAGES: tuple[str, ...] = (
    "every_day",
    "check_import_queue",
    "import",
    "statistics",
    "excel",
    "dashboard",
)

DAILY_STAGE_LABELS: dict[str, str] = {
    "every_day": "Every Day",
    "check_import_queue": "Check Import Queue",
    "import": "Import",
    "statistics": "Statistics",
    "excel": "Excel",
    "dashboard": "Dashboard",
}


def stage_percent(stage: str) -> int:
    """Return a 0–100 progress percent for *stage* in the daily chain."""
    try:
        index = DAILY_STAGES.index(stage)
    except ValueError:
        return 0
    if len(DAILY_STAGES) <= 1:
        return 100
    return int(round((index / (len(DAILY_STAGES) - 1)) * 100))


def stages_through(stage: str) -> tuple[str, ...]:
    """Return pipeline stages from ``every_day`` through *stage* inclusive."""
    try:
        index = DAILY_STAGES.index(stage)
    except ValueError:
        return ()
    return DAILY_STAGES[: index + 1]


__all__ = [
    "DAILY_STAGE_LABELS",
    "DAILY_STAGES",
    "stage_percent",
    "stages_through",
]
