"""Nightly automation workflow.

```
Import every night
 ↓
Update database
 ↓
Recalculate scores
 ↓
Generate Excel report
 ↓
Export dashboard
```

Schedule externally (cron / Task Scheduler)::

    pip-app nightly
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from profile_intelligence.application.use_cases.import_service import (
    ImportService,
    ImportSummary,
)
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.exceptions import ServiceError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.database.migrate import run_migrations
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry

logger = get_logger(__name__)

NIGHTLY_STAGES: tuple[str, ...] = (
    "import",
    "update_database",
    "recalculate_scores",
    "generate_excel_report",
    "export_dashboard",
)


@dataclass(frozen=True, slots=True)
class NightlyResult:
    """Outcome of one nightly automation run."""

    stages_run: tuple[str, ...]
    files_imported: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    profile_count: int = 0
    rescored: int = 0
    excel_path: str | None = None
    dashboard_path: str | None = None
    import_summaries: tuple[ImportSummary, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def success(self) -> bool:
        """True when the workflow completed without hard errors."""
        return not self.errors


class NightlyPipeline:
    """Run the end-of-day import → report automation chain."""

    def __init__(
        self,
        config: AppConfig,
        import_service: ImportService,
        profile_service: ProfileService,
        dashboard: DashboardService,
        database: Database,
        registry: ImporterRegistry,
    ) -> None:
        self._config = config
        self._import = import_service
        self._profiles = profile_service
        self._dashboard = dashboard
        self._database = database
        self._registry = registry

    def run(
        self,
        *,
        import_dir: PathLike | None = None,
        excel_path: PathLike | None = None,
        dashboard_path: PathLike | None = None,
        rescore: bool | None = None,
        recursive: bool | None = None,
    ) -> NightlyResult:
        """Execute all nightly stages in order."""
        self._config.ensure_directories()
        inbox = (
            Path(import_dir)
            if import_dir is not None
            else self._config.nightly_import_dir
        )
        if not inbox.is_absolute():
            inbox = self._config.resolve_path(inbox)

        excel_out = (
            Path(excel_path)
            if excel_path is not None
            else self._config.nightly_excel_path
        )
        if not excel_out.is_absolute():
            excel_out = self._config.resolve_path(excel_out)

        dashboard_out = (
            Path(dashboard_path)
            if dashboard_path is not None
            else self._config.nightly_dashboard_path
        )
        if not dashboard_out.is_absolute():
            dashboard_out = self._config.resolve_path(dashboard_out)

        do_rescore = (
            self._config.nightly.rescore if rescore is None else rescore
        )
        do_recursive = (
            self._config.nightly.recursive if recursive is None else recursive
        )

        logger.info(
            "Nightly pipeline start: inbox=%s stages=%s",
            inbox,
            " → ".join(NIGHTLY_STAGES),
        )
        errors: list[str] = []
        stages_run: list[str] = []

        # 1. Import every night
        summaries, import_errors = self._import_inbox(
            inbox, recursive=do_recursive
        )
        errors.extend(import_errors)
        stages_run.append("import")
        created = sum(item.created for item in summaries)
        updated = sum(item.updated for item in summaries)
        skipped = sum(item.skipped for item in summaries)

        # 2. Update database (ensure schema + capture post-import totals)
        try:
            run_migrations(self._database)
            profile_count = self._profiles.count()
        except Exception as exc:
            raise ServiceError(
                "Nightly update_database stage failed",
                cause=exc,
            ) from exc
        stages_run.append("update_database")
        logger.info(
            "Nightly update_database: profiles=%d created=%d updated=%d",
            profile_count,
            created,
            updated,
        )

        # 3. Recalculate scores
        rescored = 0
        if do_rescore:
            try:
                rescored = self._profiles.rescore_all()
            except Exception as exc:
                raise ServiceError(
                    "Nightly recalculate_scores stage failed",
                    cause=exc,
                ) from exc
        stages_run.append("recalculate_scores")

        # 4. Generate Excel report
        try:
            excel_written = self._profiles.export_excel(excel_out)
        except Exception as exc:
            raise ServiceError(
                "Nightly generate_excel_report stage failed",
                cause=exc,
            ) from exc
        stages_run.append("generate_excel_report")

        # 5. Export dashboard
        try:
            text = self._dashboard.render_text()
            dashboard_out.parent.mkdir(parents=True, exist_ok=True)
            dashboard_out.write_text(text + "\n", encoding="utf-8")
        except Exception as exc:
            raise ServiceError(
                "Nightly export_dashboard stage failed",
                cause=exc,
            ) from exc
        stages_run.append("export_dashboard")

        result = NightlyResult(
            stages_run=tuple(stages_run),
            files_imported=len(summaries),
            created=created,
            updated=updated,
            skipped=skipped,
            profile_count=profile_count,
            rescored=rescored,
            excel_path=str(excel_written),
            dashboard_path=str(dashboard_out),
            import_summaries=tuple(summaries),
            errors=tuple(errors),
        )
        logger.info(
            "Nightly pipeline done: files=%d created=%d updated=%d "
            "rescored=%d excel=%s dashboard=%s",
            result.files_imported,
            result.created,
            result.updated,
            result.rescored,
            result.excel_path,
            result.dashboard_path,
        )
        return result

    def _import_inbox(
        self,
        inbox: Path,
        *,
        recursive: bool,
    ) -> tuple[list[ImportSummary], list[str]]:
        inbox.mkdir(parents=True, exist_ok=True)
        files = self._discover_import_files(inbox, recursive=recursive)
        if not files:
            logger.info("Nightly import: no importable files in %s", inbox)
            return [], []

        summaries: list[ImportSummary] = []
        errors: list[str] = []
        for path in files:
            try:
                summary = self._import.import_path(path)
                summaries.append(summary)
                errors.extend(summary.errors)
            except Exception as exc:
                message = f"{path}: {exc}"
                errors.append(message)
                logger.exception("Nightly import failed for %s", path)
        return summaries, errors

    def _discover_import_files(
        self,
        inbox: Path,
        *,
        recursive: bool,
    ) -> Sequence[Path]:
        pattern_iter = inbox.rglob("*") if recursive else inbox.iterdir()
        candidates = sorted(
            path
            for path in pattern_iter
            if path.is_file() and not path.name.startswith(".")
        )
        return [
            path
            for path in candidates
            if self._registry.find_handler(path) is not None
        ]
