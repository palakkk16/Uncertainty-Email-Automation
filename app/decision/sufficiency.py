"""Deterministic ASK versus SEND threshold.

SEND means every required slot is resolved. ``resolved_fraction`` is the
count of resolved slots divided by 3. That is a completeness ratio, not a
probability, not a model confidence score, and not semantic entropy.
Nothing in this module sends mail.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.extraction.compose import subject_is_grounded
from app.extraction.mentions import copied_mention, occurs_in, span_mention
from app.schemas.chat import EmailExtraction, SlotAssessment

_EMAIL_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,}"
)
_SEND_REPLY = "The decision is SEND. No email was sent."

RecipientStatus = Literal["resolved", "missing", "bare_name", "ambiguous"]
TextStatus = Literal["resolved", "missing"]


@dataclass(frozen=True)
class Draft:
    """The resolved fields of a SEND. recipient is one bare address."""

    recipient: str
    subject: str
    body: str


@dataclass(frozen=True)
class Decision:
    """One threshold outcome. clarification is null and draft is set only for SEND."""

    decision: Literal["ASK", "SEND"]
    clarification: str | None
    reply: str
    assessment: SlotAssessment
    draft: Draft | None = None


def decide(instruction: str, extraction: EmailExtraction) -> Decision:
    """Choose ASK or SEND from slot constraints. Do not send mail."""
    recipient, mention, addresses = _recipient_slot(instruction, extraction)
    subject = _text_slot(extraction.subject, instruction, must_occur=False)
    if subject == "resolved" and not subject_is_grounded(extraction.subject, instruction):
        subject = "missing"
    body = _text_slot(extraction.body, instruction, must_occur=False)
    assessment = SlotAssessment(
        method="slot_sufficiency_threshold",
        recipient=recipient,
        subject=subject,
        body=body,
        resolved_fraction=_resolved_fraction(recipient, subject, body),
    )
    question = _question(recipient, mention, addresses, subject, body)
    if question is None:
        draft = _draft(addresses, extraction)
        return Decision("SEND", None, _SEND_REPLY, assessment, draft)
    return Decision("ASK", question, question, assessment)


def _draft(addresses: list[str], extraction: EmailExtraction) -> Draft:
    """Every slot is resolved here, so a gap is a programmer error."""
    subject, body = extraction.subject, extraction.body
    if len(addresses) != 1 or subject is None or body is None:
        raise RuntimeError("SEND requires one address, a subject, and a body")
    return Draft(addresses[0], subject, body)


def _recipient_slot(
    instruction: str,
    extraction: EmailExtraction,
) -> tuple[RecipientStatus, str | None, list[str]]:
    """Classify the recipient. Ambiguous addresses outrank a copied name."""
    instruction_emails = _unique_emails(instruction)
    extracted = [
        item
        for item in _unique_emails(extraction.recipient or "")
        if occurs_in(item, instruction)
    ]
    if len(instruction_emails) > 1 or len(extracted) > 1:
        return "ambiguous", None, instruction_emails or extracted
    if len(extracted) == 1 and len(instruction_emails) <= 1:
        return "resolved", None, extracted
    if instruction_emails:
        return "missing", None, []
    mention = _bare_mention(instruction, extraction)
    if mention is not None:
        return "bare_name", mention, []
    return "missing", None, []


def _bare_mention(instruction: str, extraction: EmailExtraction) -> str | None:
    """Prefer a copied name. Fall back to the span only when that copy is absent."""
    copied = copied_mention(extraction.recipient_mention, instruction)
    if copied is not None:
        return copied
    return span_mention(instruction)


def _text_slot(
    value: str | None,
    instruction: str,
    *,
    must_occur: bool = True,
) -> TextStatus:
    """Resolved when the slot has non-empty text.

    Body may be an auto-drafted message that does not appear in the user's
    words. Subject may be a titled expansion of a topic the user stated.
    """
    if not isinstance(value, str) or not value.strip():
        return "missing"
    if not must_occur or occurs_in(value, instruction):
        return "resolved"
    return "missing"


def _resolved_fraction(
    recipient: RecipientStatus,
    subject: TextStatus,
    body: TextStatus,
) -> float:
    """Resolved slots / 3. Completeness only; bare_name and ambiguous count as open."""
    resolved = (
        recipient == "resolved",
        subject == "resolved",
        body == "resolved",
    )
    return sum(resolved) / 3


def _question(
    recipient: RecipientStatus,
    mention: str | None,
    addresses: list[str],
    subject: TextStatus,
    body: TextStatus,
) -> str | None:
    """One question. Recipient first, then subject, then body."""
    if recipient == "ambiguous":
        return _which_address(addresses)
    if recipient == "bare_name" and mention:
        return f"What is {mention}'s email address?"
    if recipient != "resolved":
        return "Which email address should I send this to?"
    if subject != "resolved":
        return "What subject should I use?"
    if body != "resolved":
        return "What should the body of the email say?"
    return None


def _which_address(addresses: list[str]) -> str:
    if len(addresses) < 2:
        return "Which email address should I use?"
    if len(addresses) == 2:
        first, second = addresses
        return f"Which email address should I use, {first} or {second}?"
    listed = ", ".join(addresses[:-1])
    return f"Which email address should I use, {listed}, or {addresses[-1]}?"


def _unique_emails(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _EMAIL_RE.findall(text):
        key = match.lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(match)
    return found
