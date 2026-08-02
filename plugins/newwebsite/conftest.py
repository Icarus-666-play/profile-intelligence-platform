"""Local fixtures for NewWebsite plugin tests (standalone collection)."""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from profile_intelligence.core.logging import reset_logging

_ROOT = Path(__file__).resolve().parents[2]
for candidate in (_ROOT, _ROOT / "src", _ROOT / "plugins"):
    text = str(candidate)
    if text not in sys.path:
        sys.path.insert(0, text)


@pytest.fixture(autouse=True)
def _reset_logging_state() -> Iterator[None]:
    reset_logging()
    yield
    reset_logging()
