"""Best-effort field copy when Gemini is unavailable. Does not invent text."""

from __future__ import annotations

import re

from app.extraction.mentions import copied_mention, span_mention
from app.schemas.chat import EmailExtraction

_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
_QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')
_TO_NAME_RE = re.compile(
    r"(?i)\b(?:to|mail|send)\s+(?!an?\b)([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,2})"
)
_FOR_SUBJECT_RE = re.compile(
    r"(?i)\bfor\s+(.+?)(?=\s+and\s+body\b|\s+with\s+body\b|\n|$)"
)
_COMMAND_RE = re.compile(
    r"(?i)^(send|e-?mail|mail|message|write|contact)\b"
)


def local_regex_extract(instruction: str) -> EmailExtraction:
    """Copy an address, a name, and quoted or follow-up subject/body from the instruction."""
    emails = _EMAIL_RE.findall(instruction)
    recipient = emails[0] if emails else None
    quoted = [" ".join((group or "").split()) for group in _quoted_parts(instruction)]
    quoted = [part for part in quoted if part]
    mention = None
    if recipient is None:
        mention = copied_mention(span_mention(instruction) or _to_mention(instruction), instruction)
    fields = EmailExtraction(
        recipient=recipient,
        recipient_mention=mention,
        subject=quoted[0] if quoted else _for_subject(instruction),
        body=quoted[1] if len(quoted) > 1 else None,
    )
    return apply_followup_slots(instruction, fields)


def apply_followup_slots(instruction: str, fields: EmailExtraction) -> EmailExtraction:
    """Fill the next open text slot from the latest user line when it is a short answer.

    The frontend joins turns with newlines. A reply such as "leave approval"
    after a subject question is that last line, not a new email command.
    """
    subject = fields.subject or _for_subject(instruction)
    body = fields.body
    last = _last_line(instruction)
    if last is not None and _is_slot_answer(last) and "@" not in last:
        if subject is None:
            subject = last
        elif body is None:
            body = last
    if subject == fields.subject and body == fields.body:
        return fields
    return EmailExtraction(
        recipient=fields.recipient,
        recipient_mention=fields.recipient_mention,
        subject=subject,
        body=body,
    )


def _quoted_parts(instruction: str) -> list[str]:
    parts: list[str] = []
    for first, second in _QUOTED_RE.findall(instruction):
        parts.append(first or second)
    return parts


def _to_mention(instruction: str) -> str | None:
    match = _TO_NAME_RE.search(instruction)
    if match is None:
        return None
    return match.group(1)


def _for_subject(instruction: str) -> str | None:
    match = _FOR_SUBJECT_RE.search(instruction)
    if match is None:
        return None
    text = " ".join(match.group(1).split())
    if not text or "@" in text or _COMMAND_RE.search(text):
        return None
    return text


def _last_line(instruction: str) -> str | None:
    lines = [" ".join(part.split()) for part in instruction.splitlines() if part.strip()]
    if len(lines) < 2:
        return None
    return lines[-1]


def _is_slot_answer(text: str) -> bool:
    if not text or _COMMAND_RE.search(text) or len(text) > 200:
        return False
    return 1 <= len(text.split()) <= 20
