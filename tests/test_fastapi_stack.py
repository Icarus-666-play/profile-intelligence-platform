"""Tests for Browser → React → FastAPI → Application → Repository → SQLite."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from profile_intelligence.api import ApiContext, create_app, create_fastapi_app
from profile_intelligence.api.main import create_app as create_app_from_main
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AppConfig
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.infrastructure.analysis import AnalysisService
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.infrastructure.storage import FileStorage
from profile_intelligence.web import DIST_DIR


def _api_context(tmp_path: Path) -> tuple[ApiContext, ApplicationService]:
    container = build_container(root_dir=tmp_path)
    app = container.resolve(ApplicationService)
    app.start()
    from profile_intelligence.infrastructure.backups import BackupService
    from profile_intelligence.infrastructure.dashboard import ReportsAnalyticsService
    from profile_intelligence.infrastructure.database.connection import Database

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
        database=container.resolve(Database),
        reports_analytics=container.resolve(ReportsAnalyticsService),
        backups=container.resolve(BackupService),
    )
    return ctx, app


def test_file_storage_roots(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    storage = container.resolve(FileStorage)
    storage.ensure_directories()
    assert storage.data_dir.is_dir()
    assert storage.media_dir.is_dir()
    assert storage.inbox_dir.is_dir()
    assert storage.exports_dir.is_dir()
    nested = storage.resolve("inbox/sample.csv")
    assert nested.parent == storage.inbox_dir


def test_api_main_create_app_alias(temp_root: Path) -> None:
    assert create_app is create_fastapi_app
    assert create_app_from_main is create_app
    ctx, app_svc = _api_context(temp_root)
    try:
        app = create_app_from_main(ctx, serve_spa=False)
        client = TestClient(app)
        assert client.get("/api/health").json()["stack"] == "fastapi"
    finally:
        app_svc.shutdown()


def test_create_api_context_and_fastapi_app(temp_root: Path) -> None:
    """Exact wiring used by the FastAPI entry docs."""
    from profile_intelligence.api.context import create_api_context
    from profile_intelligence.api.fastapi_app import create_fastapi_app as build_app

    ctx = create_api_context(root_dir=temp_root)
    app = build_app(ctx, serve_spa=False)
    client = TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert ctx.daily is not None
    assert ctx.database is not None


def test_uvicorn_main_app_entry(
    temp_root: Path, monkeypatch: object
) -> None:
    """``uvicorn profile_intelligence.api.main:app`` resolves a FastAPI app."""
    import profile_intelligence.api.main as main_mod
    from profile_intelligence.api.context import create_api_context

    monkeypatch.setattr(main_mod, "_app", None)
    monkeypatch.setattr(
        main_mod,
        "create_default_app",
        lambda: main_mod.create_app(
            create_api_context(root_dir=temp_root),
            serve_spa=False,
        ),
    )
    loaded = getattr(main_mod, "app")
    client = TestClient(loaded)
    assert client.get("/api/health").json()["stack"] == "fastapi"


def test_fastapi_health_and_dashboard(temp_root: Path) -> None:
    ctx, app_svc = _api_context(temp_root)
    try:
        ctx.repository.upsert_draft(
            ProfileDraft(
                display_name="Ada Lovelace",
                email="ada@example.com",
                source="fastapi-test",
                score=91,
            )
        )
        app = create_app(ctx, serve_spa=False)
        client = TestClient(app)
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["stack"] == "fastapi"

        dashboard = client.get("/api/dashboard")
        assert dashboard.status_code == 200
        assert dashboard.json()["total_profiles"] >= 1

        profiles = client.get("/api/profiles")
        assert profiles.status_code == 200
        assert profiles.json()["total"] >= 1
    finally:
        app_svc.shutdown()


def test_fastapi_serves_react_spa(temp_root: Path) -> None:
    assert (DIST_DIR / "index.html").is_file(), "Run: cd frontend && npm run build"
    ctx, app_svc = _api_context(temp_root)
    try:
        app = create_fastapi_app(ctx, serve_spa=True)
        client = TestClient(app)
        home = client.get("/")
        assert home.status_code == 200
        assert "Profile Intelligence Platform" in home.text
        # Client-side route fallback still returns the SPA shell.
        search = client.get("/search")
        assert search.status_code == 200
        assert "root" in search.text
    finally:
        app_svc.shutdown()
