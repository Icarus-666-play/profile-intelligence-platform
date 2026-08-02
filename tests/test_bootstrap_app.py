"""Bootstrap ApiContext + official ASGI entry health checks."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from profile_intelligence.api.fastapi_app import create_fastapi_app
from profile_intelligence.bootstrap import create_application_context


def test_create_application_context_builds_api_context(temp_root: Path) -> None:
    ctx = create_application_context(root_dir=temp_root)
    assert ctx.config is not None
    assert ctx.profiles is not None
    assert ctx.repository is not None
    assert ctx.imports is not None
    assert ctx.import_flow is not None
    assert ctx.compare is not None
    assert ctx.dashboard is not None
    assert ctx.analysis is not None
    assert ctx.importers is not None
    assert ctx.database is not None
    assert ctx.daily is not None
    assert ctx.daily_activity is not None


def test_fastapi_app_starts_and_health_ok(temp_root: Path) -> None:
    ctx = create_application_context(root_dir=temp_root)
    app = create_fastapi_app(ctx, serve_spa=False)
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_official_main_module_exposes_app(temp_root: Path, monkeypatch: object) -> None:
    """``uvicorn profile_intelligence.api.main:app`` resolves an ASGI app."""
    import profile_intelligence.api.main as main_mod

    ctx = create_application_context(root_dir=temp_root)
    monkeypatch.setattr(main_mod, "ctx", ctx)
    monkeypatch.setattr(main_mod, "app", create_fastapi_app(ctx, serve_spa=False))
    client = TestClient(main_mod.app)
    assert client.get("/api/health").json() == {
        "status": "ok",
        "stack": "fastapi",
    }
