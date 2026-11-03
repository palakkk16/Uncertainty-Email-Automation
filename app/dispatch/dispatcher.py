"""Turn a SEND draft into one delivered email, at most once per window.

The router depends on `get_dispatcher`, so tests replace it through
`app.dependency_overrides` and never reach Gmail.
"""

from __future__ import annotations

from typing import Protocol

from app.config import load_dispatch_settings
from app.decision import Draft
from app.dispatch.errors import DispatchRejected
from app.dispatch.gmail import GmailSender
from app.dispatch.guard import DuplicateGuard, message_key
from app.schemas.chat import DispatchResult


class MailSender(Protocol):
    """Anything that delivers one message and returns its provider id."""

    def send(self, recipient: str, subject: str, body: str) -> str: ...


class Dispatcher:
    """Allowlist check, duplicate guard, then one send.

    An empty allowed_recipients set skips the allowlist. That is how
    APP_ALLOW_ALL_RECIPIENTS delivers to any address the user provided.
    """

    def __init__(
        self,
        sender: MailSender,
        allowed_recipients: frozenset[str],
        guard: DuplicateGuard,
    ) -> None:
        self._sender = sender
        self._allowed = allowed_recipients
        self._guard = guard

    def dispatch(self, draft: Draft) -> DispatchResult:
        """Send the draft unless the same email was sent within the window."""
        if self._allowed and draft.recipient.lower() not in self._allowed:
            raise DispatchRejected("recipient_not_allowed")
        key = message_key(draft.recipient, draft.subject, draft.body)
        if not self._guard.claim(key):
            return DispatchResult(status="already_sent")
        try:
            message_id = self._sender.send(draft.recipient, draft.subject, draft.body)
        except Exception:
            self._guard.release(key)
            raise
        return DispatchResult(status="sent", message_id=message_id)


# One guard per process, shared by every request.
_GUARD = DuplicateGuard()


def get_dispatcher() -> Dispatcher | None:
    """FastAPI dependency. None when APP_DISPATCH_ENABLED is false."""
    settings = load_dispatch_settings()
    if settings is None:
        return None
    sender = GmailSender(settings.sender, settings.token_path)
    return Dispatcher(sender, settings.allowed_recipients, _GUARD)
