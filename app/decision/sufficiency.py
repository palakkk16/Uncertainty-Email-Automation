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

from app.extraction.compose import compose_missing_body, subject_is_grounded
from app.extraction.heuristic import local_regex_extract
from app.extraction.mentions import copied_mention, occurs_in, span_mention
from app.schemas.chat import EmailExtraction, SlotAssessment

_EMAIL_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,}"
)
_SEND_REPLY = "The decision is SEND. No email was sent."
RECIPIENT_QUESTION = (
    "Who should I send this email to? Please provide their email address."
)
SUBJECT_QUESTION = "What subject should I use?"
BODY_QUESTION = "What should the body of the email say?"

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
    last_question = _inferred_last_question(instruction)
    extraction = _absorb_same_slot_answer(instruction, extraction, last_question)
    recipient, mention, addresses, subject, body, assessment = _assess(
        instruction, extraction
    )
    question = _question(recipient, mention, addresses, subject, body)
    if question is not None and question == last_question:
        extraction = _fill_from_last_reply(instruction, extraction, question)
        recipient, mention, addresses, subject, body, assessment = _assess(
            instruction, extraction
        )
        question = _question(recipient, mention, addresses, subject, body)
        if question == last_question:
            question = None
    if question is None:
        draft = _draft(addresses, extraction)
        return Decision("SEND", None, _SEND_REPLY, assessment, draft)
    return Decision("ASK", question, question, assessment)


def _assess(
    instruction: str, extraction: EmailExtraction
) -> tuple[RecipientStatus, str | None, list[str], TextStatus, TextStatus, SlotAssessment]:
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
    return recipient, mention, addresses, subject, body, assessment


def _inferred_last_question(instruction: str) -> str | None:
    """What the agent asked on the previous user text, if this is a follow-up."""
    last = _last_line(instruction)
    if last is None:
        return None
    prior = _without_last_line(instruction)
    fields = local_regex_extract(prior)
    recipient, mention, addresses, subject, body, _assessment = _assess(prior, fields)
    return _question(recipient, mention, addresses, subject, body)


def _absorb_same_slot_answer(
    instruction: str,
    extraction: EmailExtraction,
    last_question: str | None,
) -> EmailExtraction:
    if last_question is None:
        return extraction
    return _fill_from_last_reply(instruction, extraction, last_question)


def _fill_from_last_reply(
    instruction: str,
    extraction: EmailExtraction,
    question: str,
) -> EmailExtraction:
    last = _last_line(instruction)
    if last is None:
        return extraction
    subject = extraction.subject
    body = extraction.body
    if question == SUBJECT_QUESTION:
        subject = last
    elif question == BODY_QUESTION:
        body = body or last
    else:
        return extraction
    return compose_missing_body(
        instruction,
        EmailExtraction(
            recipient=extraction.recipient,
            recipient_mention=extraction.recipient_mention,
            subject=subject,
            body=body,
        ),
    )


def _last_line(instruction: str) -> str | None:
    lines = [" ".join(part.split()) for part in instruction.splitlines() if part.strip()]
    if len(lines) < 2:
        return None
    return lines[-1]


def _without_last_line(instruction: str) -> str:
    lines = [part.strip() for part in instruction.splitlines() if part.strip()]
    if len(lines) < 2:
        return instruction
    return "\n".join(lines[:-1])


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
    if recipient != "resolved":
        return RECIPIENT_QUESTION
    if subject != "resolved":
        return SUBJECT_QUESTION
    if body != "resolved":
        return BODY_QUESTION
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
