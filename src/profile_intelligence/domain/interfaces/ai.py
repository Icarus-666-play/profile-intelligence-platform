"""AI provider port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from profile_intelligence.domain.value_objects.ai import (
    AICompletionRequest,
    AICompletionResult,
)


class IAIProvider(ABC):
    """Port for optional AI assistance (local or remote)."""

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider name (``null``, ``local``, ``remote``, …)."""

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether this provider will attempt network / model calls."""

    @abstractmethod
    def available(self) -> bool:
        """Return True when the provider can serve completions now."""

    @abstractmethod
    def complete(self, request: AICompletionRequest) -> AICompletionResult:
        """Run a text completion for *request*."""
