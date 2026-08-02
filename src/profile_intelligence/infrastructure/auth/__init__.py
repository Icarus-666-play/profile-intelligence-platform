"""Optional local authentication for the React entry flow."""

from profile_intelligence.infrastructure.auth.local_auth import (
    AuthSession,
    LocalAuthService,
)

__all__ = ["AuthSession", "LocalAuthService"]
