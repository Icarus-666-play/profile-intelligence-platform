"""Facade over profile analysis modules.

```
analysis/
  similarity.py
  recommendation.py
  summarization.py
  classification.py
  duplicates.py
```
"""

from __future__ import annotations

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.ai import IAIProvider
from profile_intelligence.domain.interfaces.repositories import (
    IProfileRepository,
    ProfileEntity,
)
from profile_intelligence.infrastructure.analysis.classification import (
    ProfileClassification,
    ProfileClassifier,
)
from profile_intelligence.infrastructure.analysis.duplicates import (
    DuplicateAnalysisResult,
    ProfileDuplicateAnalyzer,
)
from profile_intelligence.infrastructure.analysis.recommendation import (
    ProfileRecommendation,
    ProfileRecommender,
)
from profile_intelligence.infrastructure.analysis.similarity import (
    ProfileSimilarityAnalyzer,
    SimilarityScore,
)
from profile_intelligence.infrastructure.analysis.summarization import (
    ProfileSummarizer,
    ProfileSummary,
)

logger = get_logger(__name__)


class AnalysisService:
    """High-level profile analysis operations."""

    def __init__(
        self,
        repository: IProfileRepository,
        *,
        similarity: ProfileSimilarityAnalyzer | None = None,
        recommender: ProfileRecommender | None = None,
        summarizer: ProfileSummarizer | None = None,
        classifier: ProfileClassifier | None = None,
        duplicates: ProfileDuplicateAnalyzer | None = None,
        ai: IAIProvider | None = None,
    ) -> None:
        self._repository = repository
        self._similarity = similarity or ProfileSimilarityAnalyzer()
        self._recommender = recommender or ProfileRecommender(self._similarity)
        self._summarizer = summarizer or ProfileSummarizer(ai)
        self._classifier = classifier or ProfileClassifier()
        self._duplicates = duplicates or ProfileDuplicateAnalyzer(self._similarity)

    def similarity(self, left_id: int, right_id: int) -> SimilarityScore:
        """Score similarity between two stored profiles."""
        left = self._require(left_id)
        right = self._require(right_id)
        return self._similarity.score(
            left,
            right,
            left_id=left.id,
            right_id=right.id,
        )

    def recommend(
        self,
        profile_id: int,
        *,
        limit: int = 5,
    ) -> tuple[ProfileRecommendation, ...]:
        """Recommend similar profiles for *profile_id*."""
        seed = self._require(profile_id)
        candidates = self._repository.list_all(limit=10_000, offset=0)
        return self._recommender.recommend(seed, candidates, limit=limit)

    def summarize(self, profile_id: int) -> ProfileSummary:
        """Summarize one stored profile."""
        return self._summarizer.summarize(self._require(profile_id))

    def classify(self, profile_id: int) -> ProfileClassification:
        """Classify one stored profile."""
        return self._classifier.classify(self._require(profile_id))

    def classify_all(
        self,
        *,
        limit: int = 10_000,
    ) -> tuple[ProfileClassification, ...]:
        """Classify stored profiles."""
        profiles = self._repository.list_all(limit=limit, offset=0)
        return self._classifier.classify_many(profiles)

    def find_duplicates(
        self,
        *,
        limit: int = 10_000,
        threshold: float | None = None,
    ) -> DuplicateAnalysisResult:
        """Find near-duplicate profile groups."""
        profiles = self._repository.list_all(limit=limit, offset=0)
        analyzer = (
            self._duplicates
            if threshold is None
            else ProfileDuplicateAnalyzer(self._similarity, threshold=threshold)
        )
        return analyzer.analyze(profiles)

    def _require(self, profile_id: int) -> ProfileEntity:
        profile = self._repository.get_by_id(profile_id)
        if profile is None:
            from profile_intelligence.core.exceptions import ValidationError

            raise ValidationError(f"Profile not found: id={profile_id}")
        return profile
