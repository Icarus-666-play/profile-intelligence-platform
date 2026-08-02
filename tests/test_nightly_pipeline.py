"""Tests for the nightly automation workflow."""

from __future__ import annotations

from pathlib import Path

import profile_intelligence.main as main_module
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.nightly_pipeline import (
    NIGHTLY_STAGES,
    NightlyPipeline,
)
from profile_intelligence.bootstrap import build_container
from profile_intelligence.main import build_parser, main


def test_nightly_stages_order() -> None:
    assert NIGHTLY_STAGES == (
        "import",
        "update_database",
        "recalculate_scores",
        "generate_excel_report",
        "export_dashboard",
    )


def test_nightly_pipeline_end_to_end(temp_root: Path) -> None:
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

    result = container.resolve(NightlyPipeline).run()
    assert result.stages_run == NIGHTLY_STAGES
    assert result.files_imported == 1
    assert result.created == 2
    assert result.profile_count == 2
    assert result.rescored == 2
    assert result.excel_path is not None
    assert Path(result.excel_path).is_file()
    assert result.dashboard_path is not None
    dashboard = Path(result.dashboard_path)
    assert dashboard.is_file()
    assert "Profiles: 2" in dashboard.read_text(encoding="utf-8")
    assert result.success
    app.shutdown()


def test_parser_nightly_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "nightly",
            "--import-dir",
            "inbox",
            "--excel-output",
            "out.xlsx",
            "--dashboard-output",
            "dash.txt",
            "--no-rescore",
            "--recursive",
        ]
    )
    assert args.command == "nightly"
    assert args.import_dir == "inbox"
    assert args.excel_output == "out.xlsx"
    assert args.dashboard_output == "dash.txt"
    assert args.no_rescore is True
    assert args.recursive is True


def test_cli_nightly(
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
    assert main(["nightly"]) == 0
    out = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "Nightly pipeline complete" in out
    assert "recalculate_scores" in out
    assert (temp_root / "exports" / "nightly-profiles.xlsx").is_file()
    assert (temp_root / "exports" / "nightly-dashboard.txt").is_file()
