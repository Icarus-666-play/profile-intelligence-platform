"""Local HTTP server for the Dashboard UI (+ JSON API)."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from wsgiref.simple_server import make_server

from profile_intelligence.api.app import ApiApp, CombinedApp
from profile_intelligence.api.context import ApiContext
from profile_intelligence.core.logging import get_logger
from profile_intelligence.ui.app import DashboardUI
from profile_intelligence.ui.context import UiContext

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class UiServerConfig:
    """Bind options for the local Dashboard UI server."""

    host: str = "127.0.0.1"
    port: int = 8765
    open_browser: bool = True


def serve_ui(
    context: UiContext,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    api_context: ApiContext | None = None,
) -> None:
    """Serve the Dashboard UI and ``/api`` JSON routes until interrupted."""
    ui = DashboardUI(context)
    app: Callable[..., Any]
    if api_context is not None:
        app = CombinedApp(ui, ApiApp(api_context))
    else:
        app = ui
    httpd = make_server(host, port, app)
    url = f"http://{host}:{port}/"
    logger.info("Dashboard UI listening on %s", url)
    print("Profile Intelligence Platform — Dashboard UI")
    print(f"Open: {url}")
    if api_context is not None:
        print(f"API:  {url.rstrip('/')}/api/…")
    print("Press Ctrl+C to stop.")
    if open_browser:
        try:
            webbrowser.open(url)
        except (OSError, webbrowser.Error):
            logger.debug("Could not open system browser", exc_info=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard UI stopped.")
    finally:
        httpd.server_close()


__all__ = ["UiServerConfig", "serve_ui"]
