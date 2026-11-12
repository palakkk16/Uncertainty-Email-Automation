"""Turn a short topic into a complete professional email.

Recipient addresses stay copy-only. Subject and body are drafted so a
fragment such as "for sick leave approval" is never sent as the message.
"""

from __future__ import annotations

import os
import re

from app.extraction.mentions import occurs_in, span_mention
from app.schemas.chat import EmailExtraction

_GREETING_RE = re.compile(r"(?i)^(hi|hello|dear|hey)\b")
_SIGNOFF_RE = re.compile(r"(?i)\b(best regards|kind regards|sincerely|thanks|thank you)\b")
_SICK_RE = re.compile(r"(?i)\bsick\b|\bunwell\b|\bill\b")
_LEAVE_RE = re.compile(r"(?i)\bleave\b|\bvacation\b|\btime off\b|\babsent\b")
_INVITE_RE = re.compile(r"(?i)\binvit|\bwedding\b|\bbirthday\b|\banniversary\b")
_MEETING_RE = re.compile(r"(?i)\bmeeting\b|\bcall\b|\bstandup\b|\bsync\b")
_PROJECT_RE = re.compile(r"(?i)\bproject\b|\bupdate\b|\bstatus\b|\bprogress\b")
_WHEN_RE = re.compile(
    r"(?i)\b(?:today|tomorrow|tonight|monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday)"
    r"(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)?"
    r"|\bat\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)"
)
_SMALL = frozenset({"a", "an", "and", "at", "for", "in", "of", "on", "or", "the", "to"})
_ABOUT_RE = re.compile(r"(?i)\b(?:about|regarding)\s+(.+)$")


def compose_missing_body(instruction: str, fields: EmailExtraction) -> EmailExtraction:
    """Draft a titled subject and a full body when the user stated an intent."""
    topic = _topic(instruction, fields)
    if not _has_text(topic):
        return fields
    subject = _professional_subject(topic)
    body = fields.body
    if _is_fragment(body, topic):
        body = _full_email(topic, fields, instruction)
    return EmailExtraction(
        recipient=fields.recipient,
        recipient_mention=fields.recipient_mention,
        subject=subject,
        body=body,
    )


def _topic(instruction: str, fields: EmailExtraction) -> str | None:
    if _has_text(fields.subject) and _grounded(fields.subject, instruction):
        return _strip_for(fields.subject)
    about = _about_phrase(instruction)
    if about:
        return about
    if _has_text(fields.subject):
        return _strip_for(fields.subject)
    if _has_text(fields.body) and _is_fragment(fields.body, fields.body):
        return _strip_for(fields.body)
    return None


def _professional_subject(topic: str) -> str:
    kind = _kind(topic)
    titled = _normalize_clock(_title_case(_strip_for(topic)))
    if kind == "sick_leave":
        return "Request for Sick Leave Approval"
    if kind == "leave":
        return "Request for Leave Approval"
    if kind == "invitation":
        if "wedding" in topic.lower():
            return "Wedding Invitation"
        return titled if "invitation" in titled.lower() else f"{titled} Invitation"
    if kind == "meeting":
        return titled if "meeting" in titled.lower() else f"Meeting: {titled}"
    if kind == "project":
        return titled if "update" in titled.lower() else f"{titled} Update"
    return titled


def _full_email(topic: str, fields: EmailExtraction, instruction: str) -> str:
    name = _addressee(fields, instruction)
    when = _when(instruction, topic)
    paragraph = _paragraph(_kind(topic), topic, when)
    signer = _signer_name()
    return f"Hi {name},\n\n{paragraph}\n\nBest regards,\n{signer}"


