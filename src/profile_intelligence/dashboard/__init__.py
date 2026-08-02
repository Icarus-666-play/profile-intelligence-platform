"""Desktop dashboard / presentation layer.

Milestone 1 ships a console dashboard via :class:`DashboardService`.
A Windows-first graphical UI is planned for Milestone 2.
"""

from __future__ import annotations

from profile_intelligence.dashboard.service import DashboardService, DashboardSnapshot

__all__ = ["DashboardService", "DashboardSnapshot"]
