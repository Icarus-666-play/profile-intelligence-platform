"""Reports analytics: distributions and import trends.

```
Countries · Average Prices · Languages · Services
Duplicates · Monthly Imports · Import Trend
```
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import text

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
_SPLIT_RE = re.compile(r"[,/;|]")
_TREND_DAYS = 30
_MONTHS = 12
_TOP_N = 25


@dataclass(frozen=True, slots=True)
class NamedCount:
    """A labeled histogram bucket."""

    name: str
    count: int


@dataclass(frozen=True, slots=True)
class AveragePriceBucket:
    """Average price for a duration/currency bucket."""

    label: str
    average: float
    currency: str
    count: int


@dataclass(frozen=True, slots=True)
class PeriodCount:
    """Count for a calendar period (day or month)."""

    period: str
    count: int


@dataclass(frozen=True, slots=True)
class DuplicateRow:
    """One near-duplicate pair for Reports."""

    left_id: int
    right_id: int
    left_name: str
    right_name: str
    score: float


@dataclass(frozen=True, slots=True)
class ReportsAnalytics:
    """Distributions and trends shown on the Reports page."""

    countries: tuple[NamedCount, ...] = ()
    average_prices: tuple[AveragePriceBucket, ...] = ()
    languages: tuple[NamedCount, ...] = ()
    services: tuple[NamedCount, ...] = ()
    duplicates: tuple[DuplicateRow, ...] = ()
    monthly_imports: tuple[PeriodCount, ...] = ()
    import_trend: tuple[PeriodCount, ...] = ()


class ReportsAnalyticsService:
    """Build Reports analytics from profiles, child tables, and the ledger."""

    def __init__(
        self,
        repository: IProfileRepository,
        *,
        database: Database | None = None,
        analysis: AnalysisService | None = None,
        import_ledger: ImportFileLedger | None = None,
    ) -> None:
        self._repository = repository
        self._database = database
        self._analysis = analysis
        self._ledger = import_ledger

    def build(self, *, duplicate_limit: int = 25) -> ReportsAnalytics:
        """Collect the seven Reports panels."""
        profiles = list(self._repository.list_all(limit=100_000, offset=0))
        return ReportsAnalytics(
            countries=self._countries(profiles),
            average_prices=self._average_prices(profiles),
            languages=self._languages(profiles),
            services=self._services(),
            duplicates=self._duplicates(limit=duplicate_limit),
            monthly_imports=self._monthly_imports(profiles),
            import_trend=self._import_trend(profiles),
        )

    def _countries(self, profiles: Sequence[ProfileEntity]) -> tuple[NamedCount, ...]:
        counter: Counter[str] = Counter()
        for profile in profiles:
            country = _country_for_profile(profile)
            if country:
                counter[country] += 1
        return _named_counts(counter)

    def _languages(self, profiles: Sequence[ProfileEntity]) -> tuple[NamedCount, ...]:
        counter: Counter[str] = Counter()
        for profile in profiles:
            for language in _languages_for_profile(profile):
                counter[language] += 1
        return _named_counts(counter)

    def _services(self) -> tuple[NamedCount, ...]:
        if self._database is None:
            return ()
        try:
            with self._database.session() as session:
                rows = session.execute(
                    text(
                        "SELECT name, COUNT(*) AS total "
                        "FROM profile_services "
                        "WHERE available = 1 "
                        "GROUP BY name "
                        "ORDER BY total DESC, name ASC "
                        "LIMIT :limit"
                    ),
                    {"limit": _TOP_N},
                ).all()
        except Exception as exc:  # noqa: BLE001 — reports stay soft
            logger.debug("Services histogram failed: %s", exc)
            return ()
        return tuple(
            NamedCount(name=str(name), count=int(total))
            for name, total in rows
            if name
        )

    def _average_prices(
        self, profiles: Sequence[ProfileEntity]
    ) -> tuple[AveragePriceBucket, ...]:
        buckets: dict[tuple[str, str], list[float]] = defaultdict(list)
        if self._database is not None:
            try:
                with self._database.session() as session:
                    rows = session.execute(
                        text(
                            "SELECT duration, price, currency FROM profile_rates"
                        )
                    ).all()
                for duration, price, currency in rows:
                    parsed = _parse_number(str(price or ""), _PRICE_RE)
                    if parsed is None:
                        continue
                    label = str(duration or "Rate").strip() or "Rate"
                    code = str(currency or "EUR").upper() or "EUR"
                    buckets[(label, code)].append(parsed)
            except Exception as exc:  # noqa: BLE001 — reports stay soft
                logger.debug("Average prices query failed: %s", exc)
        if not buckets:
            for profile in profiles:
                raw = _raw_mapping(profile.raw_json)
                rates = raw.get("rates")
                if not isinstance(rates, list):
                    continue
                for item in rates:
                    if not isinstance(item, dict):
                        continue
                    parsed = _parse_number(str(item.get("price") or ""), _PRICE_RE)
                    if parsed is None:
                        continue
                    label = str(item.get("duration") or "Rate").strip() or "Rate"
                    code = str(item.get("currency") or "EUR").upper() or "EUR"
                    buckets[(label, code)].append(parsed)
        items = [
            AveragePriceBucket(
                label=label,
                average=round(sum(values) / len(values), 0),
                currency=currency,
                count=len(values),
            )
            for (label, currency), values in buckets.items()
            if values
        ]
        items.sort(key=lambda row: (-row.count, row.label, row.currency))
        return tuple(items[:_TOP_N])

    def _duplicates(self, *, limit: int) -> tuple[DuplicateRow, ...]:
        if self._analysis is None:
            return ()
        result = self._analysis.find_duplicates(limit=2_000)
        return tuple(
            DuplicateRow(
                left_id=pair.left_id,
                right_id=pair.right_id,
                left_name=pair.left_name,
                right_name=pair.right_name,
                score=round(float(pair.score.value), 3),
            )
            for pair in result.pairs[:limit]
        )

    def _monthly_imports(
        self, profiles: Sequence[ProfileEntity]
    ) -> tuple[PeriodCount, ...]:
        dates = self._import_dates(profiles)
        counter: Counter[str] = Counter()
        for day in dates:
            counter[day.strftime("%Y-%m")] += 1
        today = datetime.now(tz=UTC).date()
        periods: list[PeriodCount] = []
        year = today.year
        month = today.month
        for _ in range(_MONTHS):
            key = f"{year:04d}-{month:02d}"
            periods.append(PeriodCount(period=key, count=counter.get(key, 0)))
            month -= 1
            if month == 0:
                month = 12
                year -= 1
        periods.reverse()
        return tuple(periods)

    def _import_trend(
        self, profiles: Sequence[ProfileEntity]
    ) -> tuple[PeriodCount, ...]:
        dates = self._import_dates(profiles)
        counter: Counter[str] = Counter(day.isoformat() for day in dates)
        today = datetime.now(tz=UTC).date()
        start = today - timedelta(days=_TREND_DAYS - 1)
        return tuple(
            PeriodCount(
                period=(start + timedelta(days=offset)).isoformat(),
                count=counter.get((start + timedelta(days=offset)).isoformat(), 0),
            )
            for offset in range(_TREND_DAYS)
        )

    def _import_dates(self, profiles: Sequence[ProfileEntity]) -> list[date]:
        dates: list[date] = []
        if self._ledger is not None:
            try:
                entries = self._ledger.list_recent(limit=10_000)
            except Exception as exc:  # noqa: BLE001 — reports stay soft
                logger.debug("Ledger dates failed: %s", exc)
                entries = ()
            for entry in entries:
                parsed = _as_date(entry.imported_at)
                if parsed is not None:
                    dates.append(parsed)
        if dates:
            return dates
        for profile in profiles:
            parsed = _as_date(profile.created_at)
            if parsed is not None:
                dates.append(parsed)
        return dates


def reports_analytics_to_dict(data: ReportsAnalytics) -> dict[str, Any]:
    """Serialize :class:`ReportsAnalytics` for the REST API."""
    return {
        "countries": [
            {"name": row.name, "count": row.count} for row in data.countries
        ],
        "average_prices": [
            {
                "label": row.label,
                "average": row.average,
                "currency": row.currency,
                "count": row.count,
            }
            for row in data.average_prices
        ],
        "languages": [
            {"name": row.name, "count": row.count} for row in data.languages
        ],
        "services": [
            {"name": row.name, "count": row.count} for row in data.services
        ],
        "duplicate_pairs": [
            {
                "left_id": row.left_id,
                "right_id": row.right_id,
                "left_name": row.left_name,
                "right_name": row.right_name,
                "score": row.score,
            }
            for row in data.duplicates
        ],
        "monthly_imports": [
            {"period": row.period, "count": row.count}
            for row in data.monthly_imports
        ],
        "import_trend": [
            {"period": row.period, "count": row.count}
            for row in data.import_trend
        ],
    }


def _named_counts(counter: Counter[str]) -> tuple[NamedCount, ...]:
    items = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return tuple(
        NamedCount(name=name, count=count) for name, count in items[:_TOP_N]
    )


def _country_for_profile(profile: ProfileEntity) -> str | None:
    raw = _raw_mapping(profile.raw_json)
    for key in ("country", "nationality", "origin"):
        value = _as_text(raw.get(key))
        if value:
            return value
    location = profile.location
    if not location:
        return None
    text_value = location.strip()
    if not text_value:
        return None
    part = text_value.split(",")[-1].strip() if "," in text_value else text_value
    return part or None


def _languages_for_profile(profile: ProfileEntity) -> tuple[str, ...]:
    raw = _raw_mapping(profile.raw_json)
    value = raw.get("languages")
    if value is None:
        value = raw.get("language") or raw.get("speaks")
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(
            part.strip() for part in _SPLIT_RE.split(value) if part.strip()
        )
    if isinstance(value, (list, tuple)):
        items: list[str] = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name") or item.get("language")
                if name:
                    items.append(str(name).strip())
            else:
                text_value = str(item).strip()
                if text_value:
                    items.append(text_value)
        return tuple(items)
    return ()


def _raw_mapping(raw_json: str | None) -> dict[str, Any]:
    if not raw_json:
        return {}
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _parse_number(raw: str, pattern: re.Pattern[str]) -> float | None:
    match = pattern.search(raw.replace(" ", ""))
    if match is None:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def _as_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.date()
        return value.astimezone(UTC).date()
    if isinstance(value, date):
        return value
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        parsed = datetime.fromisoformat(text_value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return date.fromisoformat(text_value[:10])
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.date()
    return parsed.astimezone(UTC).date()


__all__ = [
    "AveragePriceBucket",
    "DuplicateRow",
    "NamedCount",
    "PeriodCount",
    "ReportsAnalytics",
    "ReportsAnalyticsService",
    "reports_analytics_to_dict",
]
