"""Tests for Profile → Rate → Service → Review → Photo → Availability."""

from __future__ import annotations

from sqlalchemy import func, select

from profile_intelligence.domain.entities.profile import ProfileDraft, ProfileExtractor
from profile_intelligence.domain.value_objects.profile_children import (
    Availability,
    Photo,
    Rate,
    Review,
    Service,
)
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.database.models_profile_children import (
    ProfileAvailability,
    ProfilePhoto,
    ProfileRate,
    ProfileReview,
    ProfileService,
)
from profile_intelligence.infrastructure.database.repository import (
    SQLiteProfileRepository,
)


def _full_draft() -> ProfileDraft:
    return ProfileDraft(
        display_name="Sophia",
        external_id="eg-1",
        source="eurogirls",
        rates=(
            Rate(duration="1 hour", price="300", currency="EUR", incall=True),
            Rate(duration="2 hours", price="500", currency="EUR", outcall=True),
        ),
        services=(
            Service(name="GFE", available=True),
            Service(name="Dinner", available=False),
        ),
        reviews=(
            Review(text="Great", author="Pat", rating="5"),
        ),
        photos=(
            Photo(original_url="https://example.com/main.jpg", role="main"),
            Photo(original_url="https://example.com/g1.jpg", role="gallery"),
        ),
        availability=(
            Availability(
                day_of_week="monday",
                start_time="10:00",
                end_time="18:00",
                status="available",
            ),
        ),
    )


def test_extractor_parses_child_collections() -> None:
    extractor = ProfileExtractor(default_source="eurogirls")
    draft = extractor.extract(
        {
            "name": "Ada",
            "rates": [{"duration": "1 hour", "price": "200", "incall": True}],
            "services": [{"name": "GFE"}, "Dinner"],
            "reviews": [{"body": "Nice", "author": "Sam"}],
            "photos": [{"url": "https://example.com/a.jpg", "role": "main"}],
            "availability": [
                {"day": "tuesday", "from": "12:00", "to": "20:00"},
            ],
        }
    )
    assert len(draft.rates) == 1
    assert draft.rates[0].incall is True
    assert len(draft.services) == 2
    assert draft.reviews[0].text == "Nice"
    assert draft.photos[0].role == "main"
    assert draft.availability[0].day_of_week == "tuesday"


def test_extractor_photo_fallback_from_main_and_gallery() -> None:
    extractor = ProfileExtractor()
    draft = extractor.extract(
        {
            "name": "Bee",
            "main_image": {"original_url": "https://example.com/m.jpg"},
            "gallery": ["https://example.com/g.jpg"],
        }
    )
    assert len(draft.photos) == 2
    assert draft.photos[0].role == "main"
    assert draft.photos[1].original_url.endswith("g.jpg")


def test_upsert_draft_persists_and_replaces_children(database: Database) -> None:
    repo = SQLiteProfileRepository(database)
    created, was_created = repo.upsert_draft(_full_draft())
    assert was_created is True
    assert created.id is not None

    with database.session() as session:
        assert session.scalar(select(func.count()).select_from(ProfileRate)) == 2
        assert session.scalar(select(func.count()).select_from(ProfileService)) == 2
        assert session.scalar(select(func.count()).select_from(ProfileReview)) == 1
        assert session.scalar(select(func.count()).select_from(ProfilePhoto)) == 2
        assert (
            session.scalar(select(func.count()).select_from(ProfileAvailability)) == 1
        )

    updated_draft = ProfileDraft(
        display_name="Sophia",
        external_id="eg-1",
        source="eurogirls",
        rates=(Rate(duration="overnight", price="1200", currency="EUR"),),
        services=(Service(name="Travel"),),
        reviews=(),
        photos=(Photo(original_url="https://example.com/only.jpg"),),
        availability=(),
    )
    _, was_created = repo.upsert_draft(updated_draft)
    assert was_created is False

    with database.session() as session:
        rates = list(session.scalars(select(ProfileRate)).all())
        services = list(session.scalars(select(ProfileService)).all())
        reviews = list(session.scalars(select(ProfileReview)).all())
        photos = list(session.scalars(select(ProfilePhoto)).all())
        availability = list(session.scalars(select(ProfileAvailability)).all())

    assert len(rates) == 1
    assert rates[0].duration == "overnight"
    assert len(services) == 1
    assert services[0].name == "Travel"
    assert reviews == []
    assert len(photos) == 1
    assert availability == []


def test_delete_profile_cascades_children(database: Database) -> None:
    repo = SQLiteProfileRepository(database)
    profile, _ = repo.upsert_draft(_full_draft())
    assert repo.delete(profile.id) is True

    with database.session() as session:
        assert session.scalar(select(func.count()).select_from(ProfileRate)) == 0
        assert session.scalar(select(func.count()).select_from(ProfileService)) == 0
        assert session.scalar(select(func.count()).select_from(ProfileReview)) == 0
        assert session.scalar(select(func.count()).select_from(ProfilePhoto)) == 0
        assert (
            session.scalar(select(func.count()).select_from(ProfileAvailability)) == 0
        )
