"""Normalize extracted NewWebsite profiles into platform RawRecords.

```
plugins/
  newwebsite/
    normalizer.py
```
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from newwebsite.extractor import ExtractedProfile
from newwebsite.parser import PARSER_VERSION, WEBSITE, ParsedDocument
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.value_objects.importing import RawRecord

logger = get_logger("importers.external.newwebsite.normalizer")


class NewWebsiteNormalizer:
    """Map :class:`ExtractedProfile` onto importer RawRecord dictionaries."""

    def normalize(
        self,
        profile: ExtractedProfile,
        document: ParsedDocument,
        *,
        import_date: datetime | None = None,
    ) -> RawRecord:
        """Return a single RawRecord ready for the import pipeline."""
        stamp = import_date or datetime.now(tz=UTC)
        tags = ", ".join(profile.tags) if profile.tags else None

        record: dict[str, Any] = {
            "name": profile.name,
            "display_name": profile.name,
            "external_id": profile.external_id or profile.url,
            "email": profile.email,
            "phone": profile.phone,
            "title": profile.title,
            "organization": profile.organization or WEBSITE,
            "location": profile.location,
            "tags": tags,
            "notes": profile.notes,
            "url": profile.url or document.url,
            "source": WEBSITE,
            "metadata": {
                "import_date": stamp.isoformat(),
                "website": document.website,
                "parser_version": document.parser_version or PARSER_VERSION,
                "source_path": str(document.path),
                "kind": document.kind,
                "warnings": list(profile.warnings),
            },
        }
        logger.debug(
            "Normalized NewWebsite profile name=%r source=%s",
            record.get("display_name"),
            WEBSITE,
        )
        return record
