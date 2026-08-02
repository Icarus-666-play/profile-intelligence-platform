"""Tests for Search Show me filters on GET /api/profiles."""

from __future__ import annotations

import json
from pathlib import Path

from profile_intelligence.api import ApiApp
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.domain.value_objects.profile_children import (
    Rate,
    Review,
    Service,
)
from tests.test_api import _api_context, _request


def test_show_me_filters_country_price_service_language_rating(
    temp_root: Path,
) -> None:
    ctx, app_svc, container = _api_context(temp_root)
    try:
        repo = container.resolve(IProfileRepository)
        match, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Ana",
                location="Amsterdam, Netherlands",
                source="demo",
                raw_json=json.dumps(
                    {
                        "nationality": "Brazilian",
                        "country": "Netherlands",
                        "languages": ["English", "Portuguese"],
                        "services": ["Massage", "GFE"],
                        "rates": [
                            {"duration": "1 hour", "price": "250", "currency": "EUR"}
                        ],
                        "reviews": [
                            {"rating": "4.8", "author": "A"},
                            {"rating": "5.0", "author": "B"},
                        ],
                    }
                ),
                rates=(Rate(duration="1 hour", price="250", currency="EUR"),),
                reviews=(
                    Review(rating="4.8", author="A"),
                    Review(rating="5.0", author="B"),
                ),
                services=(
                    Service(name="Massage"),
                    Service(name="GFE"),
                ),
            )
        )
        other, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Bella",
                location="Paris, France",
                source="demo",
                raw_json=json.dumps(
                    {
                        "nationality": "French",
                        "languages": ["French"],
                        "services": ["Dinner"],
                        "rates": [
                            {"duration": "1 hour", "price": "400", "currency": "EUR"}
                        ],
                        "reviews": [{"rating": "4.0", "author": "C"}],
                    }
                ),
                rates=(Rate(duration="1 hour", price="400", currency="EUR"),),
                reviews=(Review(rating="4.0", author="C"),),
                services=(Service(name="Dinner"),),
            )
        )
        assert match.id is not None
        assert other.id is not None

        api = ApiApp(ctx)
        code, payload = _request(
            api,
            "GET",
            "/api/profiles",
            query=(
                "country=Brazilian&max_price=300&currency=EUR"
                "&service=Massage&language=English&min_rating=4.5"
            ),
        )
        assert code == 200
        ids = {row["id"] for row in payload["items"]}
        assert match.id in ids
        assert other.id not in ids
        assert payload["filters"]["country"] == "Brazilian"
        assert payload["filters"]["max_price"] == 300.0
        assert payload["filters"]["service"] == "Massage"
        assert payload["filters"]["language"] == "English"
        assert payload["filters"]["min_rating"] == 4.5
        item = next(row for row in payload["items"] if row["id"] == match.id)
        assert "Massage" in item["services"]
        assert item["nationality"] == "Brazilian"
    finally:
        app_svc.shutdown()
