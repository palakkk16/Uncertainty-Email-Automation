"""Direct executor that fills gaps and always records a send.

The record lives on an in-memory sink. This module does not call the
slot-sufficiency threshold and it has no clarification branch.
"""

from __future__ import annotations

import re

from app.extraction.mentions import span_mention

ASSUMED_SUBJECT = "Follow up"
UNKNOWN_RECIPIENT = "unknown@example.com"

_EMAIL_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,}"
)
_SUBJECT_RE = re.compile(r"(?i)\bsubject\s+(.+?)(?=\s+and\s+body\b|$)")
_BODY_RE = re.compile(r"(?i)\bbody\s+(.+)$")
_NAME_STOP = frozenset({"with", "and", "about", "subject", "body", "or"})


class MemorySink:
    """In-memory send attempts. Recording does not perform I/O."""

    def __init__(self) -> None:
        self.attempts: list[dict[str, str]] = []

    def record(self, recipient: str, subject: str, body: str) -> None:
        self.attempts.append(
            {"recipient": recipient, "subject": subject, "body": body}
        )


def execute(instruction: str, sink: MemorySink) -> dict[str, str]:
    """Fill whatever is missing and record one send attempt."""
    attempt = {
        "recipient": _recipient(instruction),
        "subject": _subject(instruction),
        "body": _body(instruction),
    }
    sink.record(attempt["recipient"], attempt["subject"], attempt["body"])
    return attempt


def _recipient(instruction: str) -> str:
    emails = _emails(instruction)
    if emails:
        return emails[0]
    name = _bare_name(instruction)
    if name:
        return _placeholder(name)
    return UNKNOWN_RECIPIENT


def _bare_name(instruction: str) -> str | None:
    mention = span_mention(instruction)
    if mention is None:
        return None
    kept: list[str] = []
    for word in mention.split():
        if word.lower() in _NAME_STOP:
            break
        kept.append(word)
    if not kept:
        return None
    return " ".join(kept)


def _placeholder(name: str) -> str:
    local = ".".join(part.lower() for part in name.split())
    return f"{local}@example.com"


def _subject(instruction: str) -> str:
    match = _SUBJECT_RE.search(instruction)
    if match is None:
        return ASSUMED_SUBJECT
    text = " ".join(match.group(1).split())
    if not text:
        return ASSUMED_SUBJECT
    return text


def _body(instruction: str) -> str:
    match = _BODY_RE.search(instruction)
    if match is None:
        return instruction.strip()
    text = " ".join(match.group(1).split())
    if not text:
        return instruction.strip()
    return text


def _emails(instruction: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _EMAIL_RE.findall(instruction):
        key = match.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(match)
    return found
