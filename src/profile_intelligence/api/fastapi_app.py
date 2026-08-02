"""Compatibility shim — prefer :mod:`profile_intelligence.api.main`.

Historical import path for the FastAPI factory. New code should use::

    from profile_intelligence.api.main import create_app
"""

from __future__ import annotations

from profile_intelligence.api.main import REACT_DIST, create_app, create_fastapi_app

__all__ = ["REACT_DIST", "create_app", "create_fastapi_app"]
