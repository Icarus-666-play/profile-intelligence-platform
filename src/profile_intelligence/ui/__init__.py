"""Milestone 2 Dashboard UI — local multi-page presentation layer.

Navigation::

    Profile Intelligence Platform
    Dashboard
    Search
    Import
    Compare
    Reports
    Settings
    Plugins
    Logs
    About
"""

from __future__ import annotations

from profile_intelligence.ui.app import DashboardUI
from profile_intelligence.ui.context import UiContext
from profile_intelligence.ui.navigation import NAV_ITEMS, NavItem
from profile_intelligence.ui.server import serve_ui

__all__ = [
    "NAV_ITEMS",
    "DashboardUI",
    "NavItem",
    "UiContext",
    "serve_ui",
]
