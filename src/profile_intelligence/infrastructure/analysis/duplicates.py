"""Near-duplicate profile analysis.

```
analysis/
  duplicates.py
```

Distinct from import-time :class:`DuplicateDetector` (exact identity keys)
and media :class:`ImageDuplicateFinder` (content hashes).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.repositories import ProfileEntity
from profile_intelligence.infrastructure.analysis.similarity import (
    ProfileSimilarityAnalyzer,
    SimilarityScore,
)

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DuplicatePair:
    """Two profiles considered near-duplicates."""

    left_id: int
    right_id: int
    left_name: str
    right_name: str
    score: SimilarityScore


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    """A cluster of near-duplicate profile ids."""

    profile_ids: tuple[int, ...]
    pairs: tuple[DuplicatePair, ...] = field(default_factory=tuple)

    @property
    def size(self) -> int:
        """Number of profiles in the group."""
        return len(self.profile_ids)


@dataclass(frozen=True, slots=True)
class DuplicateAnalysisResult:
    """Outcome of a near-duplicate scan."""

    pairs: tuple[DuplicatePair, ...] = field(default_factory=tuple)
    groups: tuple[DuplicateGroup, ...] = field(default_factory=tuple)
    scanned: int = 0

    @property
    def duplicate_count(self) -> int:
        """Profiles that appear in at least one group beyond a singleton."""
        return sum(max(0, group.size - 1) for group in self.groups)


class ProfileDuplicateAnalyzer:
    """Find near-duplicate profiles using similarity thresholds."""

    def __init__(
        self,
        similarity: ProfileSimilarityAnalyzer | None = None,
        *,
        threshold: float = 0.75,
    ) -> None:
        self._similarity = similarity or ProfileSimilarityAnalyzer()
        self._threshold = threshold

    def analyze(
        self,
        profiles: Sequence[ProfileEntity],
    ) -> DuplicateAnalysisResult:
        """Scan *profiles* for near-duplicate pairs and groups."""
        indexed = [row for row in profiles if row.id is not None]
        pairs: list[DuplicatePair] = []

        for index, left in enumerate(indexed):
            assert left.id is not None
            for right in indexed[index + 1 :]:
                assert right.id is not None
                score = self._similarity.score(
                    left,
                    right,
                    left_id=left.id,
                    right_id=right.id,
                )
                if score.value < self._threshold:
                    continue
                pairs.append(
                    DuplicatePair(
                        left_id=left.id,
                        right_id=right.id,
                        left_name=left.display_name,
                        right_name=right.display_name,
                        score=score,
                    )
                )

        groups = self._group_pairs(pairs)
        result = DuplicateAnalysisResult(
            pairs=tuple(pairs),
            groups=groups,
            scanned=len(indexed),
        )
        logger.info(
            "Duplicate analysis: scanned=%d pairs=%d groups=%d extras=%d",
            result.scanned,
            len(result.pairs),
            len(result.groups),
            result.duplicate_count,
        )
        return result

    def _group_pairs(
        self,
        pairs: Sequence[DuplicatePair],
    ) -> tuple[DuplicateGroup, ...]:
        parent: dict[int, int] = {}

        def find(node: int) -> int:
            while parent.get(node, node) != node:
                node = parent[node]
            return node

        def union(left: int, right: int) -> None:
            root_left = find(left)
            root_right = find(right)
            if root_left != root_right:
                parent[root_right] = root_left

        for pair in pairs:
            parent.setdefault(pair.left_id, pair.left_id)
            parent.setdefault(pair.right_id, pair.right_id)
            union(pair.left_id, pair.right_id)

        buckets: dict[int, list[int]] = {}
        for node in parent:
            root = find(node)
            buckets.setdefault(root, []).append(node)

        pair_index: dict[int, list[DuplicatePair]] = {}
        for pair in pairs:
            root = find(pair.left_id)
            pair_index.setdefault(root, []).append(pair)

        groups: list[DuplicateGroup] = []
        for root, members in sorted(buckets.items(), key=lambda item: item[0]):
            if len(members) < 2:
                continue
            groups.append(
                DuplicateGroup(
                    profile_ids=tuple(sorted(members)),
                    pairs=tuple(pair_index.get(root, ())),
                )
            )
        return tuple(groups)
