"""Unit tests for the EuroGirls Safari .webarchive importer (Sprint 1)."""

from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from eurogirls.extractor import EuroGirlsExtractor, Rate, Service
from eurogirls.normalizer import EuroGirlsNormalizer
from eurogirls.parser import PARSER_VERSION, WebArchiveParser
from eurogirls.plugin import EuroGirlsImporter
from profile_intelligence.application.use_cases.application import ApplicationService
from profile_intelligence.application.use_cases.import_service import ImportService
from profile_intelligence.application.use_cases.profile_service import ProfileService
from profile_intelligence.bootstrap import build_container
from profile_intelligence.infrastructure.media.hashing import hash_bytes

SAMPLES = Path(__file__).resolve().parents[2] / "samples" / "eurogirls"
SOPHIA = SAMPLES / "sophia_eurogirls.webarchive"
INCOMPLETE = SAMPLES / "incomplete_eurogirls.webarchive"


def _sample_html(
    *,
    name: str = "Luna",
    profile_id: str = "EG-999",
) -> str:
    return f"""<!DOCTYPE html>
<html>
<head>
  <title>{name} | EuroGirls</title>
  <meta property="og:url"
        content="https://www.eurogirlsescort.com/escorts/{profile_id.lower()}"/>
</head>
<body data-site="eurogirls">
  <h1 class="profile-name">{name}</h1>
  <div class="profile-id" data-profile-id="{profile_id}">ID: {profile_id}</div>
  <span class="city">Berlin</span>
  <span class="country">Germany</span>
  <table class="details">
    <tr><th>Nationality</th><td>German</td></tr>
    <tr><th>Languages</th><td>English; German</td></tr>
    <tr><th>Age</th><td>25</td></tr>
    <tr><th>Height</th><td>165 cm</td></tr>
    <tr><th>Weight</th><td>52 kg</td></tr>
    <tr><th>Hair</th><td>Blonde</td></tr>
    <tr><th>Eyes</th><td>Blue</td></tr>
    <tr><th>Bust</th><td>B</td></tr>
    <tr><th>Measurements</th><td>85-60-88</td></tr>
  </table>
  <table class="rates">
    <tr data-duration="1 hour" data-price="250" data-currency="EUR"
        data-incall="true" data-outcall="true">
      <td>1 hour</td><td>250 EUR</td><td>Incall / Outcall</td>
    </tr>
  </table>
  <ul class="services">
    <li data-service="GFE" data-available="true">GFE</li>
    <li data-service="Travel" data-available="false">Travel</li>
  </ul>
  <img class="main-photo" src="https://cdn.example/main.jpg"/>
  <div class="gallery">
    <img src="https://cdn.example/g1.jpg"/>
  </div>
</body>
</html>
"""


def _write_archive(
    path: Path,
    html: str,
    *,
    url: str = "https://www.eurogirlsescort.com/escorts/luna",
    subresources: list[dict[str, object]] | None = None,
) -> None:
    archive = {
        "WebMainResource": {
            "WebResourceData": html.encode("utf-8"),
            "WebResourceURL": url,
            "WebResourceMIMEType": "text/html",
            "WebResourceTextEncodingName": "UTF-8",
        },
        "WebSubresources": subresources or [],
    }
    path.write_bytes(plistlib.dumps(archive, fmt=plistlib.FMT_BINARY))


@pytest.fixture
def parser() -> WebArchiveParser:
    return WebArchiveParser()


@pytest.fixture
def extractor() -> EuroGirlsExtractor:
    return EuroGirlsExtractor()


@pytest.fixture
def normalizer() -> EuroGirlsNormalizer:
    return EuroGirlsNormalizer()


@pytest.fixture
def importer(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
    normalizer: EuroGirlsNormalizer,
) -> EuroGirlsImporter:
    return EuroGirlsImporter(
        parser=parser,
        extractor=extractor,
        normalizer=normalizer,
    )


def test_sample_files_exist() -> None:
    assert SOPHIA.is_file()
    assert INCOMPLETE.is_file()


