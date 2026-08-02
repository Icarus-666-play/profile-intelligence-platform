"""Tests for workflow domain events and the in-memory event bus."""

from __future__ import annotations

from profile_intelligence.application.events import InMemoryEventBus
from profile_intelligence.domain.events import (
    WORKFLOW_EVENT_CHAIN,
    DashboardUpdated,
    ExcelExported,
    ImagesExtracted,
    ProfileImported,
    ScoreCalculated,
)


def test_workflow_event_chain_order() -> None:
    assert tuple(cls.__name__ for cls in WORKFLOW_EVENT_CHAIN) == (
        "ProfileImported",
        "ScoreCalculated",
        "ImagesExtracted",
        "ExcelExported",
        "DashboardUpdated",
    )


def test_event_bus_publishes_and_records_history() -> None:
    bus = InMemoryEventBus()
    seen: list[str] = []
    bus.subscribe(ProfileImported, lambda event: seen.append(event.name))
    bus.subscribe(ScoreCalculated, lambda event: seen.append(event.name))

    bus.publish(ProfileImported(created=2, updated=1))
    bus.publish(ScoreCalculated(rescored=3))

    assert seen == ["ProfileImported", "ScoreCalculated"]
    assert [event.name for event in bus.history()] == [
        "ProfileImported",
        "ScoreCalculated",
    ]


def test_event_payloads() -> None:
    imported = ProfileImported(
        profile_ids=(1, 2),
        created=2,
        updated=0,
        source="eurogirls",
    )
    assert imported.name == "ProfileImported"
    assert imported.profile_ids == (1, 2)
    assert imported.event_id

    scored = ScoreCalculated(profile_ids=(1,), rescored=1)
    images = ImagesExtracted(profile_ids=(1,), image_count=4)
    excel = ExcelExported(path="exports/out.xlsx", profile_count=2)
    dash = DashboardUpdated(path="exports/dash.txt", profile_count=2)

    assert scored.rescored == 1
    assert images.image_count == 4
    assert excel.path.endswith("out.xlsx")
    assert dash.profile_count == 2
