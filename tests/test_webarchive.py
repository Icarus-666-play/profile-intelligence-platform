"""Tests for Safari .webarchive import support."""

from __future__ import annotations

import plistlib
from pathlib import Path

from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.infrastructure.importers.plugins.webarchive_importer import (
    WebArchiveImporter,
)
from profile_intelligence.main import main


def _write_webarchive(path: Path, *, name: str = "Melinda Cross") -> None:
    html = f"""<!DOCTYPE html>
<html><head>
<title>{name} | Profile</title>
<meta property="og:title" content="{name}"/>
<meta property="og:description" content="Independent companion based in London."/>
</head><body>
<h1>{name}</h1>
<p>Title: Companion</p>
<p>Location: London, UK</p>
<p>Email: melinda.cross@example.com</p>
<p>Phone: +44 20 7946 0958</p>
</body></html>
"""
    archive = {
        "WebMainResource": {
            "WebResourceData": html.encode("utf-8"),
            "WebResourceURL": "https://example.com/profiles/melinda-cross",
            "WebResourceMIMEType": "text/html",
            "WebResourceTextEncodingName": "UTF-8",
        }
    }
    path.write_bytes(plistlib.dumps(archive, fmt=plistlib.FMT_BINARY))


def test_webarchive_importer_parses_profile(tmp_path: Path) -> None:
    path = tmp_path / "profile.webarchive"
    _write_webarchive(path)
    plugin = WebArchiveImporter()
    assert plugin.can_handle(path)
    result = plugin.import_file(path)
    assert result.success
    assert len(result.records) == 1
    record = result.records[0]
    assert record["display_name"] == "Melinda Cross"
    assert record["email"] == "melinda.cross@example.com"
    assert "London" in str(record.get("location", ""))


def test_webarchive_pipeline_import_search(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    path = temp_root / "profile.webarchive"
    _write_webarchive(path)
    summary = container.resolve(ImportService).import_path(path)
    assert summary.plugin == "webarchive"
    assert summary.created == 1

    profiles = container.resolve(ProfileService)
    assert profiles.count() == 1
    found = profiles.search("melinda")
    assert len(found) == 1
    assert found[0].display_name == "Melinda Cross"
    assert found[0].email == "melinda.cross@example.com"
    app.shutdown()


def test_sample_webarchive_exists() -> None:
    sample = Path(__file__).resolve().parents[1] / "samples" / "profile.webarchive"
    assert sample.is_file()
    plugin = WebArchiveImporter()
    result = plugin.import_file(sample)
    assert result.success
    assert "Melinda" in str(result.records[0].get("display_name", ""))


def test_cli_webarchive_workflow(temp_root: Path, monkeypatch, capsys) -> None:
    from profile_intelligence import main as main_module

    path = temp_root / "profile.webarchive"
    _write_webarchive(path)

    def _build(config_path=None, root_dir=None):
        return build_container(config_path=config_path, root_dir=temp_root)

    monkeypatch.setattr(main_module, "build_container", _build)

    assert main(["migrate"]) == 0
    assert main(["import", str(path)]) == 0
    assert main(["list"]) == 0
    list_out = capsys.readouterr().out
    assert "Melinda Cross" in list_out

    assert main(["search", "melinda"]) == 0
    search_out = capsys.readouterr().out
    assert "Melinda Cross" in search_out
