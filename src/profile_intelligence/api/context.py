"""Shared dependencies for the local REST API.

Context construction lives in :func:`profile_intelligence.bootstrap.create_application_context`.

Typical wiring::

    from profile_intelligence.bootstrap import create_application_context
    from profile_intelligence.api.fastapi_app import create_fastapi_app

    ctx = create_application_context()
    app = create_fastapi_app(ctx)
"""

from __future__ import annotations

from dataclasses import dataclass

from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.daily_pipeline import DailyPipeline
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.container import Container
from profile_intelligence.core.types import PathLike
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.infrastructure.analysis import AnalysisService
from profile_intelligence.infrastructure.auth import LocalAuthService
from profile_intelligence.infrastructure.backups import BackupService
from profile_intelligence.infrastructure.dashboard import (
    DashboardService,
    ReportsAnalyticsService,
)
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.download import DocumentDownloader
from profile_intelligence.infrastructure.importers.daily_activity import (
    DailyActivityStore,
)
from profile_intelligence.infrastructure.importers.import_activity import (
    ImportActivityStore,
)
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry


@dataclass(slots=True)
class ApiContext:
    """Services available to REST handlers."""

    config: AppConfig
    profiles: ProfileService
    repository: IProfileRepository
    imports: ImportService
    import_flow: ImportFlow
    compare: CompareService
    dashboard: DashboardService
    analysis: AnalysisService
    importers: ImporterRegistry
    downloader: DocumentDownloader | None = None
    auth: LocalAuthService | None = None
    import_activity: ImportActivityStore | None = None
    database: Database | None = None
    reports_analytics: ReportsAnalyticsService | None = None
    backups: BackupService | None = None
    daily: DailyPipeline | None = None
    daily_activity: DailyActivityStore | None = None


def create_api_context(
    *,
    container: Container | None = None,
    config_path: PathLike | None = None,
    root_dir: PathLike | None = None,
    start: bool = True,
) -> ApiContext:
    """Backward-compatible alias for :func:`create_application_context`."""
    from profile_intelligence.bootstrap import create_application_context

    return create_application_context(
        container=container,
        config_path=config_path,
        root_dir=root_dir,
        start=start,
    )


__all__ = ["ApiContext", "create_api_context"]
