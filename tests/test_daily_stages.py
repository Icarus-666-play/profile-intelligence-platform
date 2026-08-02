"""Daily automation stage helpers."""

from __future__ import annotations

from profile_intelligence.domain.value_objects.daily import (
    DAILY_STAGES,
    stage_percent,
    stages_through,
)


def test_daily_stage_order() -> None:
    assert DAILY_STAGES == (
        "every_day",
        "check_import_queue",
        "import",
        "statistics",
        "excel",
        "dashboard",
    )
    assert stages_through("import") == (
        "every_day",
        "check_import_queue",
        "import",
    )
    assert stage_percent("every_day") == 0
    assert stage_percent("dashboard") == 100
    assert 0 < stage_percent("statistics") < 100