def _paragraph(kind: str, topic: str, when: str) -> str:
    extra = f" {when.strip()}." if when else "."
    if kind == "sick_leave":
        return (
            "I am writing to request approval for sick leave as I am currently "
            "unwell and unable to attend work or classes today. Please let me "
            "know if any additional details are needed."
        )
    if kind == "leave":
        return (
            "I am writing to request approval for leave. Please let me know if "
            "any additional details are needed."
        )
    if kind == "invitation":
        occasion = _strip_for(topic)
        return (
            f"I would like to invite you to {occasion}. I hope you can join, "
            "and please let me know if you have any questions."
        )
    if kind == "meeting":
        return (
            f"I am writing to schedule a meeting{extra} Please confirm whether "
            "that time works for you, or suggest an alternative."
        )
    if kind == "project":
        return (
            "I am writing to share a project update. Please let me know if you "
            "would like more detail on progress, blockers, or next steps."
        )
    purpose = _strip_for(topic)
    return (
        f"I am writing regarding {purpose}. Please let me know if any "
        "additional details are needed."
    )


def _kind(topic: str) -> str:
    if _SICK_RE.search(topic) and _LEAVE_RE.search(topic):
        return "sick_leave"
    if _LEAVE_RE.search(topic):
        return "leave"
    if _INVITE_RE.search(topic):
        return "invitation"
    if _MEETING_RE.search(topic):
        return "meeting"
    if _PROJECT_RE.search(topic):
        return "project"
    return "general"


def _is_fragment(value: str | None, topic: str | None) -> bool:
    if not _has_text(value):
        return True
    text = value.strip()
    if _GREETING_RE.search(text) and _SIGNOFF_RE.search(text) and len(text) >= 80:
        return False
    folded = " ".join(text.split()).lower()
    topic_fold = " ".join((topic or "").split()).lower()
    if topic_fold and folded == topic_fold:
        return True
    if "\n" not in text and len(text) < 80:
        return True
    return not (_GREETING_RE.search(text) and _SIGNOFF_RE.search(text))


def _addressee(fields: EmailExtraction, instruction: str) -> str:
    mention = fields.recipient_mention or span_mention(instruction)
    if mention:
        return mention.split()[0].capitalize()
    local = (fields.recipient or "").split("@", 1)[0]
    letters = re.sub(r"[^A-Za-z]", "", local)
    if 2 <= len(letters) <= 16 and letters.isalpha():
        return letters.capitalize()
    return "there"


def _signer_name() -> str:
    explicit = os.environ.get("APP_SIGNER_NAME", "").strip()
    if explicit:
        return explicit.split()[0]
    return "Palak"


def _when(instruction: str, topic: str) -> str:
    blob = f"{topic} {instruction}"
    match = _WHEN_RE.search(blob)
    if match is None:
        return ""
    return _normalize_clock(" ".join(match.group(0).split()))


def _title_case(phrase: str) -> str:
    words = phrase.split()
    titled: list[str] = []
    for index, word in enumerate(words):
        lower = word.lower()
        if index > 0 and lower in _SMALL:
            titled.append(lower)
        else:
            titled.append(lower[:1].upper() + lower[1:] if lower else word)
    return " ".join(titled)


def _normalize_clock(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        mer = match.group(2).upper().replace(".", "")
        return f"{match.group(1)} {mer}"

    return re.sub(r"(?i)(\d{1,2}(?::\d{2})?)\s*([ap]\.?m\.?)", repl, text)


def _strip_for(value: str) -> str:
    text = " ".join(value.split()).strip()
    if text.lower().startswith("for "):
        text = text[4:].strip()
    return text


def _about_phrase(instruction: str) -> str | None:
    match = _ABOUT_RE.search(" ".join(instruction.split()))
    if match is None:
        return None
    text = " ".join(match.group(1).split())
    return text or None


def _grounded(value: str, instruction: str) -> bool:
    if occurs_in(value, instruction):
        return True
    folded = " ".join(instruction.split()).lower()
    tokens = [token.strip(".,:;!?") for token in value.lower().split()]
    content = [token for token in tokens if token not in _SMALL and len(token) > 2]
    if not content:
        return False
    hits = sum(1 for token in content if token in folded)
    return hits >= min(2, len(content))


def _has_text(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())
