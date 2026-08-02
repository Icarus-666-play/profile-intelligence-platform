"""Shared service context for Dashboard UI pages."""

from __future__ import annotations

from dataclasses import dataclass

from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.core.config import AppConfig
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry


@dataclass(slots=True)
class UiContext:
    """Dependencies resolved once for the local UI process."""

    config: AppConfig
    dashboard: DashboardService
    profiles: ProfileService
    imports: ImportService
    compare: CompareService
    importers: ImporterRegistry
    import_flow: ImportFlow | None = None


__all__ = ["UiContext"]
