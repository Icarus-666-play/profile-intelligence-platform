"""Normalize extracted EuroGirls profiles into platform RawRecords."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from eurogirls.extractor import ExtractedProfile
from eurogirls.parser import PARSER_VERSION, WEBSITE, ParsedWebArchive
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.value_objects.importing import RawRecord

logger = get_logger("importers.external.eurogirls.normalizer")


class EuroGirlsNormalizer:
    """Map :class:`ExtractedProfile` onto importer RawRecord dictionaries.

    Extra structured fields (rates, services, photos, physical attributes)
    are preserved for ``Profile.raw_json`` via the platform extractor.
    """

    def normalize(
        self,
        profile: ExtractedProfile,
        archive: ParsedWebArchive,
        *,
        import_date: datetime | None = None,
    ) -> RawRecord:
        """Return a single RawRecord ready for the import pipeline."""
        stamp = import_date or datetime.now(tz=UTC)
        location = self._compose_location(profile.city, profile.country)
        languages = ", ".join(profile.languages) if profile.languages else None
        tags = self._compose_tags(profile)
        notes = self._compose_notes(profile)

        record: dict[str, Any] = {
            "name": profile.name,
            "display_name": profile.name,
            "external_id": profile.profile_id or profile.url,
            "profile_id": profile.profile_id,
            "url": profile.url or archive.url,
            "source": WEBSITE,
            "organization": WEBSITE,
            "location": location,
            "country": profile.country,
            "city": profile.city,
            "nationality": profile.nationality,
            "languages": languages,
            "age": profile.age,
            "height": profile.height,
            "weight": profile.weight,
            "hair": profile.hair,
            "eyes": profile.eyes,
            "bust": profile.bust,
            "measurements": profile.measurements,
            "tags": tags,
            "notes": notes,
            "rates": [rate.to_mapping() for rate in profile.rates],
            "services": [service.to_mapping() for service in profile.services],
            "photos": [photo.to_mapping() for photo in profile.photos],
            "main_image": next(
                (
                    photo.to_mapping()
                    for photo in profile.photos
                    if photo.role == "main"
                ),
                None,
            ),
            "gallery": [
                photo.to_mapping()
                for photo in profile.photos
                if photo.role == "gallery"
            ],
            "metadata": {
                "import_date": stamp.isoformat(),
                "website": archive.website,
                "parser_version": archive.parser_version or PARSER_VERSION,
                "source_path": str(archive.path),
                "warnings": list(profile.warnings),
            },
        }
        cleaned = {
            key: value
            for key, value in record.items()
            if value not in (None, "", [], {})
        }
        logger.debug(
            "Normalized EuroGirls record name=%r keys=%d",
            cleaned.get("display_name"),
            len(cleaned),
        )
        return cleaned

    @staticmethod
    def _compose_location(city: str | None, country: str | None) -> str | None:
        parts = [part for part in (city, country) if part]
        return ", ".join(parts) if parts else None

    @staticmethod
    def _compose_tags(profile: ExtractedProfile) -> str | None:
        tags: list[str] = []
        if profile.nationality:
            tags.append(profile.nationality)
        tags.extend(profile.languages)
        for service in profile.services:
            if service.available:
                tags.append(service.name)
        # Deduplicate while preserving order.
        seen: set[str] = set()
        ordered: list[str] = []
        for tag in tags:
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(tag)
        return ", ".join(ordered) if ordered else None

    @staticmethod
    def _compose_notes(profile: ExtractedProfile) -> str | None:
        lines: list[str] = []
        physical = []
        for label, value in (
            ("Age", profile.age),
            ("Height", profile.height),
            ("Weight", profile.weight),
            ("Hair", profile.hair),
            ("Eyes", profile.eyes),
            ("Bust", profile.bust),
            ("Measurements", profile.measurements),
        ):
            if value:
                physical.append(f"{label}: {value}")
        if physical:
            lines.append("Physical — " + "; ".join(physical))
        if profile.rates:
            rate_bits = [
                f"{rate.duration}: {rate.price} {rate.currency}"
                f"{' incall' if rate.incall else ''}"
                f"{' outcall' if rate.outcall else ''}".strip()
                for rate in profile.rates
            ]
            lines.append("Rates — " + "; ".join(rate_bits))
        if profile.services:
            names = [
                service.name
                for service in profile.services
                if service.available
            ]
            if names:
                lines.append("Services — " + ", ".join(names))
        return "\n".join(lines) if lines else None
