"""Built-in Safari ``.webarchive`` importer plugin."""

from __future__ import annotations

import plistlib
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlparse

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.infrastructure.importers.base import ImportResult, RawRecord
from profile_intelligence.infrastructure.importers.profile_importer import (
    ProfileImporter,
    ProfileParseOutcome,
)

logger = get_logger(__name__)

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s\-.]?)?(?:\(?\d{2,4}\)?[\s\-.]?)?\d{3,4}[\s\-.]?\d{3,4}"
)
_LABEL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "location",
        re.compile(
            r"(?:location|city|based in|from)\s*[:\-]\s*([^\n<]{2,80})",
            re.IGNORECASE,
        ),
    ),
    (
        "organization",
        re.compile(
            r"(?:organization|organisation|company|agency)\s*[:\-]\s*([^\n<]{2,80})",
            re.IGNORECASE,
        ),
    ),
    (
        "title",
        re.compile(
            r"(?:title|role|occupation)\s*[:\-]\s*([^\n<]{2,80})",
            re.IGNORECASE,
        ),
    ),
    (
        "phone",
        re.compile(
            r"(?:phone|tel|mobile|cell)\s*[:\-]\s*([+\d()\-\s.]{7,32})",
            re.IGNORECASE,
        ),
    ),
    (
        "email",
        re.compile(
            r"(?:email|e-mail)\s*[:\-]\s*(" + _EMAIL_RE.pattern + ")",
            re.IGNORECASE,
        ),
    ),
)


class _ProfileHTMLParser(HTMLParser):
    """Collect title, headings, meta tags, and visible text from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.headings: list[str] = []
        self.meta: dict[str, str] = {}
        self.text_parts: list[str] = []
        self._capture_title = False
        self._capture_heading = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key.lower(): (value or "") for key, value in attrs}
        if tag == "title":
            self._capture_title = True
        elif tag in {"h1", "h2"}:
            self._capture_heading = True
        elif tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif tag == "meta":
            key = (
                attrs_map.get("property")
                or attrs_map.get("name")
                or attrs_map.get("itemprop")
                or ""
            ).lower()
            content = attrs_map.get("content", "").strip()
            if key and content:
                self.meta[key] = content

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._capture_title = False
        elif tag in {"h1", "h2"}:
            self._capture_heading = False
        elif tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._capture_title:
            self.title_parts.append(text)
        if self._capture_heading:
            self.headings.append(text)
        if self._skip_depth == 0:
            self.text_parts.append(text)


class WebArchiveImporter(ProfileImporter):
    """Import a profile snapshot from a Safari ``.webarchive`` file."""

    name: ClassVar[str] = "webarchive"
    description: ClassVar[str] = (
        "Safari .webarchive profile page importer (HTML main resource)"
    )
    supported_extensions: ClassVar[tuple[str, ...]] = (".webarchive",)

    def parse_profiles(self, path: Path, **options: object) -> ProfileParseOutcome:
        archive = _load_webarchive(path)
        main = archive.get("WebMainResource")
        if not isinstance(main, dict):
            return ImportResult.failure(
                "WebArchive missing WebMainResource dictionary"
            )

        html = _decode_main_html(main)
        url = str(main.get("WebResourceURL") or "").strip() or None
        record = _extract_profile_record(html, url=url)
        if not record.get("name") and not record.get("display_name"):
            return ImportResult.failure(
                "Could not extract a profile name from webarchive HTML"
            )

        logger.debug(
            "Parsed webarchive %s name=%r url=%s",
            path,
            record.get("display_name") or record.get("name"),
            url,
        )
        return [record], 0


def _load_webarchive(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            payload = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException, ValueError) as exc:
        raise ImporterError(
            f"Failed to read webarchive plist: {path}",
            cause=exc,
        ) from exc
    if not isinstance(payload, dict):
        raise ImporterError("WebArchive root must be a dictionary")
    return payload


def _decode_main_html(main: dict[str, Any]) -> str:
    data = main.get("WebResourceData")
    if data is None:
        raise ImporterError("WebMainResource has no WebResourceData")
    if isinstance(data, str):
        return data
    if not isinstance(data, (bytes, bytearray)):
        raise ImporterError("WebResourceData must be bytes or str")

    encoding = str(main.get("WebResourceTextEncodingName") or "utf-8")
    try:
        return bytes(data).decode(encoding, errors="replace")
    except LookupError:
        return bytes(data).decode("utf-8", errors="replace")


def _extract_profile_record(html: str, *, url: str | None) -> RawRecord:
    parser = _ProfileHTMLParser()
    parser.feed(html)
    parser.close()

    title = " ".join(parser.title_parts).strip()
    heading = parser.headings[0].strip() if parser.headings else ""
    og_title = parser.meta.get("og:title") or parser.meta.get("twitter:title") or ""
    display_name = _clean_name(heading or og_title or title)

    body_text = "\n".join(parser.text_parts)
    record: dict[str, Any] = {
        "display_name": display_name,
        "name": display_name,
        "source": "webarchive",
        "notes": None,
    }

    if url:
        record["external_id"] = url
        host = urlparse(url).hostname
        if host:
            record["organization"] = host

    description = (
        parser.meta.get("og:description")
        or parser.meta.get("description")
        or parser.meta.get("twitter:description")
        or ""
    ).strip()
    if description:
        record["notes"] = description

    for field_name, pattern in _LABEL_PATTERNS:
        match = pattern.search(body_text) or pattern.search(html)
        if match and not record.get(field_name):
            record[field_name] = match.group(1).strip()

    if not record.get("email"):
        email_match = _EMAIL_RE.search(body_text) or _EMAIL_RE.search(html)
        if email_match:
            record["email"] = email_match.group(0)

    if not record.get("phone"):
        phone_match = _PHONE_RE.search(body_text)
        if phone_match:
            candidate = phone_match.group(0).strip()
            digits = re.sub(r"\D", "", candidate)
            if len(digits) >= 7:
                record["phone"] = candidate

    location_meta = parser.meta.get("og:locale") or parser.meta.get("geo.region")
    if location_meta and not record.get("location"):
        record["location"] = location_meta

    # Keep a compact snippet for debugging / completeness notes.
    if not record.get("notes") and body_text:
        snippet = re.sub(r"\s+", " ", body_text).strip()
        record["notes"] = snippet[:400] or None

    return {key: value for key, value in record.items() if value not in (None, "")}


def _clean_name(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    # Common "Name | Site" / "Name - Site" title patterns.
    for separator in (" | ", " - ", " — ", " · "):
        if separator in text:
            text = text.split(separator, 1)[0].strip()
            break
    return text
