"""Tests for IProfile / IRate / IService / IReview / IPhoto repositories."""

from __future__ import annotations

from profile_intelligence.bootstrap import build_container
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.domain.interfaces.repositories import (
    IPhotoRepository,
    IProfileRepository,
    IRateRepository,
    IReviewRepository,
    IServiceRepository,
    ProfileRepositoryPort,
)
from profile_intelligence.domain.value_objects.profile_children import (
    Photo,
    Rate,
    Review,
    Service,
)
from profile_intelligence.infrastructure.database.child_repositories import (
    SQLitePhotoRepository,
    SQLiteRateRepository,
    SQLiteReviewRepository,
    SQLiteServiceRepository,
)
from profile_intelligence.infrastructure.database.connection import Database
from profile_intelligence.infrastructure.database.repository import (
    SQLiteProfileRepository,
)


def test_profile_repository_port_alias() -> None:
    assert ProfileRepositoryPort is IProfileRepository


def test_sqlite_repository_implements_iprofile(database: Database) -> None:
    assert isinstance(SQLiteProfileRepository(database), IProfileRepository)


def test_child_repositories_implement_ports(database: Database) -> None:
    assert isinstance(SQLiteRateRepository(database), IRateRepository)
    assert isinstance(SQLiteServiceRepository(database), IServiceRepository)
    assert isinstance(SQLiteReviewRepository(database), IReviewRepository)
    assert isinstance(SQLitePhotoRepository(database), IPhotoRepository)


def test_container_resolves_repository_ports(temp_root) -> None:
    container = build_container(root_dir=temp_root)
    profile_repo = container.resolve(IProfileRepository)
    assert isinstance(profile_repo, SQLiteProfileRepository)
    assert isinstance(profile_repo, IProfileRepository)
    assert isinstance(container.resolve(IRateRepository), IRateRepository)
    assert isinstance(container.resolve(IServiceRepository), IServiceRepository)
    assert isinstance(container.resolve(IReviewRepository), IReviewRepository)
    assert isinstance(container.resolve(IPhotoRepository), IPhotoRepository)


def test_child_repositories_replace_and_list(database: Database) -> None:
    profiles: IProfileRepository = SQLiteProfileRepository(database)
    rates: IRateRepository = SQLiteRateRepository(database)
    services: IServiceRepository = SQLiteServiceRepository(database)
    reviews: IReviewRepository = SQLiteReviewRepository(database)
    photos: IPhotoRepository = SQLitePhotoRepository(database)

    profile, created = profiles.upsert_draft(
        ProfileDraft(display_name="Ada", source="test", external_id="ada-1")
    )
    assert created is True
    assert profile.id is not None
    profile_id = int(profile.id)

    rates.replace_for_profile(
        profile_id,
        (
            Rate(duration="1 hour", price="200", currency="EUR", incall=True),
            Rate(duration="2 hours", price="350", currency="EUR"),
        ),
    )
    services.replace_for_profile(
        profile_id,
        (Service(name="GFE"), Service(name="Dinner", available=False)),
    )
    reviews.replace_for_profile(
        profile_id,
        (Review(text="Great", author="Pat", rating="5"),),
    )
    photos.replace_for_profile(
        profile_id,
        (
            Photo(original_url="https://example.com/a.jpg", role="main"),
            Photo(original_url="https://example.com/b.jpg"),
        ),
    )

    assert len(rates.list_for_profile(profile_id)) == 2
    assert rates.list_for_profile(profile_id)[0].incall is True
    assert [item.name for item in services.list_for_profile(profile_id)] == [
        "GFE",
        "Dinner",
    ]
    assert reviews.list_for_profile(profile_id)[0].author == "Pat"
    assert photos.list_for_profile(profile_id)[0].role == "main"

    assert rates.delete_for_profile(profile_id) == 2
    assert services.delete_for_profile(profile_id) == 2
    assert reviews.delete_for_profile(profile_id) == 1
    assert photos.delete_for_profile(profile_id) == 2
    assert rates.list_for_profile(profile_id) == ()
