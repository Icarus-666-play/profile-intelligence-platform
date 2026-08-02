"""Normalize raw import rows into typed profile drafts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any

from profile_intelligence.core.exceptions import ExtractorError
from profile_intelligence.core.logging import get_logger

logger = get_logger(__name__)

_HEADER_ALIASES: dict[str, tuple[str, ...]] = {
    "display_name": (
        "display_name",
        "displayname",
        "name",
        "full_name",
        "fullname",
        "profile_name",
    ),
    "external_id": (
        "external_id",
        "externalid",
        "id",
        "profile_id",
        "uid",
        "user_id",
    ),
    "email": ("email", "e_mail", "email_address", "mail"),
    "phone": ("phone", "mobile", "telephone", "phone_number", "cell"),
    "title": ("title", "job_title", "role", "position", "jobtitle"),
    "organization": (
        "organization",
        "organisation",
        "company",
        "org",
        "employer",
    ),
    "location": ("location", "city", "address", "region", "country"),
    "tags": ("tags", "labels", "keywords", "skills"),
    "notes": ("notes", "comments", "comment", "description"),
    "source": ("source", "origin", "provider"),
}


def _normalize_key(key: object) -> str:
    text = str(key).strip().lower()
    return "".join(ch if ch.isalnum() else "_" for ch in text).strip("_")


@dataclass(slots=True)
class ProfileDraft:
    """Normalized profile payload prior to persistence."""

    display_name: str
    external_id: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    organization: str | None = None
    location: str | None = None
    tags: str | None = None
    notes: str | None = None
    source: str | None = None
    raw_json: str | None = None
    score: int | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Return a plain dict of draft fields."""
        return asdict(self)


class ProfileExtractor:
    """Map loosely-named raw records onto :class:`ProfileDraft`."""

    def __init__(self, *, default_source: str | None = None) -> None:
        self.default_source = default_source
        self._alias_index = {
            alias: field_name
            for field_name, aliases in _HEADER_ALIASES.items()
            for alias in aliases
        }

    def extract(
        self,
        record: Mapping[str, Any],
        *,
        source_override: str | None = None,
    ) -> ProfileDraft:
        """Extract a single profile draft from a raw mapping."""
        if not isinstance(record, Mapping):
            raise ExtractorError("Record must be a mapping")

        normalized: dict[str, Any] = {}
        for key, value in record.items():
            alias = self._alias_index.get(_normalize_key(key))
            if alias is None:
                continue
            cleaned = self._clean_value(value)
            if cleaned is None:
                continue
            # First non-empty alias wins.
            normalized.setdefault(alias, cleaned)

        display_name = normalized.get("display_name")
        if not display_name:
            raise ExtractorError(
                "Record is missing a display name "
                "(expected columns like name/display_name/full_name)"
            )

        source = (
            source_override
            or normalized.get("source")
            or self.default_source
        )

        return ProfileDraft(
            display_name=str(display_name),
            external_id=_as_optional_str(normalized.get("external_id")),
            email=_as_optional_str(normalized.get("email")),
            phone=_as_optional_str(normalized.get("phone")),
            title=_as_optional_str(normalized.get("title")),
            organization=_as_optional_str(normalized.get("organization")),
            location=_as_optional_str(normalized.get("location")),
            tags=_as_optional_str(normalized.get("tags")),
            notes=_as_optional_str(normalized.get("notes")),
            source=_as_optional_str(source),
            raw_json=json.dumps(dict(record), ensure_ascii=True, default=str),
        )

    def extract_many(
        self,
        records: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
        *,
        source_override: str | None = None,
    ) -> tuple[list[ProfileDraft], list[str]]:
        """Extract many drafts; return drafts and per-row error messages."""
        drafts: list[ProfileDraft] = []
        errors: list[str] = []
        for index, record in enumerate(records, start=1):
            try:
                drafts.append(
                    self.extract(record, source_override=source_override)
                )
            except ExtractorError as exc:
                errors.append(f"row {index}: {exc.message}")
        logger.debug(
            "Extracted %d draft(s) with %d error(s)",
            len(drafts),
            len(errors),
        )
        return drafts, errors

    @staticmethod
    def _clean_value(value: object) -> object | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


def _as_optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def draft_field_names() -> tuple[str, ...]:
    """Return ProfileDraft field names (useful for exporters/tests)."""
    return tuple(field.name for field in fields(ProfileDraft))
