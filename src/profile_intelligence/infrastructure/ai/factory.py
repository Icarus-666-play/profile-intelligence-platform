"""AI provider factory."""

from __future__ import annotations

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.exceptions import ConfigurationError
from profile_intelligence.domain.interfaces.ai import IAIProvider
from profile_intelligence.infrastructure.ai.local import LocalAIProvider
from profile_intelligence.infrastructure.ai.null_provider import NullAIProvider
from profile_intelligence.infrastructure.ai.remote import RemoteAIProvider


def create_ai_provider(config: AppConfig) -> IAIProvider:
    """Build the configured AI provider.

    Supported providers::

        AI
          Null (default when disabled)
          Local (future)
          Remote (future)
    """
    section = config.ai
    if not section.enabled:
        return NullAIProvider(model=section.model)

    provider = (section.provider or "").strip().lower()
    if provider in {"", "null", "none", "off"}:
        return NullAIProvider(model=section.model)
    if provider in {"local", "ollama"}:
        return LocalAIProvider(
            model=section.model,
            base_url=section.base_url,
        )
    if provider in {"remote", "openai"}:
        return RemoteAIProvider(
            model=section.model,
            base_url=section.base_url,
            api_key=section.api_key,
        )
    raise ConfigurationError(
        f"Unsupported AI provider: {provider!r} "
        "(expected null, local/ollama, or remote/openai)"
    )
