"""Built React SPA assets (``web/dist``) served by FastAPI."""

from __future__ import annotations

from pathlib import Path

DIST_DIR = Path(__file__).resolve().parent / "dist"

__all__ = ["DIST_DIR"]
