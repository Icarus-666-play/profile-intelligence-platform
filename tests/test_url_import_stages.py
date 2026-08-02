"""URL import pipeline stage helpers."""

from __future__ import annotations

from profile_intelligence.domain.value_objects.url_import import (
    URL_IMPORT_STAGES,
    stage_percent,
    stages_through,
)


def test_url_import_stage_order() -> None:
    assert URL_IMPORT_STAGES == (
        "download",
        "parse",
        "preview",
        "import",
        "finished",
    )
    assert stages_through("parse") == ("download", "parse")
    assert stage_percent("download") == 0
    assert stage_percent("finished") == 100
    assert 0 < stage_percent("preview") < 100
