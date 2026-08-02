"""Aggregate and render rich import statistics."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import ProfileEntity


@dataclass(frozen=True, slots=True)
class ImportStats:
    """Counts reported after an import run.

    Example report::

        Imported:

        2 profiles

        35 services

        12 rates

        18 images

        0 duplicates

        Execution time:

        0.8 sec
    """

    profiles: int = 0
    services: int = 0
    rates: int = 0
    images: int = 0
    duplicates: int = 0
    execution_seconds: float = 0.0

    def merge(self, other: ImportStats) -> ImportStats:
        """Return combined stats (execution times add)."""
        return ImportStats(
            profiles=self.profiles + other.profiles,
            services=self.services + other.services,
            rates=self.rates + other.rates,
            images=self.images + other.images,
            duplicates=self.duplicates + other.duplicates,
            execution_seconds=(
                self.execution_seconds + other.execution_seconds
            ),
        )

    def render(self) -> str:
        """Format the human-readable import summary block."""
        seconds = f"{self.execution_seconds:.1f}"
        return (
            "Imported:\n"
            "\n"
            f"{self.profiles} profiles\n"
            "\n"
            f"{self.services} services\n"
            "\n"
            f"{self.rates} rates\n"
            "\n"
            f"{self.images} images\n"
            "\n"
            f"{self.duplicates} duplicates\n"
            "\n"
            "Execution time:\n"
            "\n"
            f"{seconds} sec"
        )


def collect_import_stats(
    *,
    drafts: Sequence[ProfileDraft] = (),
    entities: Sequence[ProfileEntity] = (),
    duplicates: int = 0,
    profiles: int | None = None,
    execution_seconds: float = 0.0,
) -> ImportStats:
    """Count services / rates / images from draft children or raw payloads."""
    if drafts:
        services = sum(len(draft.services) for draft in drafts)
        rates = sum(len(draft.rates) for draft in drafts)
        images = sum(len(draft.photos) for draft in drafts)
        # Fall back to raw_json when child tuples are empty (legacy drafts).
        if services == 0 and rates == 0 and images == 0:
            sources = [
                payload
                for draft in drafts
                if (payload := _payload_from_raw_json(draft.raw_json)) is not None
            ]
            services = sum(_count_list(item.get("services")) for item in sources)
            rates = sum(_count_list(item.get("rates")) for item in sources)
            images = sum(_count_images(item) for item in sources)
    else:
        sources = [
            payload
            for entity in entities
            if (payload := _payload_from_raw_json(entity.raw_json)) is not None
        ]
        services = sum(_count_list(item.get("services")) for item in sources)
        rates = sum(_count_list(item.get("rates")) for item in sources)
        images = sum(_count_images(item) for item in sources)

    profile_count = (
        profiles
        if profiles is not None
        else (len(entities) if entities else len(drafts))
    )
    return ImportStats(
        profiles=profile_count,
        services=services,
        rates=rates,
        images=images,
        duplicates=duplicates,
        execution_seconds=execution_seconds,
    )


def aggregate_stats(items: Iterable[ImportStats]) -> ImportStats:
    """Sum a sequence of :class:`ImportStats`."""
    total = ImportStats()
    for item in items:
        total = total.merge(item)
    return total


def _payload_from_raw_json(raw_json: str | None) -> dict[str, Any] | None:
    if not raw_json:
        return None
    try:
        payload = json.loads(raw_json)
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _count_list(value: object) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def _count_images(payload: Mapping[str, Any]) -> int:
    photos = payload.get("photos")
    if isinstance(photos, list):
        return len(photos)
    gallery = payload.get("gallery")
    main = payload.get("main_image")
    count = _count_list(gallery)
    if isinstance(main, Mapping) or (
        isinstance(main, str) and main.strip()
    ):
        count += 1
    return count
