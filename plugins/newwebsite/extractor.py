"""Extract structured profile fields from a parsed NewWebsite document.

```
plugins/
  newwebsite/
    extractor.py
```
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from newwebsite.parser import ParsedDocument
from profile_intelligence.core.logging import get_logger

logger = get_logger("importers.external.newwebsite.extractor")

_META_RE = re.compile(
    r'data-(?P<key>name|email|phone|title|organization|location|external_id)'
    r'="(?P<value>[^"]+)"',
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ExtractedProfile:
    """Structured NewWebsite profile prior to normalization."""

    name: str | None = None
    external_id: str | None = None
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    organization: str | None = None
    location: str | None = None
    url: str | None = None
    tags: tuple[str, ...] = field(default_factory=tuple)
    notes: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_complete(self) -> bool:
        """True when a display name is present."""
        return bool(self.name and self.name.strip())

    def to_mapping(self) -> dict[str, Any]:
        """Serialize extracted fields for debugging / raw_json."""
        return {
            "name": self.name,
            "external_id": self.external_id,
            "email": self.email,
            "phone": self.phone,
            "title": self.title,
            "organization": self.organization,
            "location": self.location,
            "url": self.url,
            "tags": list(self.tags),
            "notes": self.notes,
            "warnings": list(self.warnings),
        }


class NewWebsiteExtractor:
    """Pull profile fields from HTML or JSON NewWebsite documents."""

    def extract(self, document: ParsedDocument) -> ExtractedProfile:
        """Extract one primary profile from *document*."""
        if document.kind == "json":
            return self._extract_json(document)
        return self._extract_html(document)

    def extract_many(self, document: ParsedDocument) -> tuple[ExtractedProfile, ...]:
        """Extract all profiles when the JSON payload contains a list."""
        if document.kind != "json":
            return (self.extract(document),)

        rows = document.payload.get("profiles") or document.payload.get("records")
        if isinstance(rows, list):
            profiles = [
                self._from_mapping(row, url=document.url)
                for row in rows
                if isinstance(row, Mapping)
            ]
            return tuple(profiles) or (self._extract_json(document),)
        return (self._extract_json(document),)

    def _extract_json(self, document: ParsedDocument) -> ExtractedProfile:
        rows = document.payload.get("profiles") or document.payload.get("records")
        if isinstance(rows, list) and rows and isinstance(rows[0], Mapping):
            return self._from_mapping(rows[0], url=document.url)
        return self._from_mapping(document.payload, url=document.url)

    def _extract_html(self, document: ParsedDocument) -> ExtractedProfile:
        warnings: list[str] = []
        soup = BeautifulSoup(document.html, "html.parser")

        fields: dict[str, str | None] = {
            "name": None,
            "email": None,
            "phone": None,
            "title": None,
            "organization": None,
            "location": None,
            "external_id": None,
        }

        root = soup.select_one(".nw-profile, [data-site='newwebsite'], article.profile")
        scope = root or soup

        for key in fields:
            node = scope.select_one(f"[data-{key}], .{key}, #{key}")
            if node is not None:
                text = node.get_text(" ", strip=True)
                attr = node.get(f"data-{key}")
                fields[key] = str(attr).strip() if attr else (text or None)

        # Fallback: meta-style attributes anywhere in the document.
        for match in _META_RE.finditer(document.html):
            key = match.group("key").lower()
            if fields.get(key) is None:
                fields[key] = match.group("value").strip()

        if fields["name"] is None:
            heading = scope.find(["h1", "h2"])
            if heading is not None:
                fields["name"] = heading.get_text(" ", strip=True) or None

        if fields["name"] is None:
            warnings.append("No profile name found in HTML")

        tags = tuple(
            node.get_text(" ", strip=True)
            for node in scope.select(".tag, .tags li, [data-tag]")
            if node.get_text(" ", strip=True)
        )
        notes_node = scope.select_one(".notes, .description, [data-notes]")
        notes = (
            notes_node.get_text("\n", strip=True) if notes_node is not None else None
        )

        profile = ExtractedProfile(
            name=fields["name"],
            external_id=fields["external_id"],
            email=fields["email"],
            phone=fields["phone"],
            title=fields["title"],
            organization=fields["organization"] or "newwebsite",
            location=fields["location"],
            url=document.url,
            tags=tags,
            notes=notes,
            warnings=tuple(warnings),
        )
        logger.debug(
            "Extracted NewWebsite HTML profile name=%r warnings=%d",
            profile.name,
            len(profile.warnings),
        )
        return profile

    def _from_mapping(
        self,
        raw: Mapping[str, Any],
        *,
        url: str | None,
    ) -> ExtractedProfile:
        tags_raw = raw.get("tags")
        if isinstance(tags_raw, str):
            tags: tuple[str, ...] = tuple(
                part.strip() for part in tags_raw.split(",") if part.strip()
            )
        elif isinstance(tags_raw, Sequence) and not isinstance(tags_raw, (str, bytes)):
            tags = tuple(str(item).strip() for item in tags_raw if str(item).strip())
        else:
            tags = ()

        name = _text(raw.get("name") or raw.get("display_name"))
        warnings: list[str] = []
        if name is None:
            warnings.append("No profile name found in JSON")

        return ExtractedProfile(
            name=name,
            external_id=_text(raw.get("external_id") or raw.get("id")),
            email=_text(raw.get("email")),
            phone=_text(raw.get("phone")),
            title=_text(raw.get("title")),
            organization=_text(raw.get("organization")) or "newwebsite",
            location=_text(raw.get("location")),
            url=_text(raw.get("url")) or url,
            tags=tags,
            notes=_text(raw.get("notes")),
            warnings=tuple(warnings),
        )


def _text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
