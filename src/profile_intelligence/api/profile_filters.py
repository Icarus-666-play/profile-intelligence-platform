"""Apply Search "Show me" filters to enriched profile list payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProfileListFilters:
    """Optional filters for ``GET /api/profiles``."""

    country: str | None = None
    language: str | None = None
    service: str | None = None
    max_price: float | None = None
    min_rating: float | None = None
    currency: str | None = None

    @property
    def active(self) -> bool:
        return any(
            (
                self.country,
                self.language,
                self.service,
                self.max_price is not None,
                self.min_rating is not None,
            )
        )

    @classmethod
    def from_query(cls, query: dict[str, str]) -> ProfileListFilters:
        country = _optional_text(query.get("country") or query.get("nationality"))
        language = _optional_text(query.get("language") or query.get("languages"))
        service = _optional_text(query.get("service") or query.get("services"))
        currency = _optional_text(query.get("currency"))
        max_price = _optional_float(query.get("max_price"))
        min_rating = _optional_float(query.get("min_rating"))
        return cls(
            country=country,
            language=language,
            service=service,
            max_price=max_price,
            min_rating=min_rating,
            currency=currency.upper() if currency else None,
        )

    def to_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {}
        if self.country:
            payload["country"] = self.country
        if self.language:
            payload["language"] = self.language
        if self.service:
            payload["service"] = self.service
        if self.max_price is not None:
            payload["max_price"] = self.max_price
        if self.min_rating is not None:
            payload["min_rating"] = self.min_rating
        if self.currency:
            payload["currency"] = self.currency
        return payload


def apply_profile_filters(
    items: list[dict[str, Any]],
    filters: ProfileListFilters,
) -> list[dict[str, Any]]:
    """Return items that match all active filters (AND)."""
    if not filters.active:
        return items
    return [item for item in items if _matches(item, filters)]


def _matches(item: dict[str, Any], filters: ProfileListFilters) -> bool:
    if filters.country and not _matches_country(item, filters.country):
        return False
    if filters.language and not _matches_text_list(
        item.get("languages"), filters.language
    ):
        return False
    if filters.service and not _matches_text_list(
        item.get("services"), filters.service
    ):
        return False
    if filters.max_price is not None and not _matches_max_price(
        item, filters.max_price, filters.currency
    ):
        return False
    if filters.min_rating is not None:
        rating = item.get("rating")
        if rating is None:
            return False
        try:
            if float(rating) < filters.min_rating:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _matches_country(item: dict[str, Any], needle: str) -> bool:
    candidates = (
        item.get("country"),
        item.get("nationality"),
        item.get("location"),
    )
    target = needle.casefold()
    for value in candidates:
        if isinstance(value, str) and target in value.casefold():
            return True
    return False


def _matches_text_list(values: object, needle: str) -> bool:
    if not isinstance(values, (list, tuple)):
        return False
    target = needle.casefold()
    for value in values:
        if isinstance(value, str) and target in value.casefold():
            return True
    return False


def _matches_max_price(
    item: dict[str, Any],
    max_price: float,
    currency: str | None,
) -> bool:
    price = item.get("average_price")
    if price is None:
        return False
    try:
        if float(price) > max_price:
            return False
    except (TypeError, ValueError):
        return False
    if currency:
        code = str(item.get("average_price_currency") or "EUR").upper()
        if code != currency.upper():
            return False
    return True


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _optional_float(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


__all__ = [
    "ProfileListFilters",
    "apply_profile_filters",
]