def test_parser_loads_sample(parser: WebArchiveParser) -> None:
    parsed = parser.parse(SOPHIA)
    assert parsed.is_complete
    assert parsed.parser_version == PARSER_VERSION
    assert "Sophia" in parsed.html
    assert parsed.url and "eurogirlsescort.com" in parsed.url
    assert len(parsed.subresources) == 3
    assert parser.looks_like_eurogirls(parsed)


def test_extractor_general_and_physical(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
) -> None:
    profile = extractor.extract(parser.parse(SOPHIA))
    assert profile.name == "Sophia"
    assert profile.profile_id == "EG-12345"
    assert profile.city == "Amsterdam"
    assert profile.country == "Netherlands"
    assert profile.nationality == "Italian"
    assert profile.languages == ["English", "Italian", "Dutch"]
    assert profile.age == "28"
    assert profile.height == "170 cm"
    assert profile.weight == "55 kg"
    assert profile.hair == "Brunette"
    assert profile.eyes == "Brown"
    assert profile.bust == "C"
    assert profile.measurements == "90-60-90"
    assert profile.is_complete


def test_extractor_rates_and_services(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
) -> None:
    profile = extractor.extract(parser.parse(SOPHIA))
    assert len(profile.rates) == 3
    first = profile.rates[0]
    assert isinstance(first, Rate)
    assert first.duration == "1 hour"
    assert first.price == "300"
    assert first.currency == "EUR"
    assert first.incall is True
    assert first.outcall is False
    overnight = profile.rates[2]
    assert overnight.duration == "Overnight"
    assert overnight.outcall is True
    assert len(profile.services) == 4
    assert all(isinstance(item, Service) for item in profile.services)
    assert {item.name for item in profile.services} >= {"GFE", "Dinner date"}


def test_extractor_photos_with_sha256(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
) -> None:
    archive = parser.parse(SOPHIA)
    profile = extractor.extract(archive)
    assert len(profile.photos) == 3
    main = next(photo for photo in profile.photos if photo.role == "main")
    assert main.original_url.endswith("sophia-main.jpg")
    assert main.sha256 == hash_bytes(archive.subresources[0].data)
    gallery = [photo for photo in profile.photos if photo.role == "gallery"]
    assert len(gallery) == 2
    assert all(photo.sha256 for photo in gallery)


def test_normalizer_metadata_and_entities(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
    normalizer: EuroGirlsNormalizer,
) -> None:
    archive = parser.parse(SOPHIA)
    record = normalizer.normalize(extractor.extract(archive), archive)
    assert record["display_name"] == "Sophia"
    assert record["external_id"] == "EG-12345"
    assert record["source"] == "eurogirls"
    assert "Amsterdam" in str(record["location"])
    assert isinstance(record["rates"], list)
    assert record["rates"][0]["duration"] == "1 hour"
    assert isinstance(record["services"], list)
    assert record["main_image"]["role"] == "main"
    assert len(record["gallery"]) == 2
    metadata = record["metadata"]
    assert metadata["website"] == "eurogirls"
    assert metadata["parser_version"] == PARSER_VERSION
    assert "import_date" in metadata


def test_importer_sample_success(importer: EuroGirlsImporter) -> None:
    assert importer.can_handle(SOPHIA) is True
    result = importer.import_file(SOPHIA)
    assert result.success
    assert result.records_read == 1
    record = result.records[0]
    assert record["display_name"] == "Sophia"
    assert len(record["rates"]) == 3
    assert len(record["services"]) == 4
    assert len(record["photos"]) == 3


def test_importer_rejects_incomplete(importer: EuroGirlsImporter) -> None:
    result = importer.import_file(INCOMPLETE)
    assert result.success is False
    assert result.records_read == 0
    assert any("incomplete" in err.lower() or "name" in err.lower()
               for err in result.errors)


def test_importer_never_crashes_on_garbage(
    importer: EuroGirlsImporter,
    tmp_path: Path,
) -> None:
    garbage = tmp_path / "broken_eurogirls.webarchive"
    garbage.write_bytes(b"not-a-plist")
    result = importer.import_file(garbage)
    assert result.success is False
    assert result.errors


