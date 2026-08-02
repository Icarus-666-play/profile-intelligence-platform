"""Nightly automation workflow (compatibility alias for Daily).

Prefer :class:`~profile_intelligence.application.use_cases.daily_pipeline.DailyPipeline`
and ``pip-app daily``.

```
Daily
 ↓
Import Folder
 ↓
Detect new files
 ↓
Import
 ↓
Update
 ↓
Generate Excel
 ↓
Create Dashboard
 ↓
Email Report (future)
```
"""

from __future__ import annotations

from profile_intelligence.application.use_cases.daily_pipeline import (
    DAILY_STAGES,
    DailyPipeline,
    DailyResult,
)
from profile_intelligence.core.types import PathLike

# Historical name retained for scripts / docs that still say "nightly".
NIGHTLY_STAGES: tuple[str, ...] = DAILY_STAGES
NightlyResult = DailyResult


class NightlyPipeline:
    """Backward-compatible wrapper around :class:`DailyPipeline`."""

    def __init__(self, daily_pipeline: DailyPipeline) -> None:
        self._daily = daily_pipeline

    @property
    def daily(self) -> DailyPipeline:
        """Underlying daily pipeline instance."""
        return self._daily

    def run(
        self,
        *,
        import_dir: PathLike | None = None,
        excel_path: PathLike | None = None,
        dashboard_path: PathLike | None = None,
        rescore: bool | None = None,
        recursive: bool | None = None,
        force_all_files: bool = False,
    ) -> DailyResult:
        """Delegate to the Daily pipeline."""
        return self._daily.run(
            import_dir=import_dir,
            excel_path=excel_path,
            dashboard_path=dashboard_path,
            rescore=rescore,
            recursive=recursive,
            force_all_files=force_all_files,
        )
