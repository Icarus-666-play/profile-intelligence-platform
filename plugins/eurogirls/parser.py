"""Safari ``.webarchive`` loader for EuroGirls profiles.

Converts binary plist archives into :class:`RawDocument`-ready HTML plus
subresource bytes. No SQL and no domain persistence here.
"""

from __future__ import annotations

import plistlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike

logger = get_logger("importers.external.eurogirls.parser")

PARSER_VERSION = "1.0.0"
WEBSITE = "eurogirls"


@dataclass(frozen=True, slots=True)
class WebSubresource:
    """One subresource from a Safari webarchive."""

    url: str
    data: bytes
    mime_type: str | None = None
    encoding: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedWebArchive:
    """Decoded Safari webarchive suitable for HTML extraction."""

    path: Path
    html: str
    url: str | None
    mime_type: str | None = None
    subresources: tuple[WebSubresource, ...] = field(default_factory=tuple)
    parser_version: str = PARSER_VERSION
    website: str = WEBSITE

    @property
    def is_complete(self) -> bool:
        """True when main HTML content is non-empty."""
        return bool(self.html.strip())


class WebArchiveParser:
    """Parse Safari ``.webarchive`` files into HTML + subresources."""

    def parse(self, path: PathLike) -> ParsedWebArchive:
        """Load *path* and return decoded main HTML with subresources."""
        resolved = Path(path).expanduser().resolve()
        archive = self._load_plist(resolved)
        main = archive.get("WebMainResource")
        if not isinstance(main, dict):
            raise ImporterError(
                f"WebArchive missing WebMainResource dictionary: {resolved}"
            )

        html = self._decode_resource_text(main)
        url = str(main.get("WebResourceURL") or "").strip() or None
        mime = str(main.get("WebResourceMIMEType") or "").strip() or None
        subresources = self._parse_subresources(archive.get("WebSubresources"))

        parsed = ParsedWebArchive(
            path=resolved,
            html=html,
            url=url,
            mime_type=mime,
            subresources=subresources,
        )
        logger.debug(
            "Parsed webarchive %s url=%s subresources=%d bytes=%d",
            resolved.name,
            url,
            len(subresources),
            len(html),
        )
        return parsed

    def looks_like_eurogirls(self, parsed: ParsedWebArchive) -> bool:
        """Heuristic: URL or HTML mentions EuroGirls."""
        haystacks = [
            (parsed.url or "").lower(),
            parsed.html[:4000].lower(),
            parsed.path.name.lower(),
        ]
        markers = (
            "eurogirls",
            "eurogirlsescort",
            "euro-girls",
            'data-site="eurogirls"',
            "data-site='eurogirls'",
        )
        return any(
            marker in haystack for haystack in haystacks for marker in markers
        )

    @staticmethod
    def _load_plist(path: Path) -> dict[str, Any]:
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

    @staticmethod
    def _decode_resource_text(resource: dict[str, Any]) -> str:
        data = resource.get("WebResourceData")
        if data is None:
            raise ImporterError("Web resource has no WebResourceData")
        if isinstance(data, str):
            return data
        if not isinstance(data, (bytes, bytearray)):
            raise ImporterError("WebResourceData must be bytes or str")

        encoding = str(resource.get("WebResourceTextEncodingName") or "utf-8")
        try:
            return bytes(data).decode(encoding, errors="replace")
        except LookupError:
            return bytes(data).decode("utf-8", errors="replace")

    def _parse_subresources(self, raw: object) -> tuple[WebSubresource, ...]:
        if not isinstance(raw, list):
            return ()
        items: list[WebSubresource] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            url = str(entry.get("WebResourceURL") or "").strip()
            data = entry.get("WebResourceData")
            if not url or not isinstance(data, (bytes, bytearray)):
                continue
            items.append(
                WebSubresource(
                    url=url,
                    data=bytes(data),
                    mime_type=str(entry.get("WebResourceMIMEType") or "")
                    or None,
                    encoding=str(entry.get("WebResourceTextEncodingName") or "")
                    or None,
                )
            )
        return tuple(items)
