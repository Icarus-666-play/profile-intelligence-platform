"""Tests for rich import statistics reporting."""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.import_stats import (
    ImportStats,
    collect_import_stats,
)
from profile_intelligence.bootstrap import build_container
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.value_objects.profile_children import (
    Photo,
    Rate,
    Service,
)


def test_import_stats_render_format() -> None:
    stats = ImportStats(
        profiles=2,
        services=35,
        rates=12,
        images=18,
        duplicates=0,
        execution_seconds=0.84,
    )
    report = stats.render()
    assert report == (
        "Imported:\n"
        "\n"
        "2 profiles\n"
        "\n"
        "35 services\n"
        "\n"
        "12 rates\n"
        "\n"
        "18 images\n"
        "\n"
        "0 duplicates\n"
        "\n"
        "Execution time:\n"
        "\n"
        "0.8 sec"
    )


def test_collect_import_stats_from_draft_children() -> None:
    draft = ProfileDraft(
        display_name="Sophia",
        source="eurogirls",
        rates=(
            Rate(duration="1 hour", price="300"),
            Rate(duration="2 hours", price="500"),
        ),
        services=(Service(name="GFE"), Service(name="Dinner")),
        photos=(
            Photo(original_url="https://example.com/a.jpg", role="main"),
            Photo(original_url="https://example.com/b.jpg"),
            Photo(original_url="https://example.com/c.jpg"),
        ),
    )
    stats = collect_import_stats(drafts=[draft], duplicates=0, profiles=1)
    assert stats.profiles == 1
    assert stats.rates == 2
    assert stats.services == 2
    assert stats.images == 3


def test_collect_import_stats_from_draft_raw_json() -> None:
    draft = ProfileDraft(
        display_name="Sophia",
        source="eurogirls",
        raw_json=(
            '{"rates":[{"duration":"1 hour"},{"duration":"2 hours"}],'
            '"services":[{"name":"GFE"},{"name":"Dinner"}],'
            '"photos":[{"role":"main"},{"role":"gallery"},{"role":"gallery"}]}'
        ),
    )
    stats = collect_import_stats(drafts=[draft], duplicates=0, profiles=1)
    assert stats.profiles == 1
    assert stats.rates == 2
    assert stats.services == 2
    assert stats.images == 3


def test_eurogirls_import_reports_entity_counts(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    from profile_intelligence.infrastructure.importers.registry import (
        ImporterRegistry,
    )

    registry = container.resolve(ImporterRegistry)
    repo_plugins = Path(__file__).resolve().parents[1] / "plugins"
    registry.discover_directory(repo_plugins)

    sample = (
        Path(__file__).resolve().parents[1]
        / "samples"
        / "eurogirls"
        / "sophia_eurogirls.webarchive"
    )
    target = temp_root / "sophia_eurogirls.webarchive"
    target.write_bytes(sample.read_bytes())

    summary = container.resolve(ImportService).import_path(
        target,
        plugin_name="eurogirls",
        source="eurogirls",
    )
    assert summary.stats.profiles == 1
    assert summary.stats.services == 4
    assert summary.stats.rates == 3
    assert summary.stats.images == 3
    assert summary.stats.duplicates == 0
    assert summary.stats.execution_seconds >= 0.0
    report = summary.render_report()
    assert "1 profiles" in report
    assert "4 services" in report
    assert "3 rates" in report
    assert "3 images" in report
    assert "0 duplicates" in report
    assert "Execution time:" in report
    app.shutdown()


def test_directory_import_aggregates_stats(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    from profile_intelligence.infrastructure.importers.registry import (
        ImporterRegistry,
    )

    registry = container.resolve(ImporterRegistry)
    repo_plugins = Path(__file__).resolve().parents[1] / "plugins"
    registry.discover_directory(repo_plugins)

    sample = (
        Path(__file__).resolve().parents[1]
        / "samples"
        / "eurogirls"
        / "sophia_eurogirls.webarchive"
    )
    inbox = temp_root / "batch"
    inbox.mkdir()
    (inbox / "one_eurogirls.webarchive").write_bytes(sample.read_bytes())
    (inbox / "two_eurogirls.webarchive").write_bytes(sample.read_bytes())

    summary = container.resolve(ImportService).import_directory(
        inbox,
        plugin_name="eurogirls",
        source="eurogirls",
    )
    # Second file is the same identity → one create + one update.
    assert summary.stats.profiles == 2
    assert summary.stats.services == 8
    assert summary.stats.rates == 6
    assert summary.stats.images == 6
    assert "2 profiles" in summary.render_report()
    app.shutdown()
