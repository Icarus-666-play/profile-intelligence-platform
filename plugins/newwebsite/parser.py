"""Parse NewWebsite source files into a raw document model.

```
plugins/
  newwebsite/
    parser.py
```
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from profile_intelligence.core.exceptions import ImporterError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike

logger = get_logger("importers.external.newwebsite.parser")

PARSER_VERSION = "0.1.0"
WEBSITE = "newwebsite"


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """Normalized parse result for a NewWebsite source file."""

    path: Path
    website: str = WEBSITE
    parser_version: str = PARSER_VERSION
    kind: str = "html"  # html | json
    url: str | None = None
    html: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    @property
    def is_complete(self) -> bool:
        """True when the document has usable HTML or JSON body."""
        if self.kind == "json":
            return bool(self.payload)
        return bool(self.html.strip())


class NewWebsiteParser:
    """Load ``.html`` / ``.json`` NewWebsite exports into :class:`ParsedDocument`."""

    def parse(self, path: PathLike) -> ParsedDocument:
        """Parse *path* according to its file extension."""
        resolved = Path(path)
        if not resolved.is_file():
            raise ImporterError(f"NewWebsite source not found: {resolved}")

        suffix = resolved.suffix.lower()
        if suffix == ".json":
            return self._parse_json(resolved)
        if suffix in {".html", ".htm"}:
            return self._parse_html(resolved)
        raise ImporterError(
            f"Unsupported NewWebsite source extension: {resolved.suffix}"
        )

    def looks_like_newwebsite(self, document: ParsedDocument) -> bool:
        """Heuristic content sniff for unmarked NewWebsite documents."""
        if document.kind == "json":
            source = str(document.payload.get("source") or "").lower()
            website = str(document.payload.get("website") or "").lower()
            return WEBSITE in {source, website} or "name" in document.payload
        lowered = document.html.lower()
        return (
            "newwebsite" in lowered
            or 'data-site="newwebsite"' in lowered
            or 'class="nw-profile"' in lowered
        )

    def _parse_html(self, path: Path) -> ParsedDocument:
        try:
            html = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ImporterError(
                f"Failed to read NewWebsite HTML: {path}",
                cause=exc,
            ) from exc
        return ParsedDocument(
            path=path,
            kind="html",
            html=html,
            url=None,
        )

    def _parse_json(self, path: Path) -> ParsedDocument:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ImporterError(
                f"Failed to read NewWebsite JSON: {path}",
                cause=exc,
            ) from exc

        if isinstance(raw, list):
            payload: dict[str, Any] = {"profiles": raw}
        elif isinstance(raw, dict):
            payload = dict(raw)
        else:
            raise ImporterError(
                "NewWebsite JSON must be an object or array of profiles"
            )

        return ParsedDocument(
            path=path,
            kind="json",
            payload=payload,
            url=str(payload.get("url") or "") or None,
            html=str(payload.get("html") or ""),
        )
