"""Profile analysis toolkit.

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

from profile_intelligence.infrastructure.analysis.classification import (
    ProfileClassification,
    ProfileClassifier,
)
from profile_intelligence.infrastructure.analysis.duplicates import (
    DuplicateAnalysisResult,
    DuplicateGroup,
    DuplicatePair,
    ProfileDuplicateAnalyzer,
)
from profile_intelligence.infrastructure.analysis.recommendation import (
    ProfileRecommendation,
    ProfileRecommender,
)
from profile_intelligence.infrastructure.analysis.service import AnalysisService
from profile_intelligence.infrastructure.analysis.similarity import (
    ProfileSimilarityAnalyzer,
    SimilarityScore,
)
from profile_intelligence.infrastructure.analysis.summarization import (
    ProfileSummarizer,
    ProfileSummary,
)

__all__ = [
    "AnalysisService",
    "DuplicateAnalysisResult",
    "DuplicateGroup",
    "DuplicatePair",
    "ProfileClassification",
    "ProfileClassifier",
    "ProfileDuplicateAnalyzer",
    "ProfileRecommendation",
    "ProfileRecommender",
    "ProfileSimilarityAnalyzer",
    "ProfileSummarizer",
    "ProfileSummary",
    "SimilarityScore",
]
