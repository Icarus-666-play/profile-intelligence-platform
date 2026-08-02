"""Email Report adapter (future).

```
Daily
 ↓
…
 ↓
Email Report (future)
```
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from profile_intelligence.core.exceptions import ServiceError
from profile_intelligence.core.logging import get_logger
from profile_intelligence.core.types import PathLike

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class EmailReportRequest:
    """Payload for a future daily email report."""

    subject: str
    body: str
    recipients: tuple[str, ...] = ()
    attachments: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class EmailReportResult:
    """Outcome of the Email Report stage."""

    attempted: bool
    sent: bool = False
    skipped: bool = True
    message: str = "Email Report is not implemented yet (future)"


class EmailReportService:
    """Placeholder email reporter — not implemented yet."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        recipients: Sequence[str] | None = None,
    ) -> None:
        self._enabled = enabled
        self._recipients = tuple(recipients or ())

    @property
    def enabled(self) -> bool:
        """Whether email reporting is configured on."""
        return self._enabled

    def send_daily_report(
        self,
        *,
        subject: str,
        body: str,
        attachments: Sequence[PathLike] = (),
        recipients: Sequence[str] | None = None,
    ) -> EmailReportResult:
        """Send (or skip) the daily email report.

        Future milestone will deliver SMTP/local MAPI integration. Today this
        either no-ops when disabled or records that email is not implemented.
        """
        to = tuple(recipients) if recipients is not None else self._recipients
        paths = tuple(Path(item) for item in attachments)
        request = EmailReportRequest(
            subject=subject,
            body=body,
            recipients=to,
            attachments=paths,
        )

        if not self._enabled:
            logger.info("Email Report skipped (disabled / future)")
            return EmailReportResult(
                attempted=False,
                sent=False,
                skipped=True,
                message="Email Report skipped (disabled; future)",
            )

        logger.warning(
            "Email Report requested but not implemented "
            "(recipients=%d attachments=%d subject=%r)",
            len(request.recipients),
            len(request.attachments),
            request.subject,
        )
        raise ServiceError(
            "Email Report is not implemented yet. "
            "Disable daily.email_enabled until the email milestone."
        )
