"""Person mentions copied from the instruction, plus a closed span check.

A mention is kept only when that text occurs in the instruction. This module
does not invent an address and does not choose ASK versus SEND.
"""

from __future__ import annotations

import re

# Closed list so the span check stays deterministic. It is not a name tagger.
_NOT_NAMES = frozenset(
    {
        "a",
        "about",
        "an",
        "and",
        "asking",
        "at",
        "body",
        "contact",
        "email",
        "everyone",
        "for",
        "from",
        "fwd",
        "her",
        "him",
        "mail",
        "me",
        "message",
        "on",
        "or",
        "please",
        "re",
        "regarding",
        "someone",
        "somebody",
        "subject",
        "that",
        "the",
        "them",
        "this",
        "to",
        "today",
        "tomorrow",
        "with",
        "write",
    }
)

# A recipient verb, then an optional "to". Used only when no address is present.
_LEAD = re.compile(
    r"(?i)\b(?:send\s+an?\s+)?(?:e-?mail|mail|message|write|contact)\s+(?:to\s+)?"
)


def occurs_in(needle: str | None, instruction: str) -> bool:
    """True when needle is a non-empty phrase inside the instruction."""
    if not isinstance(needle, str):
        return False
    cleaned = " ".join(needle.split()).lower()
    if not cleaned:
        return False
    folded = " ".join(instruction.split()).lower()
    return cleaned in folded


def copied_mention(value: str | None, instruction: str) -> str | None:
    """Return a short name the instruction contains, otherwise None."""
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    if not cleaned or "@" in cleaned or not occurs_in(cleaned, instruction):
        return None
    words = cleaned.split()
    if not words or len(words) > 3 or not all(_name_token(word) for word in words):
        return None
    return cleaned


def span_mention(instruction: str) -> str | None:
    """Name tokens right after an email verb, if those tokens are still present."""
    match = _LEAD.search(instruction)
    if match is None:
        return None
    kept = _take_name(instruction[match.end() :])
    if not kept:
        return None
    return " ".join(kept)


def _take_name(rest: str) -> list[str]:
    kept: list[str] = []
    for raw in rest.split():
        word = raw.strip(".,;:!?\"'()[]")
        if not _name_token(word):
            break
        kept.append(word)
        if len(kept) == 3:
            break
    return kept


def _name_token(word: str) -> bool:
    if not word or word.lower() in _NOT_NAMES:
        return False
    letters = word.replace("-", "").replace("'", "")
    return bool(letters) and letters.isalpha()
