"""Validator stage: ensure normalized drafts are persistable."""

from __future__ import annotations

import re
from collections.abc import Sequence

from profile_intelligence.core.exceptions import ValidationError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.extractors.profile import ProfileDraft

logger = get_logger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_DISPLAY_NAME = 512
_MAX_EMAIL = 320
_MAX_PHONE = 64
_MAX_SHORT = 255


class ProfileValidator:
    """Validate normalized profile drafts before persistence."""

    def validate(self, draft: ProfileDraft) -> ProfileDraft:
        """Validate a single draft; return it or raise :class:`ValidationError`."""
        errors = self._collect_errors(draft)
        if errors:
            raise ValidationError("; ".join(errors))
        return draft

    def validate_many(
        self,
        drafts: Sequence[ProfileDraft],
    ) -> tuple[list[ProfileDraft], list[str]]:
        """Validate many drafts; return accepted drafts and error messages."""
        accepted: list[ProfileDraft] = []
        errors: list[str] = []
        for index, draft in enumerate(drafts, start=1):
            row_errors = self._collect_errors(draft)
            if row_errors:
                errors.append(f"row {index}: " + "; ".join(row_errors))
                continue
            accepted.append(draft)
        logger.debug(
            "Validator stage: accepted=%d rejected=%d",
            len(accepted),
            len(errors),
        )
        return accepted, errors

    def _collect_errors(self, draft: ProfileDraft) -> list[str]:
        errors: list[str] = []
        name = draft.display_name.strip()
        if not name:
            errors.append("display_name is required")
        elif len(name) > _MAX_DISPLAY_NAME:
            errors.append(
                f"display_name exceeds {_MAX_DISPLAY_NAME} characters"
            )

        if draft.email:
            email = draft.email.strip()
            if len(email) > _MAX_EMAIL:
                errors.append(f"email exceeds {_MAX_EMAIL} characters")
            elif not _EMAIL_RE.match(email):
                errors.append(f"email is invalid: {email!r}")

        if draft.phone and len(draft.phone) > _MAX_PHONE:
            errors.append(f"phone exceeds {_MAX_PHONE} characters")

        for field_name, limit in (
            ("title", _MAX_SHORT),
            ("organization", _MAX_SHORT),
            ("location", _MAX_SHORT),
            ("external_id", _MAX_SHORT),
            ("source", 128),
        ):
            value = getattr(draft, field_name)
            if isinstance(value, str) and len(value) > limit:
                errors.append(f"{field_name} exceeds {limit} characters")

        return errors
