"""Optional AI provider adapters.

```
AI
  Null (default, disabled)
  Local (future)
  Remote (future)
```
"""

from __future__ import annotations

from profile_intelligence.infrastructure.ai.factory import create_ai_provider
from profile_intelligence.infrastructure.ai.local import LocalAIProvider
from profile_intelligence.infrastructure.ai.null_provider import NullAIProvider
from profile_intelligence.infrastructure.ai.remote import RemoteAIProvider

__all__ = [
    "LocalAIProvider",
    "NullAIProvider",
    "RemoteAIProvider",
    "create_ai_provider",
]
