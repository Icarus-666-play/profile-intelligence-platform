"""Tests for File → … → SQLite staged pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.exceptions import ValidationError
from profile_intelligence.extractors.profile import ProfileDraft
from profile_intelligence.pipeline import (
    DocumentParser,
    ImportPipeline,
    ProfileNormalizer,
    ProfileValidator,
    RawDocument,
)
from profile_intelligence.services.application import ApplicationService
from profile_intelligence.services.profile_service import ProfileService


def test_raw_document_from_path(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    path.write_text("name\nAda\n", encoding="utf-8")
    document = RawDocument.from_path(path, source="csv")
    assert document.path == path.resolve()
    assert document.content_type == "csv"
    assert document.metadata["name"] == "sample.csv"


def test_raw_document_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="does not exist"):
        RawDocument.from_path(tmp_path / "missing.csv")


def test_validator_rejects_bad_email() -> None:
    validator = ProfileValidator()
    draft = ProfileDraft(display_name="Ada", email="not-an-email")
    with pytest.raises(ValidationError, match="email is invalid"):
        validator.validate(draft)


def test_validator_accepts_clean_draft() -> None:
    validator = ProfileValidator()
    draft = ProfileDraft(
        display_name="Ada Lovelace",
        email="ada@example.com",
        phone="+1-555-0100",
    )
    assert validator.validate(draft) is draft


def test_normalizer_maps_aliases() -> None:
    normalizer = ProfileNormalizer()
    draft = normalizer.normalize(
        {"full_name": "Grace Hopper", "company": "US Navy"},
        source_override="csv",
    )
    assert draft.display_name == "Grace Hopper"
    assert draft.organization == "US Navy"
    assert draft.source == "csv"


def test_full_pipeline_stages(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    csv_path = temp_root / "pipeline_people.csv"
    csv_path.write_text(
        "name,email,organization\n"
        "Ada Lovelace,ada@example.com,Analytical Engines\n"
        "Bad Row,not-an-email,Nowhere\n",
        encoding="utf-8",
    )

    pipeline = container.resolve(ImportPipeline)
    document = pipeline.load_document(csv_path)
    parsed = pipeline.parse_document(document)
    assert parsed.plugin_name == "csv"
    assert len(parsed.records) == 2

    drafts, norm_errors = pipeline.normalizer.normalize_many(
        parsed.records,
        source_override="csv",
    )
    assert norm_errors == []
    assert len(drafts) == 2

    validated, val_errors = pipeline.validator.validate_many(drafts)
    assert len(validated) == 1
    assert validated[0].display_name == "Ada Lovelace"
    assert any("email is invalid" in error for error in val_errors)

    result = pipeline.process(csv_path)
    assert result.created == 1
    assert result.skipped >= 1
    assert container.resolve(ProfileService).count() == 1
    assert result.entities[0].email == "ada@example.com"
    app.shutdown()


def test_document_parser_uses_registry(temp_root: Path) -> None:
    container = build_container(root_dir=temp_root)
    app = container.resolve(ApplicationService)
    app.start()

    path = temp_root / "only.csv"
    path.write_text("name\nAda\n", encoding="utf-8")
    parser = DocumentParser(app.importers)
    parsed = parser.parse(RawDocument.from_path(path))
    assert parsed.records[0]["name"] == "Ada"
    app.shutdown()
