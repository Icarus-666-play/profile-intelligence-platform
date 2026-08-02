"""Tests for the application launcher."""

from __future__ import annotations

import pytest

from profile_intelligence.main import build_parser, main


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "Profile Intelligence Platform" in capsys.readouterr().out


def test_help(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
    assert "local-first" in capsys.readouterr().out


def test_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.config_path is None
    assert args.migrate_only is False
    assert args.list_importers is False
