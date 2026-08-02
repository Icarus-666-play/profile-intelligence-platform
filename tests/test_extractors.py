"""Tests for profile extractors."""

from __future__ import annotations

import pytest

from profile_intelligence.core.exceptions import ExtractorError
from profile_intelligence.extractors import ProfileExtractor


def test_extract_with_aliases() -> None:
    extractor = ProfileExtractor(default_source="csv")
    draft = extractor.extract(
        {
            "Full Name": "Ada Lovelace",
            "E-mail": "ada@example.com",
            "Company": "Analytical Engines",
            "Job Title": "Analyst",
        }
    )
    assert draft.display_name == "Ada Lovelace"
    assert draft.email == "ada@example.com"
    assert draft.organization == "Analytical Engines"
    assert draft.title == "Analyst"
    assert draft.source == "csv"
    assert draft.raw_json is not None


def test_extract_missing_name_raises() -> None:
    extractor = ProfileExtractor()
    with pytest.raises(ExtractorError, match="display name"):
        extractor.extract({"email": "x@example.com"})


def test_extract_many_collects_errors() -> None:
    extractor = ProfileExtractor()
    drafts, errors = extractor.extract_many(
        [
            {"name": "Valid"},
            {"email": "missing-name@example.com"},
        ]
    )
    assert len(drafts) == 1
    assert len(errors) == 1
    assert "row 2" in errors[0]
