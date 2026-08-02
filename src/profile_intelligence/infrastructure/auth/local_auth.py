"""Optional local login sessions.

```
Login (optional)
 ↓
Home
 ↓
Dashboard
```

Default config keeps login optional (guest continue). Enabling ``auth.enabled``
checks a local username/password without turning PIP into a multi-user SaaS.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from threading import Lock

from profile_intelligence.core.config import AppConfig
from profile_intelligence.core.exceptions import ValidationError


@dataclass(frozen=True, slots=True)
class AuthSession:
    """In-memory operator session."""

    token: str
    username: str
    mode: str  # "user" | "guest"
    expires_at: float

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at

    def to_dict(self) -> dict[str, object]:
        return {
            "token": self.token,
            "username": self.username,
            "mode": self.mode,
            "expires_at": self.expires_at,
            "authenticated": self.mode == "user",
            "guest": self.mode == "guest",
        }


class LocalAuthService:
    """Issue optional guest or credential sessions for the UI entry flow."""

    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._sessions: dict[str, AuthSession] = {}
        self._lock = Lock()

    @property
    def enabled(self) -> bool:
        return bool(self._config.auth.enabled)

    @property
    def allow_guest(self) -> bool:
        return bool(self._config.auth.allow_guest)

    def status(self) -> dict[str, object]:
        """Public auth configuration for the Login page."""
        return {
            "enabled": self.enabled,
            "allow_guest": self.allow_guest,
            "username_hint": self._config.auth.username if self.enabled else None,
            "flow": ["login", "home", "dashboard"],
        }

    def login(self, username: str, password: str) -> AuthSession:
        """Validate local credentials and return a user session."""
        expected_user = self._config.auth.username
        expected_password = self._config.auth.password or ""
        if self.enabled:
            user_ok = secrets.compare_digest(
                username.strip(), expected_user.strip()
            )
            pass_ok = secrets.compare_digest(password, expected_password)
            if not user_ok or not pass_ok or not expected_password:
                raise ValidationError("Invalid username or password")
        else:
            # Auth off: accept any non-empty username as a named local session.
            if not username.strip():
                raise ValidationError("Username is required")
        return self._issue(username.strip() or expected_user, mode="user")

    def continue_as_guest(self) -> AuthSession:
        """Skip login (optional path) when guest continue is allowed."""
        if not self.allow_guest:
            raise ValidationError("Guest continue is disabled")
        return self._issue("guest", mode="guest")

    def logout(self, token: str | None) -> None:
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def resolve(self, token: str | None) -> AuthSession | None:
        if not token:
            return None
        with self._lock:
            session = self._sessions.get(token)
            if session is None:
                return None
            if session.expired:
                self._sessions.pop(token, None)
                return None
            return session

    def _issue(self, username: str, *, mode: str) -> AuthSession:
        ttl = max(60, int(self._config.auth.session_ttl_seconds))
        session = AuthSession(
            token=secrets.token_urlsafe(32),
            username=username,
            mode=mode,
            expires_at=time.time() + ttl,
        )
        with self._lock:
            self._purge_expired_unlocked()
            self._sessions[session.token] = session
        return session

    def _purge_expired_unlocked(self) -> None:
        now = time.time()
        expired = [
            token
            for token, session in self._sessions.items()
            if session.expires_at <= now
        ]
        for token in expired:
            self._sessions.pop(token, None)


__all__ = ["AuthSession", "LocalAuthService"]
