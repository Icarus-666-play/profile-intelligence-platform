"""Tests for compare and dashboard services / CLI."""

from __future__ import annotations

from pathlib import Path

from profile_intelligence.bootstrap import build_container
from profile_intelligence.dashboard import DashboardService
from profile_intelligence.main import build_parser, main
from profile_intelligence.services.application import ApplicationService
from profile_intelligence.services.compare_service import CompareService
from profile_intelligence.services.import_service import ImportService
from profile_intelligence.services.profile_service import ProfileService


def _seed_two_profiles(temp_root: Path) -> tuple[int, int]:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    importer = container.resolve(ImportService)

    left = temp_root / "left.csv"
    left.write_text(
        "id,name,email,organization\n"
        "a1,Ada Lovelace,ada@example.com,Analytical Engines\n",
        encoding="utf-8",
    )
    right = temp_root / "right.csv"
    right.write_text(
        "id,name,email,organization\n"
        "a2,Ada Lovelace,ada@example.com,Bletchley\n",
        encoding="utf-8",
    )
    importer.import_path(left, source="csv")
    importer.import_path(right, source="excel")

    profiles = sorted(
        container.resolve(ProfileService).list_profiles(),
        key=lambda row: int(row.id or 0),
    )
    app.shutdown()
    assert len(profiles) == 2
    return int(profiles[0].id), int(profiles[1].id)


def test_compare_profiles(temp_root: Path) -> None:
    left_id, right_id = _seed_two_profiles(temp_root)
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    comparison = container.resolve(CompareService).compare_ids(left_id, right_id)
    assert comparison.left_id == left_id
    assert comparison.right_id == right_id
    diff_fields = {item.field for item in comparison.differences}
    assert "organization" in diff_fields or "source" in diff_fields
    assert any(
        item.field == "display_name" and item.equal for item in comparison.fields
    )
    app.shutdown()


def test_compare_sources(temp_root: Path) -> None:
    _seed_two_profiles(temp_root)
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    lines = container.resolve(CompareService).compare_sources("csv", "excel")
    assert any("Source 'csv'" in line for line in lines)
    assert any("Shared emails: 1" in line for line in lines)
    app.shutdown()


def test_dashboard_snapshot(temp_root: Path) -> None:
    _seed_two_profiles(temp_root)
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()
    text = container.resolve(DashboardService).render_text()
    assert "Profiles: 2" in text
    assert "By source:" in text
    app.shutdown()


def test_parser_primary_commands() -> None:
    parser = build_parser()
    assert parser.parse_args(["migrate"]).command == "migrate"
    assert parser.parse_args(["dashboard"]).command == "dashboard"
    assert parser.parse_args(["export"]).command == "export"
    compare = parser.parse_args(["compare", "1", "2"])
    assert compare.left == "1"
    assert compare.right == "2"
    sources = parser.parse_args(["compare", "--sources", "csv", "excel"])
    assert sources.sources == ["csv", "excel"]
    help_text = parser.format_help()
    assert "pip-app migrate" in help_text
    assert "pip-app compare" in help_text
    assert "pip-app dashboard" in help_text


def test_cli_compare_and_dashboard(
    temp_root: Path,
    monkeypatch,
    capsys,
) -> None:
    left_id, right_id = _seed_two_profiles(temp_root)

    # Point the process at the temp install root used by ConfigManager.
    monkeypatch.chdir(temp_root)
    # Copy is unnecessary: build_container(root_dir=...) isn't used by main().
    # Invoke services through main by monkeypatching build_container.
    from profile_intelligence import main as main_module

    def _build(config_path=None, root_dir=None):
        return build_container(config_path=config_path, root_dir=temp_root)

    monkeypatch.setattr(main_module, "build_container", _build)

    assert main(["compare", str(left_id), str(right_id)]) == 0
    compare_out = capsys.readouterr().out
    assert "Compare" in compare_out
    assert "Differences:" in compare_out

    assert main(["dashboard"]) == 0
    dash_out = capsys.readouterr().out
    assert "Dashboard" in dash_out
    assert "Profiles: 2" in dash_out
