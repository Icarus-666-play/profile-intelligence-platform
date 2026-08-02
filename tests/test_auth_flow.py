"""Tests for Login (optional) → Home → Dashboard auth API."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from profile_intelligence.api import ApiContext, create_fastapi_app
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.import_flow import ImportFlow
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AppConfig, AuthSection
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.infrastructure.analysis import AnalysisService
from profile_intelligence.infrastructure.auth import LocalAuthService
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry


def _ctx(
    tmp_path: Path,
    *,
    auth: AuthSection | None = None,
) -> tuple[ApiContext, ApplicationService]:
    container = build_container(root_dir=tmp_path)
    app = container.resolve(ApplicationService)
    app.start()
    config = container.resolve(AppConfig)
    if auth is not None:
        object.__setattr__(config, "auth", auth)
        auth_service = LocalAuthService(config)
    else:
        auth_service = container.resolve(LocalAuthService)
    from profile_intelligence.infrastructure.dashboard import ReportsAnalyticsService
    from profile_intelligence.infrastructure.database.connection import Database

    ctx = ApiContext(
        config=config,
        profiles=container.resolve(ProfileService),
        repository=container.resolve(IProfileRepository),
        imports=container.resolve(ImportService),
        import_flow=container.resolve(ImportFlow),
        compare=container.resolve(CompareService),
        dashboard=container.resolve(DashboardService),
        analysis=container.resolve(AnalysisService),
        importers=container.resolve(ImporterRegistry),
        auth=auth_service,
        database=container.resolve(Database),
        reports_analytics=container.resolve(ReportsAnalyticsService),
    )
    return ctx, app


def test_auth_guest_continue_default(temp_root: Path) -> None:
    ctx, app_svc = _ctx(temp_root)
    try:
        client = TestClient(create_fastapi_app(ctx, serve_spa=False))
        status = client.get("/api/auth/status")
        assert status.status_code == 200
        payload = status.json()
        assert payload["enabled"] is False
        assert payload["allow_guest"] is True
        assert payload["flow"] == ["login", "home", "dashboard"]

        guest = client.post("/api/auth/guest", json={})
        assert guest.status_code == 200
        session = guest.json()["session"]
        assert session["guest"] is True
        assert guest.json()["next"] == "/"

        resolved = client.get(f"/api/auth/session?token={session['token']}")
        assert resolved.status_code == 200
        assert resolved.json()["session"]["username"] == "guest"
    finally:
        app_svc.shutdown()


def test_auth_login_when_enabled(temp_root: Path) -> None:
    ctx, app_svc = _ctx(
        temp_root,
        auth=AuthSection(
            enabled=True,
            allow_guest=True,
            username="operator",
            password="secret",  # noqa: S106
        ),
    )
    try:
        client = TestClient(create_fastapi_app(ctx, serve_spa=False))
        bad = client.post(
            "/api/auth/login",
            json={"username": "operator", "password": "nope"},
        )
        assert bad.status_code == 401

        ok = client.post(
            "/api/auth/login",
            json={"username": "operator", "password": "secret"},
        )
        assert ok.status_code == 200
        assert ok.json()["session"]["authenticated"] is True
        assert ok.json()["next"] == "/"
    finally:
        app_svc.shutdown()
