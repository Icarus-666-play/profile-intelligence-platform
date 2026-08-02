"""Unit tests for the NewWebsite importer package."""

from __future__ import annotations

from pathlib import Path

from newwebsite.extractor import NewWebsiteExtractor
from newwebsite.normalizer import NewWebsiteNormalizer
from newwebsite.parser import NewWebsiteParser
from newwebsite.plugin import NewWebsiteImporter
from newwebsite.validator import NewWebsiteValidator
from profile_intelligence.infrastructure.importers.registry import ImporterRegistry


def _write_html(path: Path, *, name: str = "Ada Lovelace") -> None:
    path.write_text(
        f"""
        <html>
          <body>
            <article class="nw-profile" data-site="newwebsite">
              <h1 data-name="{name}">{name}</h1>
              <span data-email="ada@example.com">ada@example.com</span>
              <span data-location="London">London</span>
              <ul class="tags"><li>math</li><li>engines</li></ul>
              <p class="notes">Analytical engines</p>
            </article>
          </body>
        </html>
        """,
        encoding="utf-8",
    )


def test_parser_extractor_validator_normalizer(tmp_path: Path) -> None:
    source = tmp_path / "ada.newwebsite.html"
    _write_html(source)

    document = NewWebsiteParser().parse(source)
    assert document.is_complete
    assert NewWebsiteParser().looks_like_newwebsite(document)

    extracted = NewWebsiteExtractor().extract(document)
    assert extracted.name == "Ada Lovelace"
    assert extracted.email == "ada@example.com"

    validation = NewWebsiteValidator().validate(extracted)
    assert validation.is_valid

    record = NewWebsiteNormalizer().normalize(extracted, document)
    assert record["display_name"] == "Ada Lovelace"
    assert record["source"] == "newwebsite"
    assert "math" in (record.get("tags") or "")


def test_importer_parse_profiles_html_and_json(tmp_path: Path) -> None:
    html_path = tmp_path / "profile.newwebsite.html"
    _write_html(html_path, name="Grace Hopper")
    json_path = tmp_path / "profile.newwebsite.json"
    json_path.write_text(
        '{"name": "Alan Turing", "email": "alan@example.com", '
        '"source": "newwebsite"}',
        encoding="utf-8",
    )

    importer = NewWebsiteImporter()
    assert importer.can_handle(html_path)
    assert importer.can_handle(json_path)

    html_records, html_skipped = importer.parse_profiles(html_path)  # type: ignore[misc]
    assert html_skipped == 0
    assert html_records[0]["display_name"] == "Grace Hopper"

    json_outcome = importer.parse_profiles(json_path)
    assert isinstance(json_outcome, tuple)
    json_records, json_skipped = json_outcome
    assert json_skipped == 0
    assert json_records[0]["display_name"] == "Alan Turing"


def test_validator_rejects_nameless_profile(tmp_path: Path) -> None:
    source = tmp_path / "empty.newwebsite.html"
    source.write_text(
        '<div class="nw-profile" data-site="newwebsite"><p>no name</p></div>',
        encoding="utf-8",
    )
    importer = NewWebsiteImporter()
    result = importer.import_file(source)
    assert result.success is False


def test_plugin_discoverable_and_importable(tmp_path: Path) -> None:
    repo_plugins = Path(__file__).resolve().parents[1]
    registry = ImporterRegistry()
    registry.discover_directory(repo_plugins)
    names = {plugin.name for plugin in registry.list_plugins()}
    assert "newwebsite" in names

    source = tmp_path / "ada.newwebsite.html"
    _write_html(source)
    plugin = registry.get("newwebsite")
    assert isinstance(plugin, NewWebsiteImporter)
    result = plugin.import_file(source)
    assert result.success
    assert result.records_imported == 1
