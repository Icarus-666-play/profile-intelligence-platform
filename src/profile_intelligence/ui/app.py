"""WSGI application for the Profile Intelligence Platform Dashboard UI."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import unquote

from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.layout import read_static
from profile_intelligence.ui.pages import (
    about,
    compare,
    dashboard,
    import_page,
    logs,
    plugins,
    reports,
    search,
    settings,
)

StartResponse = Callable[[str, list[tuple[str, str]]], Any]


class DashboardUI:
    """Local multi-page Dashboard UI backed by application services."""

    def __init__(self, context: UiContext) -> None:
        self._ctx = context

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = unquote(str(environ.get("PATH_INFO", "/") or "/"))
        query = str(environ.get("QUERY_STRING", "") or "")

        if path.startswith("/static/"):
            return self._static(path, start_response)

        if method == "GET":
            return self._get(path, query, start_response)
        if method == "POST":
            return self._post(path, environ, start_response)
        return self._text(start_response, "405 Method Not Allowed", status="405 Method Not Allowed")

    def _get(
        self,
        path: str,
        query: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        ctx = self._ctx
        if path in {"/", "/dashboard"}:
            return self._html(start_response, dashboard.render(ctx))
        if path == "/search":
            return self._html(start_response, search.render(ctx, query_string=query))
        if path == "/import":
            return self._html(start_response, import_page.render(ctx))
        if path == "/compare":
            return self._html(start_response, compare.render(ctx))
        if path == "/reports":
            return self._html(start_response, reports.render(ctx))
        if path == "/settings":
            return self._html(start_response, settings.render(ctx))
        if path == "/plugins":
            return self._html(start_response, plugins.render(ctx))
        if path == "/logs":
            return self._html(start_response, logs.render(ctx))
        if path == "/about":
            return self._html(start_response, about.render(ctx))
        return self._text(start_response, "Not Found", status="404 Not Found")

    def _post(
        self,
        path: str,
        environ: dict[str, Any],
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        body = _read_body(environ)
        if path == "/import":
            form = import_page.parse_form(body)
            return self._html(start_response, import_page.handle_post(self._ctx, form))
        if path == "/compare":
            return self._html(start_response, compare.handle_post(self._ctx, body))
        if path == "/reports":
            return self._html(start_response, reports.handle_post(self._ctx))
        return self._text(start_response, "Not Found", status="404 Not Found")

    def _static(
        self,
        path: str,
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        name = path.removeprefix("/static/")
        if name not in {"styles.css", "app.js"} or "/" in name or "\\" in name:
            return self._text(start_response, "Not Found", status="404 Not Found")
        try:
            payload = read_static(name)
        except OSError:
            return self._text(start_response, "Not Found", status="404 Not Found")
        content_type = (
            "text/css; charset=utf-8"
            if name.endswith(".css")
            else "application/javascript; charset=utf-8"
        )
        start_response(
            "200 OK",
            [
                ("Content-Type", content_type),
                ("Content-Length", str(len(payload))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [payload]

    def _html(self, start_response: StartResponse, document: str) -> Iterable[bytes]:
        payload = document.encode("utf-8")
        start_response(
            "200 OK",
            [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(payload))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [payload]

    def _text(
        self,
        start_response: StartResponse,
        message: str,
        *,
        status: str,
    ) -> Iterable[bytes]:
        payload = message.encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(len(payload))),
            ],
        )
        return [payload]


def _read_body(environ: dict[str, Any]) -> bytes:
    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except (TypeError, ValueError):
        length = 0
    if length <= 0:
        return b""
    stream = environ["wsgi.input"]
    return bytes(stream.read(length))


__all__ = ["DashboardUI"]
