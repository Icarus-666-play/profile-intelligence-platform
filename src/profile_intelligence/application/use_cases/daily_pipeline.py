"""Daily automation workflow.

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

Schedule externally (cron / Task Scheduler)::

    pip-app daily
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from profile_intelligence.application.use_cases.import_service import (
    ImportService,
    ImportSummary,
)
from profile_intelligence.application.use_cases.media_pipeline import ImagePipeline
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.exceptions import ServiceError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.events import (
    WORKFLOW_EVENT_CHAIN,
    DashboardUpdated,
    DomainEvent,
    ExcelExported,
    ImagesExtracted,
    ProfileImported,
    ScoreCalculated,
)
from profile_intelligence.domain.interfaces.events import IEventBus
from profile_intelligence.domain.interfaces.repositories import IPhotoRepository
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.database.migrate import run_migrations
from profile_intelligence.infrastructure.importers.import_ledger import ImportFileLedger
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.infrastructure.media.image_repository import ImageRepository
from profile_intelligence.infrastructure.reporting.email_report import (
    EmailReportResult,
    EmailReportService,
)

logger = get_logger(__name__)

DAILY_STAGES: tuple[str, ...] = (
    "import_folder",
    "detect_new_files",
    "import",
    "update",
    "generate_excel",
    "create_dashboard",
    "email_report",
)


@dataclass(frozen=True, slots=True)
class DailyResult:
    """Outcome of one daily automation run."""

    stages_run: tuple[str, ...]
    import_folder: str | None = None
    files_detected: int = 0
    files_new: int = 0
    files_imported: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    profile_count: int = 0
    rescored: int = 0
    images_extracted: int = 0
    excel_path: str | None = None
    dashboard_path: str | None = None
    email_sent: bool = False
    email_skipped: bool = True
    email_message: str | None = None
    import_summaries: tuple[ImportSummary, ...] = field(default_factory=tuple)
    events: tuple[DomainEvent, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def success(self) -> bool:
        """True when the workflow completed without hard errors."""
        return not self.errors

    @property
    def event_names(self) -> tuple[str, ...]:
        """Published workflow event names in order."""
        return tuple(event.name for event in self.events)


class DailyPipeline:
    """Run the Daily import-folder → report automation chain."""

    def __init__(
        self,
        config: AppConfig,
        import_service: ImportService,
        profile_service: ProfileService,
        dashboard: DashboardService,
        database: Database,
        registry: ImporterRegistry,
        *,
        event_bus: IEventBus | None = None,
        photo_repository: IPhotoRepository | None = None,
        image_repository: ImageRepository | None = None,
        image_pipeline: ImagePipeline | None = None,
        import_ledger: ImportFileLedger | None = None,
        email_report: EmailReportService | None = None,
    ) -> None:
        self._config = config
        self._import = import_service
        self._profiles = profile_service
        self._dashboard = dashboard
        self._database = database
        self._registry = registry
        self._events = event_bus
        self._photos = photo_repository
        self._images = image_repository
        self._image_pipeline = image_pipeline
        self._ledger = import_ledger or ImportFileLedger(database)
        self._email = email_report or EmailReportService(
            enabled=config.daily.email_enabled,
            recipients=(
                (config.daily.email_to,) if config.daily.email_to else ()
            ),
        )

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
        """Execute all Daily stages and publish workflow events."""
        self._config.ensure_directories()

        # 1. Import Folder
        inbox = (
            Path(import_dir)
            if import_dir is not None
            else self._config.daily_import_dir
        )
        if not inbox.is_absolute():
            inbox = self._config.resolve_path(inbox)
        inbox.mkdir(parents=True, exist_ok=True)
        stages_run: list[str] = ["import_folder"]

        excel_out = (
            Path(excel_path)
            if excel_path is not None
            else self._config.daily_excel_path
        )
        if not excel_out.is_absolute():
            excel_out = self._config.resolve_path(excel_out)

        dashboard_out = (
            Path(dashboard_path)
            if dashboard_path is not None
            else self._config.daily_dashboard_path
        )
        if not dashboard_out.is_absolute():
            dashboard_out = self._config.resolve_path(dashboard_out)

        do_rescore = self._config.daily.rescore if rescore is None else rescore
        do_recursive = (
            self._config.daily.recursive if recursive is None else recursive
        )

        if self._events is not None:
            self._events.clear_history()

        logger.info(
            "Daily pipeline start: folder=%s stages=%s events=%s",
            inbox,
            " → ".join(DAILY_STAGES),
            " → ".join(cls.__name__ for cls in WORKFLOW_EVENT_CHAIN),
        )
        errors: list[str] = []
        published: list[DomainEvent] = []

        # Ensure ledger schema exists before detect/import.
        run_migrations(self._database)

        # 2. Detect new files
        candidates = self._discover_import_files(inbox, recursive=do_recursive)
        if force_all_files:
            new_files = tuple(candidates)
        else:
            new_files = self._ledger.detect_new(candidates)
        stages_run.append("detect_new_files")
        logger.info(
            "Daily detect_new_files: folder=%s candidates=%d new=%d",
            inbox,
            len(candidates),
            len(new_files),
        )

        # 3. Import
        summaries, import_errors = self._import_files(new_files)
        errors.extend(import_errors)
        stages_run.append("import")
        created = sum(item.created for item in summaries)
        updated = sum(item.updated for item in summaries)
        skipped = sum(item.skipped for item in summaries)

        # 4. Update (DB totals + confidence scores + images)
        try:
            run_migrations(self._database)
            profile_count = self._profiles.count()
            profile_ids = tuple(
                int(row.id)
                for row in self._profiles.list_profiles(limit=100_000, offset=0)
                if row.id is not None
            )
            rescored = 0
            if do_rescore:
                rescored = self._profiles.rescore_all()
            image_count = self._extract_images(profile_ids)
        except Exception as exc:
            raise ServiceError("Daily update stage failed", cause=exc) from exc
        stages_run.append("update")
        logger.info(
            "Daily update: profiles=%d created=%d updated=%d "
            "rescored=%d images=%d",
            profile_count,
            created,
            updated,
            rescored,
            image_count,
        )
        published.append(
            self._publish(
                ProfileImported(
                    profile_ids=profile_ids,
                    created=created,
                    updated=updated,
                    path=str(inbox),
                )
            )
        )
        published.append(
            self._publish(
                ScoreCalculated(profile_ids=profile_ids, rescored=rescored)
            )
        )
        published.append(
            self._publish(
                ImagesExtracted(
                    profile_ids=profile_ids,
                    image_count=image_count,
                )
            )
        )

        # 5. Generate Excel
        try:
            excel_written = self._profiles.export_excel(excel_out)
        except Exception as exc:
            raise ServiceError(
                "Daily generate_excel stage failed",
                cause=exc,
            ) from exc
        stages_run.append("generate_excel")
        published.append(
            self._publish(
                ExcelExported(
                    path=str(excel_written),
                    profile_count=profile_count,
                )
            )
        )

        # 6. Create Dashboard
        try:
            text = self._dashboard.render_text()
            dashboard_out.parent.mkdir(parents=True, exist_ok=True)
            dashboard_out.write_text(text + "\n", encoding="utf-8")
        except Exception as exc:
            raise ServiceError(
                "Daily create_dashboard stage failed",
                cause=exc,
            ) from exc
        stages_run.append("create_dashboard")
        published.append(
            self._publish(
                DashboardUpdated(
                    path=str(dashboard_out),
                    profile_count=profile_count,
                )
            )
        )

        # 7. Email Report (future)
        email_result = self._run_email_report(
            excel_path=excel_written,
            dashboard_path=dashboard_out,
            profile_count=profile_count,
            files_imported=len(summaries),
            errors=errors,
        )
        stages_run.append("email_report")
        if (
            email_result.attempted
            and not email_result.sent
            and not email_result.skipped
        ):
            errors.append(email_result.message)

        result = DailyResult(
            stages_run=tuple(stages_run),
            import_folder=str(inbox),
            files_detected=len(candidates),
            files_new=len(new_files),
            files_imported=len(summaries),
            created=created,
            updated=updated,
            skipped=skipped,
            profile_count=profile_count,
            rescored=rescored,
            images_extracted=image_count,
            excel_path=str(excel_written),
            dashboard_path=str(dashboard_out),
            email_sent=email_result.sent,
            email_skipped=email_result.skipped,
            email_message=email_result.message,
            import_summaries=tuple(summaries),
            events=tuple(published),
            errors=tuple(errors),
        )
        logger.info(
            "Daily pipeline done: folder=%s detected=%d new=%d imported=%d "
            "created=%d updated=%d excel=%s dashboard=%s email=%s events=%s",
            result.import_folder,
            result.files_detected,
            result.files_new,
            result.files_imported,
            result.created,
            result.updated,
            result.excel_path,
            result.dashboard_path,
            "sent" if result.email_sent else "skipped",
            " → ".join(result.event_names),
        )
        return result

    def _run_email_report(
        self,
        *,
        excel_path: Path,
        dashboard_path: Path,
        profile_count: int,
        files_imported: int,
        errors: Sequence[str],
    ) -> EmailReportResult:
        body = (
            "Profile Intelligence Platform — Daily Report\n"
            f"Profiles: {profile_count}\n"
            f"Files imported: {files_imported}\n"
            f"Excel: {excel_path}\n"
            f"Dashboard: {dashboard_path}\n"
        )
        if errors:
            body += "Issues:\n" + "\n".join(f"- {item}" for item in errors) + "\n"
        try:
            return self._email.send_daily_report(
                subject="PIP Daily Report",
                body=body,
                attachments=(excel_path, dashboard_path),
            )
        except ServiceError as exc:
            return EmailReportResult(
                attempted=True,
                sent=False,
                skipped=False,
                message=str(exc),
            )

    def _publish(self, event: DomainEvent) -> DomainEvent:
        if self._events is not None:
            self._events.publish(event)
        else:
            logger.debug("Event (no bus): %s", event.name)
        return event

    def _extract_images(self, profile_ids: Sequence[int]) -> int:
        if self._image_pipeline is not None and profile_ids:
            result = self._image_pipeline.process_profiles(profile_ids)
            return result.processed

        photo_count = 0
        if self._photos is not None:
            for profile_id in profile_ids:
                photo_count += len(self._photos.list_for_profile(profile_id))

        media_count = 0
        if self._images is not None:
            media_count = len(self._images.list_all(limit=100_000, offset=0))
        return max(photo_count, media_count)

    def _import_files(
        self,
        files: Sequence[Path],
    ) -> tuple[list[ImportSummary], list[str]]:
        if not files:
            logger.info("Daily import: no new files to import")
            return [], []

        summaries: list[ImportSummary] = []
        errors: list[str] = []
        for path in files:
            try:
                summary = self._import.import_path(path)
                summaries.append(summary)
                errors.extend(summary.errors)
                # Fingerprint after a completed import attempt so unchanged
                # files are skipped on the next Daily run.
                self._ledger.mark_imported(path)
            except Exception as exc:
                message = f"{path}: {exc}"
                errors.append(message)
                logger.exception("Daily import failed for %s", path)
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
