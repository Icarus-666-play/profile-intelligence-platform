"""Primary application navigation for the Dashboard UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NavItem:
    """One top-level navigation destination."""

    key: str
    label: str
    path: str
    description: str


NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem(
        "dashboard",
        "Dashboard",
        "/",
        "Local overview of profiles and confidence",
    ),
    NavItem(
        "search",
        "Search",
        "/search",
        "Find profiles in the local database",
    ),
    NavItem(
        "import",
        "Import",
        "/import",
        "Import profiles from local files",
    ),
    NavItem(
        "compare",
        "Compare",
        "/compare",
        "Diff two profiles side by side",
    ),
    NavItem(
        "reports",
        "Reports",
        "/reports",
        "Excel exports and report outputs",
    ),
    NavItem(
        "settings",
        "Settings",
        "/settings",
        "Local configuration snapshot",
    ),
    NavItem(
        "plugins",
        "Plugins",
        "/plugins",
        "Discovered importer plugins",
    ),
    NavItem(
        "logs",
        "Logs",
        "/logs",
        "Recent application and import logs",
    ),
    NavItem(
        "about",
        "About",
        "/about",
        "Application identity and version",
    ),
)

NAV_BY_PATH: dict[str, NavItem] = {item.path: item for item in NAV_ITEMS}
NAV_BY_KEY: dict[str, NavItem] = {item.key: item for item in NAV_ITEMS}

__all__ = ["NAV_BY_KEY", "NAV_BY_PATH", "NAV_ITEMS", "NavItem"]