def test_can_handle_requires_eurogirls_signal(
    importer: EuroGirlsImporter,
    tmp_path: Path,
) -> None:
    generic = tmp_path / "profile.webarchive"
    html = "<html><head><title>Melinda</title></head><body><h1>Melinda</h1></body></html>"
    _write_archive(
        generic,
        html,
        url="https://example.com/profiles/melinda",
    )
    assert importer.can_handle(generic) is False

    marked = tmp_path / "file_eurogirls.webarchive"
    _write_archive(marked, _sample_html())
    assert importer.can_handle(marked) is True


def test_rate_text_fallback(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
    tmp_path: Path,
) -> None:
    html = """<!DOCTYPE html><html><body data-site="eurogirls">
    <h1 class="profile-name">Mia</h1>
    <div class="profile-id">EG-1</div>
    <ul class="rates">
      <li>1 hour — 200 € incall</li>
      <li>2 hours 350 EUR outcall</li>
    </ul>
    </body></html>"""
    path = tmp_path / "mia_eurogirls.webarchive"
    _write_archive(path, html)
    profile = extractor.extract(parser.parse(path))
    assert len(profile.rates) >= 2
    assert profile.rates[0].currency == "EUR"


def test_pipeline_import_to_sqlite(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    # Ensure external plugins dir points at repo plugins via copy/symlink-less
    # discovery: ApplicationService uses config.plugins_dir under temp_root.
    # Copy sample into temp inbox-style path with eurogirls marker.
    target = temp_root / "sophia_eurogirls.webarchive"
    target.write_bytes(SOPHIA.read_bytes())

    # Register eurogirls from the real plugins package path.
    from profile_intelligence.infrastructure.importers.registry import (
        ImporterRegistry,
    )

    registry = container.resolve(ImporterRegistry)
    repo_plugins = Path(__file__).resolve().parents[2] / "plugins"
    registry.discover_directory(repo_plugins)
    assert registry.get("eurogirls")

    summary = container.resolve(ImportService).import_path(
        target,
        plugin_name="eurogirls",
        source="eurogirls",
    )
    assert summary.created == 1
    profiles = container.resolve(ProfileService)
    assert profiles.count() == 1
    found = profiles.search("Sophia")
    assert len(found) == 1
    assert found[0].display_name == "Sophia"
    assert found[0].source == "eurogirls"
    assert found[0].raw_json is not None
    assert "rates" in found[0].raw_json
    assert "EG-12345" in found[0].raw_json
    app.shutdown()


def test_dependency_injection_override(tmp_path: Path) -> None:
    # Injecting custom components should wire through __init__.
    importer = EuroGirlsImporter(
        parser=WebArchiveParser(),
        extractor=EuroGirlsExtractor(hash_algorithm="sha256"),
        normalizer=EuroGirlsNormalizer(),
    )
    path = tmp_path / "di_eurogirls.webarchive"
    _write_archive(path, _sample_html(name="DI Girl", profile_id="EG-DI"))
    result = importer.import_file(path)
    assert result.success
    assert result.records[0]["display_name"] == "DI Girl"


def test_can_handle_wrong_extension(importer: EuroGirlsImporter, tmp_path: Path) -> None:
    path = tmp_path / "eurogirls.csv"
    path.write_text("name\nAda\n", encoding="utf-8")
    assert importer.can_handle(path) is False


def test_can_handle_sniff_failure_returns_false(
    importer: EuroGirlsImporter,
    tmp_path: Path,
) -> None:
    path = tmp_path / "mystery.webarchive"
    path.write_bytes(b"not-a-valid-plist")
    assert importer.can_handle(path) is False


def test_parser_rejects_missing_main_resource(
    parser: WebArchiveParser,
    tmp_path: Path,
) -> None:
    path = tmp_path / "empty_eurogirls.webarchive"
    path.write_bytes(plistlib.dumps({"WebSubresources": []}, fmt=plistlib.FMT_BINARY))
    with pytest.raises(Exception, match="WebMainResource"):
        parser.parse(path)


def test_parser_string_html_resource(
    parser: WebArchiveParser,
    tmp_path: Path,
) -> None:
    path = tmp_path / "string_eurogirls.webarchive"
    archive = {
        "WebMainResource": {
            "WebResourceData": "<html data-site='eurogirls'><h1>Ana</h1></html>",
            "WebResourceURL": "https://www.eurogirlsescort.com/escorts/ana",
            "WebResourceMIMEType": "text/html",
        }
    }
    path.write_bytes(plistlib.dumps(archive, fmt=plistlib.FMT_BINARY))
    parsed = parser.parse(path)
    assert "Ana" in parsed.html


def test_importer_rejects_empty_html(
    importer: EuroGirlsImporter,
    tmp_path: Path,
) -> None:
    path = tmp_path / "blank_eurogirls.webarchive"
    _write_archive(path, "   ", url="https://www.eurogirlsescort.com/escorts/x")
    result = importer.import_file(path)
    assert result.success is False
    assert any("incomplete" in err.lower() for err in result.errors)


def test_importer_rejects_non_eurogirls_document(
    importer: EuroGirlsImporter,
    tmp_path: Path,
) -> None:
    path = tmp_path / "other.webarchive"
    html = "<html><body><h1 class='profile-name'>Other</h1></body></html>"
    _write_archive(path, html, url="https://example.com/other")
    # Force parse_profiles even though can_handle is false.
    result = importer.parse_profiles(path)
    assert isinstance(result, type(importer.import_file(SOPHIA))) or True
    from profile_intelligence.infrastructure.importers.base import ImportResult

    assert isinstance(result, ImportResult)
    assert result.success is False


def test_extractor_dt_dd_and_data_field(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
    tmp_path: Path,
) -> None:
    html = """<!DOCTYPE html><html><body data-site="eurogirls">
    <h1 class="profile-name">Nora</h1>
    <dl>
      <dt>Profile ID</dt><dd>EG-55</dd>
      <dt>City</dt><dd>Paris</dd>
      <dt>Country</dt><dd>France</dd>
      <dt>Languages</dt><dd>French / English</dd>
    </dl>
    <div data-field="hair">Red</div>
    <div data-field="eyes">Green</div>
    </body></html>"""
    path = tmp_path / "nora_eurogirls.webarchive"
    _write_archive(path, html)
    profile = extractor.extract(parser.parse(path))
    assert profile.profile_id == "EG-55"
    assert profile.city == "Paris"
    assert profile.country == "France"
    assert profile.languages == ["French", "English"]
    assert profile.hair == "Red"
    assert profile.eyes == "Green"


def test_extractor_title_fallback_name(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
    tmp_path: Path,
) -> None:
    html = """<!DOCTYPE html><html><head>
    <title>Clara | EuroGirls Escort</title>
    </head><body data-site="eurogirls">
    <div class="profile-id">EG-77</div>
    </body></html>"""
    path = tmp_path / "clara_eurogirls.webarchive"
    _write_archive(path, html)
    profile = extractor.extract(parser.parse(path))
    assert profile.name == "Clara"
    assert profile.profile_id == "EG-77"


def test_plugin_extraction_failure_is_soft(
    parser: WebArchiveParser,
    normalizer: EuroGirlsNormalizer,
    tmp_path: Path,
) -> None:
    class BoomExtractor(EuroGirlsExtractor):
        def extract(self, archive):
            raise RuntimeError("boom")

    importer = EuroGirlsImporter(
        parser=parser,
        extractor=BoomExtractor(),
        normalizer=normalizer,
    )
    path = tmp_path / "boom_eurogirls.webarchive"
    _write_archive(path, _sample_html())
    result = importer.import_file(path)
    assert result.success is False
    assert any("extraction failed" in err.lower() for err in result.errors)


def test_plugin_normalize_failure_is_soft(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
    tmp_path: Path,
) -> None:
    class BoomNormalizer(EuroGirlsNormalizer):
        def normalize(self, profile, archive, *, import_date=None):
            raise RuntimeError("normalize-boom")

    importer = EuroGirlsImporter(
        parser=parser,
        extractor=extractor,
        normalizer=BoomNormalizer(),
    )
    path = tmp_path / "norm_eurogirls.webarchive"
    _write_archive(path, _sample_html())
    result = importer.import_file(path)
    assert result.success is False
    assert any("normalize failed" in err.lower() for err in result.errors)


def test_plugin_unexpected_parse_error_is_soft(
    extractor: EuroGirlsExtractor,
    normalizer: EuroGirlsNormalizer,
    tmp_path: Path,
) -> None:
    class WeirdParser(WebArchiveParser):
        def parse(self, path):
            raise ValueError("unexpected")

    importer = EuroGirlsImporter(
        parser=WeirdParser(),
        extractor=extractor,
        normalizer=normalizer,
    )
    path = tmp_path / "weird_eurogirls.webarchive"
    _write_archive(path, _sample_html())
    result = importer.import_file(path)
    assert result.success is False
    assert any("unexpected" in err.lower() for err in result.errors)


def test_parser_invalid_root_and_resource_types(
    parser: WebArchiveParser,
    tmp_path: Path,
) -> None:
    bad_root = tmp_path / "list_eurogirls.webarchive"
    bad_root.write_bytes(plistlib.dumps(["not", "a", "dict"], fmt=plistlib.FMT_BINARY))
    with pytest.raises(Exception, match="dictionary"):
        parser.parse(bad_root)

    bad_data = tmp_path / "baddata_eurogirls.webarchive"
    archive = {
        "WebMainResource": {
            "WebResourceData": 12345,
            "WebResourceURL": "https://www.eurogirlsescort.com/escorts/x",
        }
    }
    bad_data.write_bytes(plistlib.dumps(archive, fmt=plistlib.FMT_BINARY))
    with pytest.raises(Exception, match="WebResourceData"):
        parser.parse(bad_data)


def test_extractor_rate_row_without_data_attrs(
    parser: WebArchiveParser,
    extractor: EuroGirlsExtractor,
    tmp_path: Path,
) -> None:
    html = """<!DOCTYPE html><html><body data-site="eurogirls">
    <h1 class="profile-name">Ivy</h1>
    <div class="profile-id">EG-88</div>
    <table class="rates"><tbody>
      <tr><td>1 hour</td><td>180 EUR</td><td>incall outcall</td></tr>
    </tbody></table>
    <ul class="services">
      <li class="service">Companion</li>
      <li data-service="Travel" data-available="no">Travel</li>
    </ul>
    <meta property="og:image" content="https://cdn.example/og.jpg"/>
    </body></html>"""
    path = tmp_path / "ivy_eurogirls.webarchive"
    _write_archive(path, html)
    profile = extractor.extract(parser.parse(path))
    assert len(profile.rates) == 1
    assert profile.rates[0].currency == "EUR"
    assert profile.rates[0].incall is True
    assert profile.rates[0].outcall is True
    travel = next(s for s in profile.services if s.name == "Travel")
    assert travel.available is False
    assert any(photo.role == "main" for photo in profile.photos)


def test_parser_skips_bad_subresources(
    parser: WebArchiveParser,
    tmp_path: Path,
) -> None:
    path = tmp_path / "sub_eurogirls.webarchive"
    archive = {
        "WebMainResource": {
            "WebResourceData": b"<html data-site='eurogirls'><h1>Zoe</h1></html>",
            "WebResourceURL": "https://www.eurogirlsescort.com/escorts/zoe",
            "WebResourceMIMEType": "text/html",
            "WebResourceTextEncodingName": "not-a-real-codec",
        },
        "WebSubresources": [
            {"WebResourceURL": "", "WebResourceData": b"x"},
            "not-a-dict",
            {
                "WebResourceURL": "https://cdn.example/ok.jpg",
                "WebResourceData": b"image-bytes",
                "WebResourceMIMEType": "image/jpeg",
            },
        ],
    }
    path.write_bytes(plistlib.dumps(archive, fmt=plistlib.FMT_BINARY))
    parsed = parser.parse(path)
    assert len(parsed.subresources) == 1
    assert parsed.subresources[0].url.endswith("ok.jpg")
