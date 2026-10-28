"""Gmail dispatch for SEND decisions. Off unless APP_DISPATCH_ENABLED is true."""

from app.dispatch.dispatcher import Dispatcher, MailSender, get_dispatcher
from app.dispatch.errors import (
    DispatchError,
    DispatchFailed,
    DispatchRejected,
    DispatchUnavailable,
)
from app.dispatch.guard import DuplicateGuard

__all__ = [
    "DispatchError",
    "DispatchFailed",
    "DispatchRejected",
    "DispatchUnavailable",
    "Dispatcher",
    "DuplicateGuard",
    "MailSender",
    "get_dispatcher",
]
