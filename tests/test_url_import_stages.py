"""URL import pipeline stage helpers."""

from __future__ import annotations

from profile_intelligence.domain.value_objects.url_import import (
    URL_IMPORT_STAGES,
    stage_percent,
    stages_through,
)


def test_url_import_stage_order() -> None:
    assert URL_IMPORT_STAGES == (
        "url",
        "downloader",
        "snapshot",
        "parser",
        "extractor",
        "normalizer",
        "validator",
        "preview",
        "import",
    )
    assert stages_through("snapshot") == (
        "url",
        "downloader",
        "snapshot",
    )
    assert stage_percent("url") == 0
    assert stage_percent("import") == 100
    assert 0 < stage_percent("parser") < 100
