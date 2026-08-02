"""Shared dependencies for the local REST API."""

from __future__ import annotations

from dataclasses import dataclass

from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.daily_pipeline import DailyPipeline
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.core.config import AppConfig
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


__all__ = ["ApiContext"]
