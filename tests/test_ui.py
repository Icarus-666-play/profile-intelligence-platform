"""Tests for the Milestone 2 Dashboard UI."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.compare_service import CompareService
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AppConfig
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.infrastructure.dashboard import DashboardService
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry
from profile_intelligence.main import build_parser
from profile_intelligence.ui import NAV_ITEMS, DashboardUI, UiContext
from profile_intelligence.ui.navigation import NavItem


def _ui_context(tmp_path: Path) -> tuple[UiContext, ApplicationService, Any]:
    container = build_container(root_dir=tmp_path)
    app = container.resolve(ApplicationService)
    app.start()
    ctx = UiContext(
        config=container.resolve(AppConfig),
        dashboard=container.resolve(DashboardService),
        profiles=container.resolve(ProfileService),
        imports=container.resolve(ImportService),
        compare=container.resolve(CompareService),
        importers=container.resolve(ImporterRegistry),
    )
    return ctx, app, container


def _request(
    app: DashboardUI,
    path: str,
    *,
    method: str = "GET",
    query: str = "",
    body: bytes = b"",
) -> tuple[str, dict[str, str], bytes]:
    status_holder: dict[str, str] = {}
    headers_holder: dict[str, str] = {}

    def start_response(status: str, headers: list[tuple[str, str]]) -> None:
        status_holder["status"] = status
        headers_holder.update(headers)

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": BytesIO(body),
    }
    chunks = list(app(environ, start_response))
    return status_holder["status"], headers_holder, b"".join(chunks)


def test_nav_items_cover_requested_pages() -> None:
    labels = [item.label for item in NAV_ITEMS]
    assert labels == [
        "Dashboard",
        "Search",
        "Import",
        "Compare",
        "Reports",
        "Settings",
        "Plugins",
        "Logs",
        "About",
    ]
    assert all(isinstance(item, NavItem) for item in NAV_ITEMS)


def test_dashboard_ui_pages_render(temp_root: Path) -> None:
    ctx, app_svc, _container = _ui_context(temp_root)
    try:
        ui = DashboardUI(ctx)
        for path in [
            "/",
            "/search",
            "/import",
            "/compare",
            "/reports",
            "/settings",
            "/plugins",
            "/logs",
            "/about",
        ]:
            status, headers, body = _request(ui, path)
            assert status == "200 OK"
            assert "text/html" in headers["Content-Type"]
            text = body.decode("utf-8")
            assert "Profile Intelligence Platform" in text
            assert 'class="nav-list"' in text
    finally:
        app_svc.shutdown()


def test_search_and_compare_flow(temp_root: Path) -> None:
    ctx, app_svc, container = _ui_context(temp_root)
    try:
        repo = container.resolve(IProfileRepository)
        left, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Ada Lovelace",
                external_id="ada-ui-1",
                email="ada@example.com",
                source="site-a",
                score=90,
            )
        )
        right, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Ada Byron",
                external_id="ada-ui-2",
                email="ada@example.com",
                source="site-b",
                score=70,
            )
        )
        assert left.id is not None
        assert right.id is not None

        ui = DashboardUI(ctx)
        status, _, body = _request(ui, "/search", query="q=Ada")
        assert status == "200 OK"
        assert "Ada Lovelace" in body.decode("utf-8")

        payload = f"left={left.id}&right={right.id}".encode()
        status, _, body = _request(
            ui,
            "/compare",
            method="POST",
            body=payload,
        )
        assert status == "200 OK"
        text = body.decode("utf-8")
        assert "difference" in text.lower()
        assert "display_name" in text
    finally:
        app_svc.shutdown()


def test_static_assets(temp_root: Path) -> None:
    ctx, app_svc, _container = _ui_context(temp_root)
    try:
        ui = DashboardUI(ctx)
        status, headers, body = _request(ui, "/static/styles.css")
        assert status == "200 OK"
        assert "text/css" in headers["Content-Type"]
        assert b"--font-display" in body
        status, _, body = _request(ui, "/static/app.js")
        assert status == "200 OK"
        assert b"requestAnimationFrame" in body
    finally:
        app_svc.shutdown()


def test_parser_ui_command() -> None:
    parser = build_parser()
    args = parser.parse_args(["ui", "--port", "9001", "--no-browser"])
    assert args.command == "ui"
    assert args.port == 9001
    assert args.no_browser is True
