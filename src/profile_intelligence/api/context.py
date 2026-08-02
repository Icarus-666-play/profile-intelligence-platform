"""Shared dependencies for the local REST API."""

from __future__ import annotations

from dataclasses import dataclass

from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.core.config import AppConfig
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.infrastructure.analysis import AnalysisService
from profile_intelligence.infrastructure.dashboard import DashboardService
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


__all__ = ["ApiContext"]
