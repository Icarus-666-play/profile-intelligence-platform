"""FastAPI application — REST surface for the React SPA.

```
Browser
 ↓
React
 ↓
REST API
 ↓
FastAPI
 ↓
Application Layer
 ↓
Repository Layer
 ↓
SQLite
 ↓
File Storage
```

Handlers reuse :mod:`profile_intelligence.api.routes` so WSGI and FastAPI
share one implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from profile_intelligence.api.context import ApiContext
from profile_intelligence.api.http import ApiError
from profile_intelligence.api.routes import (
    auth_guest,
    auth_login,
    auth_logout,
    auth_session,
    auth_status,
    compare_profiles,
    get_analytics,
    get_dashboard,
    get_profile,
    import_files,
    import_url,
    list_plugins,
    list_profiles,
    reload_plugins,
)
from profile_intelligence.core.exceptions import PipError
from profile_intelligence.core.logging import get_logger

logger = get_logger(__name__)

REACT_DIST = (
    Path(__file__).resolve().parent.parent / "web" / "dist"
)


def create_fastapi_app(
    ctx: ApiContext,
    *,
    serve_spa: bool = True,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    """Build the FastAPI app bound to an :class:`ApiContext`."""
    app = FastAPI(
        title="Profile Intelligence Platform",
        version="0.1.0",
        description=(
            "Local-first REST API: React → FastAPI → Application → "
            "Repository → SQLite → File Storage"
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.state.api_context = ctx

    origins = cors_origins or [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8765",
        "http://localhost:8765",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status,
            content={"error": exc.message, "status": exc.status},
        )

    @app.exception_handler(PipError)
    async def _pip_error(_request: Request, exc: PipError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": str(exc), "status": 400},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> Response:
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid request", "status": 400},
            )
        return await request_validation_exception_handler(request, exc)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "stack": "fastapi"}

    @app.post("/api/import/url")
    async def api_import_url(request: Request) -> dict[str, Any]:
        body = await _json_body(request)
        return import_url(ctx, body)

    @app.post("/api/import/files")
    async def api_import_files(request: Request) -> dict[str, Any]:
        body = await _json_body(request)
        return import_files(ctx, body)

    @app.get("/api/profiles")
    def api_list_profiles(
        q: str | None = None,
        limit: int = Query(default=50, ge=1, le=10_000),
        offset: int = Query(default=0, ge=0, le=1_000_000),
    ) -> dict[str, Any]:
        query = {
            "limit": str(limit),
            "offset": str(offset),
        }
        if q is not None:
            query["q"] = q
        return list_profiles(ctx, query)

    @app.get("/api/profiles/{profile_id}")
    def api_get_profile(profile_id: int) -> dict[str, Any]:
        return get_profile(ctx, profile_id)

    @app.post("/api/compare")
    async def api_compare(request: Request) -> dict[str, Any]:
        body = await _json_body(request)
        return compare_profiles(ctx, body)

    @app.get("/api/dashboard")
    def api_dashboard() -> dict[str, Any]:
        return get_dashboard(ctx)

    @app.get("/api/analytics")
    def api_analytics(threshold: str | None = None) -> dict[str, Any]:
        query: dict[str, str] = {}
        if threshold is not None:
            query["threshold"] = threshold
        return get_analytics(ctx, query)

    @app.get("/api/plugins")
    def api_plugins() -> dict[str, Any]:
        return list_plugins(ctx)

    @app.post("/api/plugins/reload")
    async def api_plugins_reload() -> dict[str, Any]:
        return reload_plugins(ctx)

    @app.get("/api/auth/status")
    def api_auth_status() -> dict[str, Any]:
        return auth_status(ctx)

    @app.post("/api/auth/login")
    async def api_auth_login(request: Request) -> dict[str, Any]:
        body = await _json_body(request)
        return auth_login(ctx, body)

    @app.post("/api/auth/guest")
    def api_auth_guest() -> dict[str, Any]:
        return auth_guest(ctx)

    @app.post("/api/auth/logout")
    async def api_auth_logout(request: Request) -> dict[str, Any]:
        body = await _json_body(request)
        return auth_logout(ctx, body)

    @app.get("/api/auth/session")
    def api_auth_session(token: str | None = None) -> dict[str, Any]:
        query: dict[str, str] = {}
        if token:
            query["token"] = token
        return auth_session(ctx, query)

    if serve_spa:
        _mount_react_spa(app)

    return app


def _mount_react_spa(app: FastAPI) -> None:
    """Serve the built React SPA from ``web/dist`` when present."""
    dist = REACT_DIST
    assets = dist / "assets"
    if assets.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=assets),
            name="react-assets",
        )

    index = dist / "index.html"

    @app.get("/")
    def spa_root() -> Response:
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(
            {
                "error": (
                    "React UI not built. Run: cd frontend && npm install "
                    "&& npm run build"
                ),
                "status": 503,
                "api": "/api/health",
            },
            status_code=503,
        )

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str) -> Response:
        if full_path.startswith("api/") or full_path == "api":
            return JSONResponse(
                {"error": f"Not found: GET /{full_path}", "status": 404},
                status_code=404,
            )
        # Prefer real static files from the Vite build (favicon, etc.).
        candidate = (dist / full_path).resolve()
        if candidate.is_file() and (
            candidate == dist.resolve() or dist.resolve() in candidate.parents
        ):
            return FileResponse(candidate)
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(
            {
                "error": "React UI not built",
                "status": 503,
                "api": "/api/health",
            },
            status_code=503,
        )


async def _json_body(request: Request) -> dict[str, Any]:
    """Parse a JSON object body (empty object when no body)."""
    try:
        payload = await request.json()
    except Exception as exc:
        raise ApiError(f"Invalid JSON body: {exc}", status=400) from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ApiError("JSON body must be an object", status=400)
    return payload


__all__ = ["REACT_DIST", "create_fastapi_app"]
