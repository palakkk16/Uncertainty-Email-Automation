"""Best-effort field copy when Gemini is unavailable.

Recipient stays copy-only. A short topic becomes a titled subject and a
complete drafted body so a fragment is never sent as the message.
"""

from __future__ import annotations

import re

from app.extraction.compose import compose_missing_body, subject_is_grounded
from app.extraction.mentions import copied_mention, span_mention
from app.schemas.chat import EmailExtraction

_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)
_QUOTED_RE = re.compile(r'"([^"]+)"|\'([^\']+)\'')
_TO_NAME_RE = re.compile(
    r"(?i)\b(?:to|mail|send)\s+(?!an?\b)([A-Za-z][A-Za-z'-]*)"
)
_FOR_SUBJECT_RE = re.compile(
    r"(?i)\bfor\s+(.+?)(?=\s+and\s+body\b|\s+with\s+body\b|\n|$)"
)
_SUBJECT_LABEL_RE = re.compile(
    r"(?i)\bsubject\s+(?:is\s+|:\s*)?(.+?)(?=\s+and\s+body\b|\s+with\s+body\b|\n|$)"
)
_BODY_LABEL_RE = re.compile(
    r"(?i)\b(?:and\s+)?body\s+(?:is\s+|:\s*)?(.+)$"
)
_COMMAND_RE = re.compile(
    r"(?i)^(send|e-?mail|mail|message|write|contact)\b"
)
_AFTER_EMAIL_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\s+(.+)$"
)
_INTENT_RE = re.compile(
    r"(?i)\b(?:about|regarding|asking)\s+(.+?)(?=\s+and\s+body\b|\s+with\s+body\b|\n|$)"
)


def local_regex_extract(instruction: str) -> EmailExtraction:
    """Copy an address and a name, then draft subject and body from the topic."""
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
        subject=quoted[0] if quoted else _stated_subject(instruction),
        body=quoted[1] if len(quoted) > 1 else _labeled_body(instruction),
    )
    return apply_followup_slots(instruction, fields)


def apply_followup_slots(instruction: str, fields: EmailExtraction) -> EmailExtraction:
    """Fill the open slot from the latest short reply, then draft the email.

    The frontend joins turns with newlines. After "What subject should I use?",
    a reply such as "your outfit" is that last line, not a new email command.
    An earlier ungrounded subject guess must not hide that answer.
    """
    last = _last_line(instruction)
    recipient, mention, subject, body = _merge_last_line(
        instruction,
        last,
        fields.recipient,
        fields.recipient_mention,
        fields.subject or _stated_subject(instruction),
        fields.body,
    )
    fields = EmailExtraction(
        recipient=recipient,
        recipient_mention=mention,
        subject=subject,
        body=body,
    )
    return compose_missing_body(instruction, fields)


def _merge_last_line(
    instruction: str,
    last: str | None,
    recipient: str | None,
    mention: str | None,
    subject: str | None,
    body: str | None,
) -> tuple[str | None, str | None, str | None, str | None]:
    if last is None or not _is_slot_answer(last):
        return recipient, mention, subject, body
    emails = _EMAIL_RE.findall(last)
    if emails and recipient is None:
        return emails[0], mention, subject, body
    if "@" in last:
        return recipient, mention, subject, body
    prior = _without_last_line(instruction)
    if not _keep_subject(subject, prior, body):
        return recipient, mention, last, body
    if body is None:
        return recipient, mention, subject, last
    return recipient, mention, subject, body


def _keep_subject(
    subject: str | None, prior: str, body: str | None
) -> bool:
    """Keep a subject only when the prior turn would already accept it."""
    if not subject:
        return False
    preview = compose_missing_body(
        prior,
        EmailExtraction(recipient=None, subject=subject, body=body),
    )
    return subject_is_grounded(preview.subject, prior)


def _without_last_line(instruction: str) -> str:
    lines = [part.strip() for part in instruction.splitlines() if part.strip()]
    if len(lines) < 2:
        return instruction
    return "\n".join(lines[:-1])


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


def _stated_subject(instruction: str) -> str | None:
    return (
        _for_subject(instruction)
        or _labeled_subject(instruction)
        or _intent_subject(instruction)
        or _after_address_topic(instruction)
    )


def _intent_subject(instruction: str) -> str | None:
    match = _INTENT_RE.search(" ".join(instruction.split()))
    if match is None:
        return None
    text = " ".join(match.group(1).split())
    if not text or "@" in text or _COMMAND_RE.search(text):
        return None
    return text


def _for_subject(instruction: str) -> str | None:
    match = _FOR_SUBJECT_RE.search(instruction)
    if match is None:
        return None
    text = " ".join(match.group(1).split())
    if not text or "@" in text or _COMMAND_RE.search(text):
        return None
    return text


def _labeled_subject(instruction: str) -> str | None:
    match = _SUBJECT_LABEL_RE.search(instruction)
    if match is None:
        return None
    text = " ".join(match.group(1).split())
    if not text or "@" in text:
        return None
    return text


def _after_address_topic(instruction: str) -> str | None:
    match = _AFTER_EMAIL_RE.search(" ".join(instruction.split()))
    if match is None:
        return None
    text = " ".join(match.group(1).split())
    lowered = text.lower()
    if lowered.startswith(("for ", "with ", "subject ", "and body")):
        return None
    if not text or "@" in text or _COMMAND_RE.search(text):
        return None
    return text


def _labeled_body(instruction: str) -> str | None:
    match = _BODY_LABEL_RE.search(instruction)
    if match is None:
        return None
    text = " ".join(match.group(1).split())
    return text or None


def _last_line(instruction: str) -> str | None:
    lines = [" ".join(part.split()) for part in instruction.splitlines() if part.strip()]
    if len(lines) < 2:
        return None
    return lines[-1]


def _is_slot_answer(text: str) -> bool:
    if not text or _COMMAND_RE.search(text) or len(text) > 200:
        return False
    return 1 <= len(text.split()) <= 20
