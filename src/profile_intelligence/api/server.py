"""ASGI server launcher for FastAPI + React."""

from __future__ import annotations

import webbrowser

from profile_intelligence.api.context import ApiContext
from profile_intelligence.api.fastapi_app import create_fastapi_app
from profile_intelligence.core.logging import get_logger

logger = get_logger(__name__)


def serve_fastapi(
    api_context: ApiContext,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    open_browser: bool = True,
    serve_spa: bool = True,
) -> None:
    """Serve React + FastAPI until interrupted."""
    import uvicorn

    app = create_fastapi_app(api_context, serve_spa=serve_spa)
    url = f"http://{host}:{port}/"
    logger.info("FastAPI + React listening on %s", url)
    print("Profile Intelligence Platform — React + FastAPI")
    print(f"Open: {url}")
    print(f"API:  {url.rstrip('/')}/api/…")
    print(f"Docs: {url.rstrip('/')}/api/docs")
    print("Press Ctrl+C to stop.")
    if open_browser:
        try:
            webbrowser.open(url)
        except (OSError, webbrowser.Error):
            logger.debug("Could not open system browser", exc_info=True)
    uvicorn.run(app, host=host, port=port, log_level="info")


__all__ = ["serve_fastapi"]
