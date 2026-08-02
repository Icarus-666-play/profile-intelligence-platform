"""Nightly automation workflow.

Business reaction chain:

```
ProfileImported
 ↓
ScoreCalculated
 ↓
ImagesExtracted
 ↓
ExcelExported
 ↓
DashboardUpdated
```

Operational stages:

```
Import every night
 ↓
Update database
 ↓
Recalculate scores
 ↓
Extract images
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
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.infrastructure.media.image_repository import ImageRepository

logger = get_logger(__name__)

NIGHTLY_STAGES: tuple[str, ...] = (
    "import",
    "update_database",
    "recalculate_scores",
    "extract_images",
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
    images_extracted: int = 0
    excel_path: str | None = None
    dashboard_path: str | None = None
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
        *,
        event_bus: IEventBus | None = None,
        photo_repository: IPhotoRepository | None = None,
        image_repository: ImageRepository | None = None,
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

    def run(
        self,
        *,
        import_dir: PathLike | None = None,
        excel_path: PathLike | None = None,
        dashboard_path: PathLike | None = None,
        rescore: bool | None = None,
        recursive: bool | None = None,
    ) -> NightlyResult:
        """Execute all nightly stages and publish workflow events."""
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

        if self._events is not None:
            self._events.clear_history()

        logger.info(
            "Nightly pipeline start: inbox=%s stages=%s events=%s",
            inbox,
            " → ".join(NIGHTLY_STAGES),
            " → ".join(cls.__name__ for cls in WORKFLOW_EVENT_CHAIN),
        )
        errors: list[str] = []
        stages_run: list[str] = []
        published: list[DomainEvent] = []

        # 1. Import every night → ProfileImported
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
            profile_ids = tuple(
                int(row.id)
                for row in self._profiles.list_profiles(limit=100_000, offset=0)
                if row.id is not None
            )
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

        # 3. Recalculate scores → ScoreCalculated
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
        published.append(
            self._publish(
                ScoreCalculated(profile_ids=profile_ids, rescored=rescored)
            )
        )

        # 4. Extract images → ImagesExtracted
        try:
            image_count = self._extract_images(profile_ids)
        except Exception as exc:
            raise ServiceError(
                "Nightly extract_images stage failed",
                cause=exc,
            ) from exc
        stages_run.append("extract_images")
        published.append(
            self._publish(
                ImagesExtracted(
                    profile_ids=profile_ids,
                    image_count=image_count,
                )
            )
        )

        # 5. Generate Excel report → ExcelExported
        try:
            excel_written = self._profiles.export_excel(excel_out)
        except Exception as exc:
            raise ServiceError(
                "Nightly generate_excel_report stage failed",
                cause=exc,
            ) from exc
        stages_run.append("generate_excel_report")
        published.append(
            self._publish(
                ExcelExported(
                    path=str(excel_written),
                    profile_count=profile_count,
                )
            )
        )

        # 6. Export dashboard → DashboardUpdated
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
        published.append(
            self._publish(
                DashboardUpdated(
                    path=str(dashboard_out),
                    profile_count=profile_count,
                )
            )
        )

        result = NightlyResult(
            stages_run=tuple(stages_run),
            files_imported=len(summaries),
            created=created,
            updated=updated,
            skipped=skipped,
            profile_count=profile_count,
            rescored=rescored,
            images_extracted=image_count,
            excel_path=str(excel_written),
            dashboard_path=str(dashboard_out),
            import_summaries=tuple(summaries),
            events=tuple(published),
            errors=tuple(errors),
        )
        logger.info(
            "Nightly pipeline done: files=%d created=%d updated=%d "
            "rescored=%d images=%d excel=%s dashboard=%s events=%s",
            result.files_imported,
            result.created,
            result.updated,
            result.rescored,
            result.images_extracted,
            result.excel_path,
            result.dashboard_path,
            " → ".join(result.event_names),
        )
        return result

    def _publish(self, event: DomainEvent) -> DomainEvent:
        if self._events is not None:
            self._events.publish(event)
        else:
            logger.debug("Event (no bus): %s", event.name)
        return event

    def _extract_images(self, profile_ids: Sequence[int]) -> int:
        """Inventory images for profiles (photos + stored media assets)."""
        photo_count = 0
        if self._photos is not None:
            for profile_id in profile_ids:
                photo_count += len(self._photos.list_for_profile(profile_id))

        media_count = 0
        if self._images is not None:
            media_count = len(self._images.list_all(limit=100_000, offset=0))

        total = max(photo_count, media_count)
        logger.info(
            "Nightly extract_images: photos=%d media_assets=%d total=%d",
            photo_count,
            media_count,
            total,
        )
        return total

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
