"""AI provider scaffold tests."""

from __future__ import annotations

import pytest

from profile_intelligence.bootstrap import build_container
from profile_intelligence.core.config import AISection, AppConfig
from profile_intelligence.core.exceptions import AIError, ConfigurationError
from profile_intelligence.domain.interfaces.ai import IAIProvider
from profile_intelligence.domain.value_objects.ai import AICompletionRequest
from profile_intelligence.infrastructure.ai import (
    LocalAIProvider,
    NullAIProvider,
    RemoteAIProvider,
    create_ai_provider,
)


def test_null_provider_skips_completion() -> None:
    provider = NullAIProvider(model="none")
    assert provider.provider == "null"
    assert provider.enabled is False
    assert provider.available() is False
    result = provider.complete(AICompletionRequest(prompt="hello"))
    assert result.skipped is True
    assert result.text == ""
    assert result.finish_reason == "disabled"


def test_local_and_remote_stubs_raise() -> None:
    with pytest.raises(AIError, match="not implemented"):
        LocalAIProvider(model="llama3")
    with pytest.raises(AIError, match="not implemented"):
        RemoteAIProvider(model="gpt-4o-mini", api_key="secret")


def test_create_ai_provider_selection() -> None:
    disabled = create_ai_provider(AppConfig(ai=AISection(enabled=False)))
    assert isinstance(disabled, NullAIProvider)

    null_enabled = create_ai_provider(
        AppConfig(ai=AISection(enabled=True, provider="null"))
    )
    assert isinstance(null_enabled, NullAIProvider)

    with pytest.raises(AIError, match="not implemented"):
        create_ai_provider(
            AppConfig(ai=AISection(enabled=True, provider="ollama", model="x"))
        )

    with pytest.raises(AIError, match="not implemented"):
        create_ai_provider(
            AppConfig(ai=AISection(enabled=True, provider="openai", model="y"))
        )

    with pytest.raises(ConfigurationError, match="Unsupported AI provider"):
        create_ai_provider(
            AppConfig(ai=AISection(enabled=True, provider="nope"))
        )


def test_bootstrap_registers_null_ai(temp_root: object) -> None:
    from pathlib import Path

    assert isinstance(temp_root, Path)
    container = build_container(root_dir=temp_root)
    provider = container.resolve(IAIProvider)
    assert isinstance(provider, NullAIProvider)
    assert provider.enabled is False
