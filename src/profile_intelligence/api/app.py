"""WSGI application for the local JSON REST API."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any, Protocol
from urllib.parse import unquote

from profile_intelligence.api.context import ApiContext
from profile_intelligence.api.http import (
    ApiError,
    error_response,
    json_response,
    parse_json_body,
    query_params,
)
from profile_intelligence.api.routes import dispatch
from profile_intelligence.core.exceptions import PipError
from profile_intelligence.core.logging import get_logger

logger = get_logger(__name__)

StartResponse = Callable[[str, list[tuple[str, str]]], Any]


class _WsgiApp(Protocol):
    def __call__(
        self,
        environ: dict[str, Any],
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        """WSGI application callable."""

API_ROUTES: tuple[tuple[str, str], ...] = (
    ("POST", "/api/import/url"),
    ("POST", "/api/import/url/preview"),
    ("GET", "/api/import/activity"),
    ("POST", "/api/import/files"),
    ("GET", "/api/profiles"),
    ("GET", "/api/profiles/{id}"),
    ("POST", "/api/compare"),
    ("GET", "/api/dashboard"),
    ("GET", "/api/analytics"),
    ("GET", "/api/plugins"),
    ("POST", "/api/plugins/reload"),
    ("GET", "/api/settings"),
    ("GET", "/api/backups"),
    ("POST", "/api/backups"),
    ("GET", "/api/auth/status"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/guest"),
    ("POST", "/api/auth/logout"),
    ("GET", "/api/auth/session"),
)


class ApiApp:
    """Local JSON API mounted under ``/api``."""

    def __init__(self, context: ApiContext) -> None:
        self._ctx = context

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = unquote(str(environ.get("PATH_INFO", "/") or "/"))

        if method == "OPTIONS":
            return json_response(start_response, {"ok": True})

        try:
            body: dict[str, Any] = {}
            if method in {"POST", "PUT", "PATCH"}:
                body = parse_json_body(environ)
            status, payload = dispatch(
                self._ctx,
                method=method,
                path=path,
                query=query_params(environ),
                body=body,
            )
            return json_response(start_response, payload, status=status)
        except ApiError as exc:
            return error_response(
                start_response, exc.message, status=exc.status
            )
        except PipError as exc:
            logger.warning("API domain error on %s %s: %s", method, path, exc)
            return error_response(start_response, str(exc), status=400)
        except Exception as exc:
            logger.exception("API unexpected error on %s %s", method, path)
            return error_response(
                start_response,
                f"unexpected error: {exc}",
                status=500,
            )


class CombinedApp:
    """Dispatch ``/api/*`` to :class:`ApiApp`, everything else to UI."""

    def __init__(self, ui: _WsgiApp, api: ApiApp) -> None:
        self._ui = ui
        self._api = api

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        path = unquote(str(environ.get("PATH_INFO", "/") or "/"))
        if path == "/api" or path.startswith("/api/"):
            return self._api(environ, start_response)
        return self._ui(environ, start_response)


__all__ = ["API_ROUTES", "ApiApp", "CombinedApp"]
