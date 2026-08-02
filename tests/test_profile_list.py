"""Tests for Search profile list enrichment fields."""

from __future__ import annotations

import json
from pathlib import Path

from profile_intelligence.api import ApiApp
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import IProfileRepository
from profile_intelligence.domain.value_objects.profile_children import Photo, Rate, Review
from tests.test_api import _api_context, _request


def test_profile_list_includes_search_row_fields(temp_root: Path) -> None:
    ctx, app_svc, container = _api_context(temp_root)
    try:
        repo = container.resolve(IProfileRepository)
        raw = {
            "display_name": "Giulia",
            "age": "28",
            "nationality": "Italian",
            "country": "Netherlands",
            "languages": "English, Italian, Dutch",
            "main_image": {
                "original_url": "https://cdn.example.com/giulia.jpg",
                "role": "main",
            },
            "rates": [
                {"duration": "1 hour", "price": "200", "currency": "EUR"},
                {"duration": "2 hours", "price": "350", "currency": "EUR"},
            ],
            "reviews": [
                {"rating": "4.5", "author": "A", "text": "Great"},
                {"rating": "5", "author": "B", "text": "Excellent"},
            ],
        }
        created, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="Giulia",
                location="Amsterdam, Netherlands",
                source="eurogirlsescort",
                raw_json=json.dumps(raw),
                rates=(
                    Rate(duration="1 hour", price="200", currency="EUR"),
                    Rate(duration="2 hours", price="350", currency="EUR"),
                ),
                reviews=(
                    Review(rating="4.5", author="A", text="Great"),
                    Review(rating="5", author="B", text="Excellent"),
                ),
                photos=(
                    Photo(
                        original_url="https://cdn.example.com/giulia.jpg",
                        role="main",
                    ),
                ),
            )
        )
        assert created.id is not None

        api = ApiApp(ctx)
        code, payload = _request(api, "GET", "/api/profiles")
        assert code == 200
        item = next(row for row in payload["items"] if row["id"] == created.id)
        assert item["photo"] == "https://cdn.example.com/giulia.jpg"
        assert item["age"] == "28"
        assert item["country"] == "Netherlands"
        assert item["languages"] == ["English", "Italian", "Dutch"]
        assert item["rating"] == 4.75
        assert item["average_price"] == 275.0
        assert item["average_price_currency"] == "EUR"
        assert item["imported"] is not None
    finally:
        app_svc.shutdown()


def test_profile_list_falls_back_to_child_tables(temp_root: Path) -> None:
    ctx, app_svc, container = _api_context(temp_root)
    try:
        repo = container.resolve(IProfileRepository)
        created, _ = repo.upsert_draft(
            ProfileDraft(
                display_name="No Raw",
                location="Berlin, Germany",
                source="manual",
                rates=(Rate(duration="1h", price="150", currency="EUR"),),
                reviews=(Review(rating="4", author="X"),),
                photos=(
                    Photo(
                        original_url="https://cdn.example.com/noraw.jpg",
                        role="main",
                    ),
                ),
            )
        )
        assert created.id is not None

        api = ApiApp(ctx)
        code, payload = _request(api, "GET", "/api/profiles")
        assert code == 200
        item = next(row for row in payload["items"] if row["id"] == created.id)
        assert item["photo"] == "https://cdn.example.com/noraw.jpg"
        assert item["country"] == "Germany"
        assert item["rating"] == 4.0
        assert item["average_price"] == 150.0
        assert item["average_price_currency"] == "EUR"
    finally:
        app_svc.shutdown()
