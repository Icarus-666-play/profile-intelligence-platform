"""Compatibility shim — built-in plugins live under infrastructure.importers.plugins."""

from __future__ import annotations

from profile_intelligence.infrastructure.importers import plugins as _plugins

__all__ = list(getattr(_plugins, "__all__", []))
