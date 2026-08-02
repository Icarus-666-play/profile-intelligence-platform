"""AI request / response value objects.

```
AI
  Null (default, disabled)
  Local (future)
  Remote (future)
```
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AICompletionRequest:
    """Prompt payload for an AI completion call."""

    prompt: str
    system: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    metadata: tuple[tuple[str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class AICompletionResult:
    """Normalized completion returned by an AI provider."""

    text: str
    provider: str
    model: str | None = None
    skipped: bool = False
    finish_reason: str | None = None
