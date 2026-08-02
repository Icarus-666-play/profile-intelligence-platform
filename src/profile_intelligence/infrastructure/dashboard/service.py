"""Dashboard metrics for CLI and React UI.

```
Profiles · Imported Today · Countries · Average Price · Average Rating

Latest Imports · Newest Profiles · Duplicates · Import Queue
```
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.repositories import (
    IProfileRepository,
    ProfileEntity,
)
from profile_intelligence.infrastructure.analysis import AnalysisService
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.importers.import_ledger import (
    ImportFileLedger,
)

logger = get_logger(__name__)

_PRICE_RE = re.compile(r"(\d+(?:[.,]\d+)?)")
_RATING_RE = re.compile(r"(\d+(?:[.,]\d+)?)")


@dataclass(frozen=True, slots=True)
class LatestImportItem:
    """One recent ledger import."""

    path: str
    imported_at: str | None
    file_size: int
    name: str


@dataclass(frozen=True, slots=True)
class ImportQueueItem:
    """Inbox file waiting to be imported."""

    path: str
    file_size: int
    name: str


@dataclass(frozen=True, slots=True)
class DashboardDuplicateItem:
    """One near-duplicate pair for the dashboard panel."""

    left_id: int
    right_id: int
    left_name: str
    right_name: str
    score: float


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    """Aggregated dashboard metrics for the local profile database."""

    total_profiles: int
    scored_profiles: int
    average_score: float | None
    by_source: tuple[tuple[str, int], ...]
    top_profiles: tuple[ProfileEntity, ...]
    incomplete_profiles: tuple[ProfileEntity, ...]
    imported_today: int = 0
    countries: int = 0
    average_price: float | None = None
    average_price_currency: str = "EUR"
    average_rating: float | None = None
    newest_profiles: tuple[ProfileEntity, ...] = field(default_factory=tuple)
    latest_imports: tuple[LatestImportItem, ...] = field(default_factory=tuple)
    duplicates: tuple[DashboardDuplicateItem, ...] = field(default_factory=tuple)
    import_queue: tuple[ImportQueueItem, ...] = field(default_factory=tuple)


class DashboardService:
    """Build local dashboard snapshots for CLI and React UI."""

    def __init__(
        self,
        repository: IProfileRepository,
        *,
        database: Database | None = None,
        analysis: AnalysisService | None = None,
        import_ledger: ImportFileLedger | None = None,
        config: AppConfig | None = None,
    ) -> None:
        self._repository = repository
        self._database = database
        self._analysis = analysis
        self._ledger = import_ledger
        self._config = config

    def snapshot(
        self,
        *,
        top_limit: int = 5,
        incomplete_limit: int = 5,
        list_limit: int = 8,
    ) -> DashboardSnapshot:
        """Collect KPI counts and operator lists."""
        profiles = list(self._repository.list_all(limit=100_000, offset=0))
        scores = [row.score for row in profiles if row.score is not None]
        average = round(sum(scores) / len(scores), 1) if scores else None

        source_counts = Counter((row.source or "unknown") for row in profiles)
        by_source = tuple(
            sorted(source_counts.items(), key=lambda item: (-item[1], item[0]))
        )

        ranked = sorted(
            profiles,
            key=lambda row: (
                row.score is not None,
                row.score if row.score is not None else -1,
                row.display_name.lower(),
            ),
            reverse=True,
        )
        incomplete = sorted(
            profiles,
            key=lambda row: (
                row.score is None,
                row.score if row.score is not None else 10_000,
                row.display_name.lower(),
            ),
        )
        newest = sorted(
            profiles,
            key=_created_sort_key,
            reverse=True,
        )

        today = datetime.now(tz=UTC).date()
        imported_today = sum(
            1
            for row in profiles
            if row.created_at is not None and _as_utc_date(row.created_at) == today
        )
        countries = len(
            {
                country
                for row in profiles
                if (country := _country_from_location(row.location)) is not None
            }
        )
        average_price, currency = self._average_price()
        average_rating = self._average_rating()

        snapshot = DashboardSnapshot(
            total_profiles=len(profiles),
            scored_profiles=len(scores),
            average_score=average,
            by_source=by_source,
            top_profiles=tuple(ranked[:top_limit]),
            incomplete_profiles=tuple(incomplete[:incomplete_limit]),
            imported_today=imported_today,
            countries=countries,
            average_price=average_price,
            average_price_currency=currency,
            average_rating=average_rating,
            newest_profiles=tuple(newest[:list_limit]),
            latest_imports=self._latest_imports(limit=list_limit),
            duplicates=self._duplicates(limit=list_limit),
            import_queue=self._import_queue(limit=list_limit),
        )
        logger.debug(
            "Dashboard snapshot: total=%d today=%d countries=%d",
            snapshot.total_profiles,
            snapshot.imported_today,
            snapshot.countries,
        )
        return snapshot

    def render_text(self, snapshot: DashboardSnapshot | None = None) -> str:
        """Render a plain-text console dashboard."""
        data = snapshot or self.snapshot()
        price = (
            f"{_currency_symbol(data.average_price_currency)}"
            f"{data.average_price:.0f}"
            if data.average_price is not None
            else "n/a"
        )
        rating = (
            f"{data.average_rating:.2f}"
            if data.average_rating is not None
            else "n/a"
        )
        lines = [
            "Profile Intelligence Platform — Dashboard",
            "=" * 44,
            f"Profiles: {data.total_profiles}",
            f"Imported today: {data.imported_today}",
            f"Countries: {data.countries}",
            f"Average price: {price}",
            f"Average rating: {rating}",
            f"Scored:   {data.scored_profiles}",
            (
                f"Average confidence score (0-100): {data.average_score}"
                if data.average_score is not None
                else "Average confidence score (0-100): n/a"
            ),
            "",
            "By source:",
        ]
        if data.by_source:
            for source, count in data.by_source:
                lines.append(f"  - {source}: {count}")
        else:
            lines.append("  (none)")

        lines.extend(["", "Newest profiles:"])
        lines.extend(_profile_lines(data.newest_profiles) or ["  (none)"])

        lines.extend(["", "Top confidence:"])
        lines.extend(_profile_lines(data.top_profiles) or ["  (none)"])

        lines.extend(["", "Needs attention (lowest confidence):"])
        lines.extend(_profile_lines(data.incomplete_profiles) or ["  (none)"])

        lines.extend(
            [
                "",
                "Open the Dashboard UI: pip-app ui",
                "Or: pip-app search | compare | export",
            ]
        )
        return "\n".join(lines)

    def _average_price(self) -> tuple[float | None, str]:
        if self._database is None:
            return None, "EUR"
        try:
            with self._database.session() as session:
                rows = session.execute(
                    text("SELECT price, currency FROM profile_rates")
                ).all()
        except Exception as exc:  # noqa: BLE001 — dashboard must stay soft
            logger.debug("Average price query failed: %s", exc)
            return None, "EUR"
        values: list[float] = []
        currency_counts: Counter[str] = Counter()
        for price_raw, currency_raw in rows:
            parsed = _parse_number(str(price_raw or ""), _PRICE_RE)
            if parsed is None:
                continue
            values.append(parsed)
            currency_counts[str(currency_raw or "EUR").upper() or "EUR"] += 1
        if not values:
            return None, "EUR"
        currency = currency_counts.most_common(1)[0][0] if currency_counts else "EUR"
        return round(sum(values) / len(values), 0), currency

    def _average_rating(self) -> float | None:
        if self._database is None:
            return None
        try:
            with self._database.session() as session:
                rows = session.execute(
                    text("SELECT rating FROM profile_reviews WHERE rating IS NOT NULL")
                ).all()
        except Exception as exc:  # noqa: BLE001 — dashboard must stay soft
            logger.debug("Average rating query failed: %s", exc)
            return None
        values = [
            value
            for (raw,) in rows
            if (value := _parse_number(str(raw or ""), _RATING_RE)) is not None
        ]
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    def _latest_imports(self, *, limit: int) -> tuple[LatestImportItem, ...]:
        if self._ledger is None:
            return ()
        try:
            entries = self._ledger.list_recent(limit=limit)
        except Exception as exc:  # noqa: BLE001 — dashboard must stay soft
            logger.debug("Latest imports query failed: %s", exc)
            return ()
        return tuple(
            LatestImportItem(
                path=entry.path,
                imported_at=entry.imported_at,
                file_size=entry.file_size,
                name=Path(entry.path).name,
            )
            for entry in entries
        )

    def _duplicates(self, *, limit: int) -> tuple[DashboardDuplicateItem, ...]:
        if self._analysis is None:
            return ()
        result = self._analysis.find_duplicates(limit=2_000)
        items = [
            DashboardDuplicateItem(
                left_id=pair.left_id,
                right_id=pair.right_id,
                left_name=pair.left_name,
                right_name=pair.right_name,
                score=round(float(pair.score.value), 3),
            )
            for pair in result.pairs[:limit]
        ]
        return tuple(items)

    def _import_queue(self, *, limit: int) -> tuple[ImportQueueItem, ...]:
        if self._config is None or self._ledger is None:
            return ()
        inbox = self._config.daily_import_dir
        if not inbox.is_dir():
            return ()
        candidates = sorted(
            path
            for path in inbox.rglob("*")
            if path.is_file() and not path.name.startswith(".")
        )
        new_files = self._ledger.detect_new(candidates)[:limit]
        items: list[ImportQueueItem] = []
        for path in new_files:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            items.append(
                ImportQueueItem(path=str(path), file_size=size, name=path.name)
            )
        return tuple(items)


def _profile_lines(profiles: Sequence[ProfileEntity]) -> list[str]:
    lines: list[str] = []
    for profile in profiles:
        score = profile.score if profile.score is not None else "-"
        lines.append(
            f"  [{profile.id}] {profile.display_name} | "
            f"{profile.source or '-'} | confidence={score}"
        )
    return lines


def _country_from_location(location: str | None) -> str | None:
    if not location:
        return None
    text = location.strip()
    if not text:
        return None
    part = text.split(",")[-1].strip() if "," in text else text
    return part or None


def _parse_number(raw: str, pattern: re.Pattern[str]) -> float | None:
    match = pattern.search(raw.replace(" ", ""))
    if match is None:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _as_utc_date(value: datetime) -> object:
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(UTC).date()


def _created_sort_key(row: ProfileEntity) -> tuple[bool, datetime]:
    created = row.created_at
    if created is None:
        return (False, datetime.min.replace(tzinfo=UTC))
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    return (True, created.astimezone(UTC))


def _currency_symbol(code: str) -> str:
    return {"EUR": "€", "USD": "$", "GBP": "£"}.get(code.upper(), f"{code} ")


__all__ = [
    "DashboardDuplicateItem",
    "DashboardService",
    "DashboardSnapshot",
    "ImportQueueItem",
    "LatestImportItem",
]
