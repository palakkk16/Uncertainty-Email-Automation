"""Send one message through the Gmail API with an existing send-only token.

The token comes from the Phase 1 desktop sign-in. This module never starts a
browser sign-in: a missing, unreadable, or broader token is unavailable
until the operator signs in again. Errors carry fixed reason codes because
Google's exception text can include token material.
"""

from __future__ import annotations

import base64
import logging
import os
from collections.abc import Callable
from email.errors import MessageError
from email.message import EmailMessage
from pathlib import Path

from google.auth.exceptions import GoogleAuthError, RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.dispatch.errors import DispatchFailed, DispatchUnavailable

logger = logging.getLogger(__name__)

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

RawMessage = dict[str, str]
Deliver = Callable[[Credentials, RawMessage], str]


class GmailSender:
    """MailSender backed by the Gmail API. Reads the token on every send."""

    def __init__(
        self,
        sender: str,
        token_path: Path,
        deliver: Deliver | None = None,
    ) -> None:
        self._sender = sender
        self._token_path = token_path
        self._deliver = deliver

    def send(self, recipient: str, subject: str, body: str) -> str:
        """Send one message and return the Gmail message id."""
        raw = build_raw_message(self._sender, recipient, subject, body)
        creds = load_credentials(self._token_path)
        # Looked up at call time so tests can replace the module-level network call.
        deliver = self._deliver or _deliver
        return deliver(creds, raw)


def build_raw_message(
    sender: str, recipient: str, subject: str, body: str
) -> RawMessage:
    """RFC 5322 bytes, base64url-encoded, as Gmail's `raw` field expects."""
    try:
        message = EmailMessage()
        message["To"] = recipient
        message["From"] = sender
        message["Subject"] = subject
        message.set_content(body)
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
    except (ValueError, MessageError) as exc:
        raise DispatchFailed("invalid_message") from exc
    return {"raw": encoded}


def load_credentials(token_path: Path) -> Credentials:
    """Return valid send-only credentials, refreshing and saving them if expired."""
    if not token_path.is_file():
        raise DispatchUnavailable("token_missing")
    try:
        # No scopes argument: passing one would replace the scopes stored in
        # the file and defeat the send-only check below.
        creds = Credentials.from_authorized_user_file(str(token_path))
    except (ValueError, OSError) as exc:
        raise DispatchUnavailable("token_unreadable") from exc
    if set(creds.scopes or []) != {GMAIL_SEND_SCOPE}:
        raise DispatchUnavailable("token_scope")
    if creds.valid:
        return creds
    if not (creds.expired and creds.refresh_token):
        raise DispatchUnavailable("token_invalid")
    _refresh(creds)
    _write_token(creds, token_path)
    return creds


def _refresh(creds: Credentials) -> None:
    try:
        creds.refresh(Request())
    except RefreshError as exc:
        logger.warning("Gmail token refresh rejected: %s", type(exc).__name__)
        raise DispatchUnavailable("token_refresh_rejected") from exc
    except GoogleAuthError as exc:
        logger.warning("Gmail token refresh failed: %s", type(exc).__name__)
        raise DispatchFailed("token_refresh_failed") from exc


def _write_token(creds: Credentials, token_path: Path) -> None:
    """Owner-only, because the file holds a refresh token."""
    fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, creds.to_json().encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(token_path, 0o600)


def _deliver(creds: Credentials, raw: RawMessage) -> str:
    """The only network call to Gmail."""
    # Imported here so loading the API does not load the Gmail client.
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        sent = service.users().messages().send(userId="me", body=raw).execute()
    except HttpError as exc:
        status = getattr(getattr(exc, "resp", None), "status", "unknown")
        logger.warning("Gmail rejected the send: HTTP %s", status)
        raise DispatchFailed("gmail_http_error") from exc
    except Exception as exc:
        logger.warning("Gmail send failed: %s", type(exc).__name__)
        raise DispatchFailed(type(exc).__name__) from exc
    return _message_id(sent)


def _message_id(sent: object) -> str:
    message_id = sent.get("id") if isinstance(sent, dict) else None
    if not isinstance(message_id, str) or not message_id:
        raise DispatchFailed("no_message_id")
    return message_id
