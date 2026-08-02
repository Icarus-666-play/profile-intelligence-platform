"""FastAPI factory (compat path for :mod:`profile_intelligence.api.main`).

Typical wiring::

    from profile_intelligence.api.context import create_api_context
    from profile_intelligence.api.fastapi_app import create_fastapi_app

    ctx = create_api_context()
    app = create_fastapi_app(ctx)
"""

from __future__ import annotations

from profile_intelligence.api.main import REACT_DIST, create_app, create_fastapi_app

__all__ = ["REACT_DIST", "create_app", "create_fastapi_app"]
