"""Configurable import processing chain.

```
pipeline:
  - parser
  - normalizer
  - validator
  - duplicate_detector
  - scorer
  - repository
```
"""

from __future__ import annotations

from profile_intelligence.application.pipeline.chain import (
    DEFAULT_PIPELINE_STAGES,
    ProcessingChain,
    ProcessingResult,
)
from profile_intelligence.application.pipeline.duplicate_detector import (
    DuplicateDetector,
    DuplicateFilterResult,
    DuplicateMatch,
)
from profile_intelligence.application.pipeline.normalizer import ProfileNormalizer
from profile_intelligence.application.pipeline.parser import DocumentParser
from profile_intelligence.application.pipeline.repository_stage import (
    RepositoryStage,
    RepositoryStageResult,
)
from profile_intelligence.application.pipeline.scorer import ProfileScorer
from profile_intelligence.application.pipeline.validator import ProfileValidator

__all__ = [
    "DEFAULT_PIPELINE_STAGES",
    "DocumentParser",
    "DuplicateDetector",
    "DuplicateFilterResult",
    "DuplicateMatch",
    "ProcessingChain",
    "ProcessingResult",
    "ProfileNormalizer",
    "ProfileScorer",
    "ProfileValidator",
    "RepositoryStage",
    "RepositoryStageResult",
]
