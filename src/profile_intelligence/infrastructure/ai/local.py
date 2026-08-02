"""Local AI provider stub (future — e.g. Ollama).

```
AI
  Local (future)
```
"""

from __future__ import annotations

from profile_intelligence.core.exceptions import AIError
from profile_intelligence.domain.interfaces.ai import IAIProvider
from profile_intelligence.domain.value_objects.ai import (
    AICompletionRequest,
    AICompletionResult,
)


class LocalAIProvider(IAIProvider):
    """Placeholder local-model adapter — not implemented yet."""

    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._model = model
        self._base_url = base_url
        raise AIError(
            "Local AI provider is not implemented yet. "
            "Keep ai.enabled: false, or wait for the M3 AI Assist milestone."
        )

    @property
    def provider(self) -> str:
        return "local"

    @property
    def enabled(self) -> bool:
        return True

    def available(self) -> bool:
        return False

    def complete(self, request: AICompletionRequest) -> AICompletionResult:
        _ = request
        raise AIError("Local AI provider is not implemented yet")
