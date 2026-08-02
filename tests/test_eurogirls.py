"""Collect EuroGirls Sprint 1 plugin tests via the main test suite."""

from __future__ import annotations

# Re-export plugin package tests so `pytest` (testpaths=tests) runs them.
from eurogirls.tests import *  # noqa: F403
