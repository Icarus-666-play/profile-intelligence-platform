"""Local HTTP server for the Dashboard UI."""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from wsgiref.simple_server import make_server

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
) -> None:
    """Serve the Dashboard UI until interrupted."""
    app = DashboardUI(context)
    httpd = make_server(host, port, app)
    url = f"http://{host}:{port}/"
    logger.info("Dashboard UI listening on %s", url)
    print("Profile Intelligence Platform — Dashboard UI")
    print(f"Open: {url}")
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
