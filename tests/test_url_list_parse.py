"""URL list parsing for multi-URL import."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from profile_intelligence.api.routes import _is_placeholder_url, _url_import_list
from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AppConfig


def test_placeholder_urls_are_skipped(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    config = container.resolve(AppConfig)
    assert _is_placeholder_url("https://...")
    assert _is_placeholder_url("https://")
    urls, plugin, source = _url_import_list(
        SimpleNamespace(config=config),  # type: ignore[arg-type]
        {
            "urls": [
                "https://...",
                "https://example.com/a.csv",
                "https://example.com/a.csv",
                "https://example.com/b.csv",
            ],
            "plugin": "csv",
            "source": "batch",
        },
    )
    assert urls == [
        "https://example.com/a.csv",
        "https://example.com/b.csv",
    ]
    assert plugin == "csv"
    assert source == "batch"
