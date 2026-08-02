"""Enrich profile list/detail payloads for Search rows and cards."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from sqlalchemy import text

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.repositories import ProfileEntity
from profile_intelligence.infrastructure.database.connection import Database

logger = get_logger(__name__)

_PRICE_RE = re.compile(r"(\d+(?:[.,]\d+)?)")
_RATING_RE = re.compile(r"(\d+(?:[.,]\d+)?)")
_SPLIT_RE = re.compile(r"[,/;|]")


def list_fields_from_profile(profile: ProfileEntity) -> dict[str, Any]:
    """Derive Search-row fields from ``raw_json`` and core profile columns."""
    raw = _raw_mapping(profile.raw_json)
    price, currency = _average_price_from_raw(raw)
    return {
        "photo": _photo_from_raw(raw),
        "age": _as_optional_text(raw.get("age")),
        "country": _country_from_raw(raw, profile.location),
        "nationality": _as_optional_text(
            raw.get("nationality") or raw.get("origin")
        ),
        "languages": list(_languages_from_raw(raw)),
        "services": list(_services_from_raw(raw)),
        "rating": _average_rating_from_raw(raw),
        "average_price": price,
        "average_price_currency": currency,
        "imported": (
            profile.created_at.isoformat() if profile.created_at is not None else None
        ),
    }


def enrich_list_fields_from_database(
    profiles: Sequence[ProfileEntity],
    database: Database | None,
    items: list[dict[str, Any]],
) -> None:
    """Fill missing photo / rating / average price from child tables in place."""
    if database is None or not profiles:
        return
    ids = [int(profile.id) for profile in profiles if profile.id is not None]
    if not ids:
        return
    by_id = {
        int(profile.id): index
        for index, profile in enumerate(profiles)
        if profile.id is not None
    }
    photos = _batch_photos(database, ids)
    ratings = _batch_ratings(database, ids)
    prices = _batch_prices(database, ids)
    services = _batch_services(database, ids)
    for profile_id, index in by_id.items():
        item = items[index]
        if not item.get("photo") and profile_id in photos:
            item["photo"] = photos[profile_id]
        if item.get("rating") is None and profile_id in ratings:
            item["rating"] = ratings[profile_id]
        if item.get("average_price") is None and profile_id in prices:
            price, currency = prices[profile_id]
            item["average_price"] = price
            item["average_price_currency"] = currency
        existing_services = item.get("services")
        if not existing_services and profile_id in services:
            item["services"] = services[profile_id]


def _raw_mapping(raw_json: str | None) -> dict[str, Any]:
    if not raw_json:
        return {}
    try:
        payload = json.loads(raw_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text_value = str(value).strip()
    return text_value or None


def _photo_from_raw(raw: dict[str, Any]) -> str | None:
    candidates: list[object] = [raw.get("main_image")]
    photos = raw.get("photos")
    if isinstance(photos, list):
        candidates.extend(photos)
    gallery = raw.get("gallery")
    if isinstance(gallery, list):
        candidates.extend(gallery)
    candidates.extend((raw.get("picture"), raw.get("photo"), raw.get("image")))
    for candidate in candidates:
        url = _photo_url(candidate)
        if url:
            return url
    return None


def _photo_url(value: object) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        return _as_optional_text(
            value.get("original_url") or value.get("url") or value.get("src")
        )
    return None


def _country_from_raw(raw: dict[str, Any], location: str | None) -> str | None:
    for key in ("country", "nationality", "origin"):
        value = _as_optional_text(raw.get(key))
        if value:
            return value
    if not location:
        return None
    text_value = location.strip()
    if not text_value:
        return None
    part = text_value.split(",")[-1].strip() if "," in text_value else text_value
    return part or None


def _languages_from_raw(raw: dict[str, Any]) -> tuple[str, ...]:
    value = raw.get("languages")
    if value is None:
        value = raw.get("language") or raw.get("speaks")
    return _string_list(value)


def _services_from_raw(raw: dict[str, Any]) -> tuple[str, ...]:
    value = raw.get("services")
    if value is None:
        value = raw.get("service") or raw.get("offers")
    return _string_list(value)


def _string_list(value: object) -> tuple[str, ...]:
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
                name = (
                    item.get("name")
                    or item.get("language")
                    or item.get("service")
                    or item.get("title")
                )
                if name:
                    items.append(str(name).strip())
            else:
                text_value = str(item).strip()
                if text_value:
                    items.append(text_value)
        return tuple(items)
    return ()


def _average_price_from_raw(raw: dict[str, Any]) -> tuple[float | None, str | None]:
    rates = raw.get("rates")
    if not isinstance(rates, list):
        return None, None
    values: list[float] = []
    currencies: list[str] = []
    for item in rates:
        if not isinstance(item, dict):
            continue
        parsed = _parse_number(str(item.get("price") or ""), _PRICE_RE)
        if parsed is None:
            continue
        values.append(parsed)
        currencies.append(str(item.get("currency") or "EUR").upper() or "EUR")
    if not values:
        return None, None
    currency = max(set(currencies), key=currencies.count) if currencies else "EUR"
    return round(sum(values) / len(values), 0), currency


def _average_rating_from_raw(raw: dict[str, Any]) -> float | None:
    reviews = raw.get("reviews")
    if not isinstance(reviews, list):
        return None
    values: list[float] = []
    for item in reviews:
        if not isinstance(item, dict):
            continue
        parsed = _parse_number(str(item.get("rating") or ""), _RATING_RE)
        if parsed is not None:
            values.append(parsed)
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _batch_photos(database: Database, ids: list[int]) -> dict[int, str]:
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    params = {f"id{i}": profile_id for i, profile_id in enumerate(ids)}
    try:
        with database.session() as session:
            rows = session.execute(
                text(
                    "SELECT profile_id, original_url, role "
                    f"FROM profile_photos WHERE profile_id IN ({placeholders}) "
                    "ORDER BY CASE WHEN role = 'main' THEN 0 ELSE 1 END, id"
                ),
                params,
            ).all()
    except Exception as exc:  # noqa: BLE001 — list UI must stay soft
        logger.debug("Batch photo lookup failed: %s", exc)
        return {}
    out: dict[int, str] = {}
    for profile_id, url, _role in rows:
        key = int(profile_id)
        if key not in out and url:
            out[key] = str(url)
    return out


def _batch_ratings(database: Database, ids: list[int]) -> dict[int, float]:
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    params = {f"id{i}": profile_id for i, profile_id in enumerate(ids)}
    try:
        with database.session() as session:
            rows = session.execute(
                text(
                    "SELECT profile_id, rating FROM profile_reviews "
                    f"WHERE profile_id IN ({placeholders}) AND rating IS NOT NULL"
                ),
                params,
            ).all()
    except Exception as exc:  # noqa: BLE001 — list UI must stay soft
        logger.debug("Batch rating lookup failed: %s", exc)
        return {}
    buckets: dict[int, list[float]] = defaultdict(list)
    for profile_id, rating_raw in rows:
        parsed = _parse_number(str(rating_raw or ""), _RATING_RE)
        if parsed is not None:
            buckets[int(profile_id)].append(parsed)
    return {
        profile_id: round(sum(values) / len(values), 2)
        for profile_id, values in buckets.items()
        if values
    }


def _batch_prices(
    database: Database, ids: list[int]
) -> dict[int, tuple[float, str]]:
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    params = {f"id{i}": profile_id for i, profile_id in enumerate(ids)}
    try:
        with database.session() as session:
            rows = session.execute(
                text(
                    "SELECT profile_id, price, currency FROM profile_rates "
                    f"WHERE profile_id IN ({placeholders})"
                ),
                params,
            ).all()
    except Exception as exc:  # noqa: BLE001 — list UI must stay soft
        logger.debug("Batch price lookup failed: %s", exc)
        return {}
    prices: dict[int, list[float]] = defaultdict(list)
    currencies: dict[int, list[str]] = defaultdict(list)
    for profile_id, price_raw, currency_raw in rows:
        parsed = _parse_number(str(price_raw or ""), _PRICE_RE)
        if parsed is None:
            continue
        key = int(profile_id)
        prices[key].append(parsed)
        currencies[key].append(str(currency_raw or "EUR").upper() or "EUR")
    out: dict[int, tuple[float, str]] = {}
    for profile_id, values in prices.items():
        codes = currencies.get(profile_id) or ["EUR"]
        currency = max(set(codes), key=codes.count)
        out[profile_id] = (round(sum(values) / len(values), 0), currency)
    return out


def _batch_services(database: Database, ids: list[int]) -> dict[int, list[str]]:
    placeholders = ", ".join(f":id{i}" for i in range(len(ids)))
    params = {f"id{i}": profile_id for i, profile_id in enumerate(ids)}
    try:
        with database.session() as session:
            rows = session.execute(
                text(
                    "SELECT profile_id, name FROM profile_services "
                    f"WHERE profile_id IN ({placeholders}) "
                    "ORDER BY id"
                ),
                params,
            ).all()
    except Exception as exc:  # noqa: BLE001 — list UI must stay soft
        logger.debug("Batch service lookup failed: %s", exc)
        return {}
    buckets: dict[int, list[str]] = defaultdict(list)
    for profile_id, name in rows:
        text_value = str(name or "").strip()
        if text_value:
            buckets[int(profile_id)].append(text_value)
    return dict(buckets)


def _parse_number(raw: str, pattern: re.Pattern[str]) -> float | None:
    match = pattern.search(raw.replace(" ", ""))
    if match is None:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


__all__ = [
    "enrich_list_fields_from_database",
    "list_fields_from_profile",
]
