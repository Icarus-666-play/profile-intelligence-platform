"""Tests for database seeding."""

from __future__ import annotations

from profile_intelligence.infrastructure.database.repository import ProfileRepository
from profile_intelligence.infrastructure.database.seed import (
    DEFAULT_SEED_PROFILES,
    seed_database,
)


def test_seed_creates_demo_profiles(database) -> None:
    repo = ProfileRepository(database)
    result = seed_database(repo)
    assert result.created == len(DEFAULT_SEED_PROFILES)
    assert result.updated == 0
    assert repo.count() == len(DEFAULT_SEED_PROFILES)

    again = seed_database(repo)
    assert again.created == 0
    assert again.updated == len(DEFAULT_SEED_PROFILES)
    assert repo.count() == len(DEFAULT_SEED_PROFILES)


def test_seed_only_if_empty(database) -> None:
    repo = ProfileRepository(database)
    first = seed_database(repo, only_if_empty=True)
    assert first.created == len(DEFAULT_SEED_PROFILES)

    second = seed_database(repo, only_if_empty=True)
    assert second.created == 0
    assert second.updated == 0
    assert second.skipped == len(DEFAULT_SEED_PROFILES)
