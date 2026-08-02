"""Seed the local database with demo profile data."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.entities.profile import ProfileDraft
from profile_intelligence.infrastructure.database.repository import ProfileRepository
from profile_intelligence.infrastructure.scoring.completeness import CompletenessScorer

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class SeedProfile:
    """Built-in demo profile used by the seeder."""

    external_id: str
    display_name: str
    email: str | None = None
    phone: str | None = None
    title: str | None = None
    organization: str | None = None
    location: str | None = None
    tags: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Outcome of a seed operation."""

    created: int
    updated: int
    skipped: int = 0

    @property
    def total_written(self) -> int:
        """Profiles created or updated."""
        return self.created + self.updated


DEFAULT_SEED_PROFILES: tuple[SeedProfile, ...] = (
    SeedProfile(
        external_id="seed-001",
        display_name="Ada Lovelace",
        email="ada@example.com",
        phone="+1-555-0101",
        title="Analyst",
        organization="Analytical Engines",
        location="London",
        tags="math,computing",
        notes="Pioneer of computing",
    ),
    SeedProfile(
        external_id="seed-002",
        display_name="Grace Hopper",
        email="grace@example.com",
        phone="+1-555-0102",
        title="Rear Admiral",
        organization="US Navy",
        location="New York",
        tags="cobol,compilers",
        notes="Invented the compiler",
    ),
    SeedProfile(
        external_id="seed-003",
        display_name="Alan Turing",
        email="alan@example.com",
        title="Mathematician",
        organization="Bletchley Park",
        location="United Kingdom",
        tags="crypto,ai",
    ),
    SeedProfile(
        external_id="seed-004",
        display_name="Katherine Johnson",
        email="katherine@example.com",
        phone="+1-555-0104",
        title="Mathematician",
        organization="NASA",
        location="West Virginia",
        tags="orbital,math",
        notes="Calculated trajectories for early spaceflights",
    ),
    SeedProfile(
        external_id="seed-005",
        display_name="Margaret Hamilton",
        email="margaret@example.com",
        title="Software Engineer",
        organization="MIT Instrumentation Lab",
        location="Cambridge",
        tags="apollo,software",
        notes="Led Apollo flight software development",
    ),
)


class DatabaseSeeder:
    """Upsert demo profiles into the local SQLite database."""

    def __init__(
        self,
        repository: ProfileRepository,
        scorer: CompletenessScorer | None = None,
        *,
        source: str = "seed",
    ) -> None:
        self._repository = repository
        self._scorer = scorer or CompletenessScorer()
        self._source = source

    def seed(
        self,
        profiles: Sequence[SeedProfile] | None = None,
        *,
        only_if_empty: bool = False,
    ) -> SeedResult:
        """Seed profiles into the database.

        Parameters
        ----------
        profiles:
            Profiles to upsert. Defaults to :data:`DEFAULT_SEED_PROFILES`.
        only_if_empty:
            When True, skip seeding if any profiles already exist.
        """
        if only_if_empty and self._repository.count() > 0:
            logger.info("Database already contains profiles; skipping seed")
            skipped = len(profiles or DEFAULT_SEED_PROFILES)
            return SeedResult(created=0, updated=0, skipped=skipped)

        selected = tuple(profiles) if profiles is not None else DEFAULT_SEED_PROFILES
        created = 0
        updated = 0
        for item in selected:
            draft = self._to_draft(item)
            draft.score = self._scorer.score(draft)
            _, was_created = self._repository.upsert_draft(draft)
            if was_created:
                created += 1
            else:
                updated += 1

        result = SeedResult(created=created, updated=updated)
        logger.info(
            "Seed complete: created=%d updated=%d source=%s",
            result.created,
            result.updated,
            self._source,
        )
        return result

    def _to_draft(self, profile: SeedProfile) -> ProfileDraft:
        return ProfileDraft(
            external_id=profile.external_id,
            display_name=profile.display_name,
            email=profile.email,
            phone=profile.phone,
            title=profile.title,
            organization=profile.organization,
            location=profile.location,
            tags=profile.tags,
            notes=profile.notes,
            source=self._source,
        )


def seed_database(
    repository: ProfileRepository,
    *,
    only_if_empty: bool = False,
    profiles: Sequence[SeedProfile] | None = None,
) -> SeedResult:
    """Convenience wrapper around :class:`DatabaseSeeder`."""
    return DatabaseSeeder(repository).seed(
        profiles,
        only_if_empty=only_if_empty,
    )
