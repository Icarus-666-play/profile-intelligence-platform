"""Daily automation REST API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from profile_intelligence.api import ApiContext, create_fastapi_app
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.daily_pipeline import DailyPipeline
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.bootstrap import build_container
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


def _ctx(tmp_path: Path) -> tuple[ApiContext, ApplicationService]:
    container = build_container(root_dir=tmp_path)
    app = container.resolve(ApplicationService)
    app.start()
    ctx = ApiContext(
        config=container.resolve(AppConfig),
        profiles=container.resolve(ProfileService),
        repository=container.resolve(IProfileRepository),
        imports=container.resolve(ImportService),
        import_flow=container.resolve(ImportFlow),
        compare=container.resolve(CompareService),
        dashboard=container.resolve(DashboardService),
        analysis=container.resolve(AnalysisService),
        importers=container.resolve(ImporterRegistry),
        downloader=container.resolve(DocumentDownloader),
        auth=container.resolve(LocalAuthService),
        import_activity=container.resolve(ImportActivityStore),
        database=container.resolve(Database),
        reports_analytics=container.resolve(ReportsAnalyticsService),
        backups=container.resolve(BackupService),
        daily=container.resolve(DailyPipeline),
        daily_activity=container.resolve(DailyActivityStore),
    )
    return ctx, app


def test_daily_api_get_and_run(temp_root: Path) -> None:
    inbox = temp_root / "data" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "people.csv").write_text(
        "name,email\nAda Lovelace,ada@example.com\n",
        encoding="utf-8",
    )
    ctx, app_svc = _ctx(temp_root)
    try:
        client = TestClient(create_fastapi_app(ctx, serve_spa=False))
        meta = client.get("/api/daily")
        assert meta.status_code == 200
        body = meta.json()
        assert body["pipeline"] == [
            "every_day",
            "check_import_queue",
            "import",
            "statistics",
            "excel",
            "dashboard",
        ]
        assert body["stage_labels"]["check_import_queue"] == "Check Import Queue"

        run = client.post("/api/daily/run", json={})
        assert run.status_code == 200
        result = run.json()
        assert result["success"] is True
        assert result["stages_run"][-1] == "dashboard"
        assert result["created"] >= 1
        assert result["excel_path"]
        assert result["dashboard_path"]

        again = client.get("/api/daily")
        assert again.json()["last_result"]["created"] >= 1
        assert again.json()["progress"]["stage"] == "dashboard"
    finally:
        app_svc.shutdown()
