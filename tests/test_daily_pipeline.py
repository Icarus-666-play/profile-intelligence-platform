"""Tests for the Daily automation workflow."""

from __future__ import annotations

from pathlib import Path

import profile_intelligence.main as main_module
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.daily_pipeline import (
    DAILY_STAGES,
    DailyPipeline,
)
from profile_intelligence.bootstrap import build_container
from profile_intelligence.main import build_parser, main


def test_daily_stages_order() -> None:
    assert DAILY_STAGES == (
        "every_day",
        "check_import_queue",
        "import",
        "statistics",
        "excel",
        "dashboard",
    )


def test_daily_pipeline_end_to_end_and_skips_seen_files(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    inbox = temp_root / "data" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "people.csv").write_text(
        "name,email,organization\n"
        "Ada Lovelace,ada@example.com,Analytical Engines\n"
        "Grace Hopper,grace@example.com,US Navy\n",
        encoding="utf-8",
    )
    (inbox / "notes.txt").write_text("ignore me\n", encoding="utf-8")

    pipeline = container.resolve(DailyPipeline)
    first = pipeline.run()
    assert first.stages_run == DAILY_STAGES
    assert first.files_detected == 1
    assert first.files_new == 1
    assert first.files_imported == 1
    assert first.created == 2
    assert first.profile_count == 2
    assert first.email_skipped is True
    assert first.event_names == (
        "ProfileImported",
        "ScoreCalculated",
        "ImagesExtracted",
        "ExcelExported",
        "DashboardUpdated",
    )
    assert first.excel_path is not None
    assert Path(first.excel_path).is_file()
    assert first.dashboard_path is not None
    assert "Profiles: 2" in Path(first.dashboard_path).read_text(encoding="utf-8")
    assert first.success

    second = pipeline.run()
    assert second.files_detected == 1
    assert second.files_new == 0
    assert second.files_imported == 0
    assert second.created == 0
    assert second.profile_count == 2
    assert second.success

    app.shutdown()


def test_parser_daily_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "daily",
            "--import-dir",
            "inbox",
            "--excel-output",
            "out.xlsx",
            "--dashboard-output",
            "dash.txt",
            "--no-rescore",
            "--recursive",
            "--force-all-files",
        ]
    )
    assert args.command == "daily"
    assert args.import_dir == "inbox"
    assert args.excel_output == "out.xlsx"
    assert args.dashboard_output == "dash.txt"
    assert args.no_rescore is True
    assert args.recursive is True
    assert args.force_all_files is True


def test_cli_daily(
    temp_root: Path,
    monkeypatch: object,
    capsys: object,
) -> None:
    inbox = temp_root / "data" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "one.csv").write_text(
        "name,email\nAlan Turing,alan@example.com\n",
        encoding="utf-8",
    )

    original = build_container

    def _build(*args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        kwargs.setdefault("root_dir", temp_root)
        return original(*args, **kwargs)

    monkeypatch.setattr(main_module, "build_container", _build)  # type: ignore[attr-defined]
    assert main(["daily"]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Daily pipeline complete" in out
    assert "check_import_queue" in out
    assert "statistics" in out
    assert "email:" in out
    assert (temp_root / "exports" / "daily-profiles.xlsx").is_file()
    assert (temp_root / "exports" / "daily-dashboard.txt").is_file()
