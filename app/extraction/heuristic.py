"""Best-effort field copy when Gemini is unavailable.

Recipient and subject stay copy-only. A missing body is drafted only when
the instruction already states a subject or an explicit intent such as
leave approval.
"""

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


def compose_missing_body(instruction: str, fields: EmailExtraction) -> EmailExtraction:
    """Draft a professional body when the user stated a subject or intent."""
    if _has_text(fields.body):
        return fields
    subject = fields.subject or _for_subject(instruction)
    if not _has_text(subject):
        return fields
    return EmailExtraction(
        recipient=fields.recipient,
        recipient_mention=fields.recipient_mention,
        subject=subject,
        body=_professional_body(subject, fields, instruction),
    )


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
    if subject != fields.subject or body != fields.body:
        fields = EmailExtraction(
            recipient=fields.recipient,
            recipient_mention=fields.recipient_mention,
            subject=subject,
            body=body,
        )
    return compose_missing_body(instruction, fields)


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


def _professional_body(
    subject: str, fields: EmailExtraction, instruction: str
) -> str:
    name = _addressee(fields, instruction)
    purpose = _purpose_sentence(subject)
    return (
        f"Dear {name},\n\n"
        f"{purpose} Please let me know if any further details are required.\n\n"
        "Best regards,"
    )


def _addressee(fields: EmailExtraction, instruction: str) -> str:
    mention = fields.recipient_mention or span_mention(instruction)
    if mention:
        return mention.split()[0].capitalize()
    local = (fields.recipient or "").split("@", 1)[0]
    if local.isalpha():
        return local.capitalize()
    return "there"


def _purpose_sentence(subject: str) -> str:
    if "leave" in subject.lower():
        return "I am writing to request approval for leave."
    return f"I am writing regarding {subject.strip()}."


def _has_text(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())
