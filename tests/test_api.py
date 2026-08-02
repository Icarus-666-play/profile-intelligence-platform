"""Tests for the local JSON REST API."""

from __future__ import annotations

import base64
import json
from io import BytesIO
from pathlib import Path
from typing import Any

from profile_intelligence.api import API_ROUTES, ApiApp, ApiContext
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
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry


def _api_context(tmp_path: Path) -> tuple[ApiContext, ApplicationService, Any]:
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
        database=container.resolve(Database),
    )
    return ctx, app, container


def _request(
    app: ApiApp,
    method: str,
    path: str,
    *,
    query: str = "",
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    payload = b""
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
    status_holder: dict[str, str] = {}

    def start_response(status: str, _headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(payload)),
        "wsgi.input": BytesIO(payload),
    }
    chunks = list(app(environ, start_response))
    code = int(status_holder["status"].split()[0])
    return code, json.loads(b"".join(chunks).decode("utf-8"))


def test_api_routes_catalog() -> None:
    methods_paths = {(method, path) for method, path in API_ROUTES}
    assert ("POST", "/api/import/url") in methods_paths
    assert ("POST", "/api/import/files") in methods_paths
    assert ("GET", "/api/profiles") in methods_paths
    assert ("GET", "/api/profiles/{id}") in methods_paths
    assert ("POST", "/api/compare") in methods_paths
    assert ("GET", "/api/dashboard") in methods_paths
    assert ("GET", "/api/analytics") in methods_paths
    assert ("GET", "/api/plugins") in methods_paths
    assert ("POST", "/api/plugins/reload") in methods_paths


def test_profiles_dashboard_plugins_analytics(temp_root: Path) -> None:
    ctx, app_svc, container = _api_context(temp_root)
    try:
        repo = container.resolve(IProfileRepository)
        created, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Ada Lovelace",
                email="ada@example.com",
                source="api-test",
                score=88,
            )
        )
        assert created.id is not None

        api = ApiApp(ctx)
        code, payload = _request(api, "GET", "/api/profiles")
        assert code == 200
        assert payload["total"] >= 1
        assert payload["items"][0]["display_name"] == "Ada Lovelace"

        code, payload = _request(api, "GET", f"/api/profiles/{created.id}")
        assert code == 200
        assert payload["id"] == created.id

        code, payload = _request(api, "GET", "/api/dashboard")
        assert code == 200
        assert payload["total_profiles"] >= 1

        code, payload = _request(api, "GET", "/api/analytics")
        assert code == 200
        assert "duplicates" in payload
        assert "classification" in payload

        code, payload = _request(api, "GET", "/api/plugins")
        assert code == 200
        assert payload["count"] >= 1
        names = {item["name"] for item in payload["items"]}
        assert "csv" in names
    finally:
        app_svc.shutdown()


def test_import_files_compare_reload(temp_root: Path) -> None:
    ctx, app_svc, container = _api_context(temp_root)
    try:
        api = ApiApp(ctx)
        csv_bytes = b"name,email\nGrace Hopper,grace@example.com\n"
        code, payload = _request(
            api,
            "POST",
            "/api/import/files",
            body={
                "files": [
                    {
                        "name": "grace.csv",
                        "content_base64": base64.b64encode(csv_bytes).decode("ascii"),
                    }
                ],
                "plugin": "csv",
                "source": "api-upload",
            },
        )
        assert code == 200
        assert payload["count"] == 1
        assert payload["imports"][0]["created"] >= 1

        repo = container.resolve(IProfileRepository)
        left, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Compare Left",
                external_id="cmp-left",
                email="left@example.com",
                source="a",
            )
        )
        right, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Compare Right",
                external_id="cmp-right",
                email="right@example.com",
                source="b",
            )
        )
        assert left.id is not None and right.id is not None

        code, comparison = _request(
            api,
            "POST",
            "/api/compare",
            body={"left_id": left.id, "right_id": right.id},
        )
        assert code == 200
        assert "fields" in comparison

        before = len(ctx.importers.list_plugins())
        code, reloaded = _request(api, "POST", "/api/plugins/reload", body={})
        assert code == 200
        assert reloaded["reloaded"] == before
    finally:
        app_svc.shutdown()


def test_api_404(temp_root: Path) -> None:
    ctx, app_svc, _container = _api_context(temp_root)
    try:
        api = ApiApp(ctx)
        code, payload = _request(api, "GET", "/api/missing")
        assert code == 404
        assert "error" in payload
    finally:
        app_svc.shutdown()
