"""Console dashboard summaries (desktop UI comes in a later milestone)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.repositories import (
    IProfileRepository,
    ProfileEntity,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    """Aggregated dashboard metrics for the local profile database."""

    total_profiles: int
    scored_profiles: int
    average_score: float | None
    by_source: tuple[tuple[str, int], ...]
    top_profiles: tuple[ProfileEntity, ...]
    incomplete_profiles: tuple[ProfileEntity, ...]


class DashboardService:
    """Build local dashboard snapshots for CLI / future UI."""

    def __init__(self, repository: IProfileRepository) -> None:
        self._repository = repository

    def snapshot(
        self,
        *,
        top_limit: int = 5,
        incomplete_limit: int = 5,
    ) -> DashboardSnapshot:
        """Collect counts, score stats, and highlight lists."""
        profiles = list(self._repository.list_all(limit=100_000, offset=0))
        scores = [row.score for row in profiles if row.score is not None]
        average = (
            round(sum(scores) / len(scores), 1) if scores else None
        )

        source_counts = Counter(
            (row.source or "unknown") for row in profiles
        )
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

        snapshot = DashboardSnapshot(
            total_profiles=len(profiles),
            scored_profiles=len(scores),
            average_score=average,
            by_source=by_source,
            top_profiles=tuple(ranked[:top_limit]),
            incomplete_profiles=tuple(incomplete[:incomplete_limit]),
        )
        logger.debug(
            "Dashboard snapshot: total=%d scored=%d sources=%d",
            snapshot.total_profiles,
            snapshot.scored_profiles,
            len(snapshot.by_source),
        )
        return snapshot

    def render_text(self, snapshot: DashboardSnapshot | None = None) -> str:
        """Render a plain-text console dashboard."""
        data = snapshot or self.snapshot()
        lines = [
            "Profile Intelligence Platform — Dashboard",
            "=" * 44,
            f"Profiles: {data.total_profiles}",
            f"Scored:   {data.scored_profiles}",
            (
                f"Average completeness score: {data.average_score}"
                if data.average_score is not None
                else "Average completeness score: n/a"
            ),
            "",
            "By source:",
        ]
        if data.by_source:
            for source, count in data.by_source:
                lines.append(f"  - {source}: {count}")
        else:
            lines.append("  (none)")

        lines.extend(["", "Top scored:"])
        lines.extend(_profile_lines(data.top_profiles) or ["  (none)"])

        lines.extend(["", "Needs attention (lowest score):"])
        lines.extend(_profile_lines(data.incomplete_profiles) or ["  (none)"])

        lines.extend(
            [
                "",
                "Desktop UI dashboard is planned for Milestone 2.",
                "Use: pip-app search | compare | export",
            ]
        )
        return "\n".join(lines)


def _profile_lines(profiles: Sequence[ProfileEntity]) -> list[str]:
    lines: list[str] = []
    for profile in profiles:
        score = profile.score if profile.score is not None else "-"
        lines.append(
            f"  [{profile.id}] {profile.display_name} | "
            f"{profile.source or '-'} | score={score}"
        )
    return lines
