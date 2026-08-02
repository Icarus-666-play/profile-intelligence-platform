"""Null AI provider used when AI is disabled."""

from __future__ import annotations

from profile_intelligence.core.logging import get_logger
from profile_intelligence.domain.interfaces.ai import IAIProvider
from profile_intelligence.domain.value_objects.ai import (
    AICompletionRequest,
    AICompletionResult,
)

logger = get_logger(__name__)


class NullAIProvider(IAIProvider):
    """No-op provider — AI remains off without raising."""

    def __init__(self, *, model: str | None = None) -> None:
        self._model = model

    @property
    def provider(self) -> str:
        return "null"

    @property
    def enabled(self) -> bool:
        return False

    def available(self) -> bool:
        return False

    def complete(self, request: AICompletionRequest) -> AICompletionResult:
        logger.debug(
            "AI complete skipped (null provider) prompt_chars=%d",
            len(request.prompt),
        )
        return AICompletionResult(
            text="",
            provider=self.provider,
            model=self._model,
            skipped=True,
            finish_reason="disabled",
        )
