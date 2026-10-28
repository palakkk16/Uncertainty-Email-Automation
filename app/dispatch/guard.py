"""In-process guard against sending the same email twice in a short window.

The chat page re-posts every earlier user turn, so a complete instruction
comes back with the next message. Keys are SHA-256 digests, so the guard
never holds recipient, subject, or body text. State is per process and is
lost on restart.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections.abc import Callable

DEFAULT_WINDOW_SECONDS = 600.0


class DuplicateGuard:
    """Thread-safe set of recently claimed keys. Sync routes run in a threadpool."""

    def __init__(
        self,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._window = window_seconds
        self._clock = clock
        self._claimed: dict[str, float] = {}
        self._lock = threading.Lock()

    def claim(self, key: str) -> bool:
        """Reserve key. False when it was already claimed within the window."""
        with self._lock:
            now = self._clock()
            self._claimed = {
                item: at
                for item, at in self._claimed.items()
                if now - at < self._window
            }
            if key in self._claimed:
                return False
            self._claimed[key] = now
            return True

    def release(self, key: str) -> None:
        """Forget key so a send that failed can be retried."""
        with self._lock:
            self._claimed.pop(key, None)


def message_key(recipient: str, subject: str, body: str) -> str:
    """Digest of one email. Addresses compare case-insensitively."""
    joined = "\x1f".join((recipient.lower(), subject, body))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
