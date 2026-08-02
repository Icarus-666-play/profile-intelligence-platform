"""Profile text summarization.

```
analysis/
  summarization.py
```
"""

from __future__ import annotations

from dataclasses import dataclass

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.ai import IAIProvider
from profile_intelligence.domain.interfaces.repositories import ProfileEntity
from profile_intelligence.domain.value_objects.ai import AICompletionRequest

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    """Short textual summary of a profile."""

    profile_id: int | None
    display_name: str
    text: str
    source: str  # heuristic | ai
    confidence_score: int | None = None


class ProfileSummarizer:
    """Build concise profile summaries (heuristic, optional AI)."""

    def __init__(self, ai: IAIProvider | None = None) -> None:
        self._ai = ai

    def summarize(self, profile: ProfileEntity) -> ProfileSummary:
        """Return a summary for *profile*.

        Uses a deterministic heuristic by default. When an enabled AI provider
        is available, attempts an AI rewrite and falls back on failure.
        """
        heuristic = self._heuristic(profile)
        if self._ai is not None and self._ai.enabled and self._ai.available():
            try:
                result = self._ai.complete(
                    AICompletionRequest(
                        prompt=(
                            "Summarize this profile in one short sentence:\n"
                            f"{heuristic}"
                        ),
                        system="You write concise profile summaries.",
                        max_tokens=80,
                    )
                )
                if result.text.strip() and not result.skipped:
                    return ProfileSummary(
                        profile_id=profile.id,
                        display_name=profile.display_name,
                        text=result.text.strip(),
                        source="ai",
                        confidence_score=profile.score,
                    )
            except Exception as exc:  # noqa: BLE001 - fall back to heuristic
                logger.warning("AI summarization failed: %s", exc)

        return ProfileSummary(
            profile_id=profile.id,
            display_name=profile.display_name,
            text=heuristic,
            source="heuristic",
            confidence_score=profile.score,
        )

    def _heuristic(self, profile: ProfileEntity) -> str:
        parts = [profile.display_name]
        if profile.title:
            parts.append(profile.title)
        if profile.organization:
            parts.append(f"at {profile.organization}")
        if profile.location:
            parts.append(f"in {profile.location}")
        if profile.source:
            parts.append(f"(source: {profile.source})")
        if profile.score is not None:
            parts.append(f"[confidence {profile.score}]")
        if profile.tags:
            parts.append(f"tags: {profile.tags}")
        return " — ".join(parts) if len(parts) > 1 else parts[0]
