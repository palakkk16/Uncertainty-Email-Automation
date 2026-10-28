"""Dispatch failures. Messages are fixed reason codes, never provider text.

Google client errors can echo token material or the message itself, so the
router maps these types to fixed HTTP details.
"""

from __future__ import annotations


class DispatchError(Exception):
    """A SEND decision was not delivered."""


class DispatchUnavailable(DispatchError):
    """Dispatch cannot run until the operator fixes the Gmail token."""


class DispatchRejected(DispatchError):
    """The recipient is not on APP_DISPATCH_ALLOWED_RECIPIENTS."""


class DispatchFailed(DispatchError):
    """Gmail or the token refresh failed. The email may be retried."""
