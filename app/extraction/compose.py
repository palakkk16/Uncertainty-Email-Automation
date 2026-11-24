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
_PROJECT_RE = re.compile(r"(?i)\bproject\b|\bupdate\b|\bstatus\b|\bprogress\b|\bsubmission\b")
_OUTFIT_RE = re.compile(r"(?i)\bwear(?:ing)?\b|\boutfit\b")
_WHEN_RE = re.compile(
    r"(?i)\b(?:today|tomorrow|tonight|monday|tuesday|wednesday|"
    r"thursday|friday|saturday|sunday)"
    r"(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)?"
    r"|\bat\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)"
)
_SMALL = frozenset({"a", "an", "and", "at", "for", "in", "of", "on", "or", "the", "to"})
_SUBJECT_STOP = _SMALL | frozenset(
    {
        "about",
        "email",
        "mail",
        "please",
        "regarding",
        "request",
        "the",
    }
)
_ABOUT_RE = re.compile(r"(?i)\b(?:about|regarding)\s+(.+)$")
_ASKING_RE = re.compile(r"(?i)\basking\s+(.+)$")
_HEADACHE_RE = re.compile(r"(?i)\bheadache\b|\bmigraine\b|\bfeel better\b")
_WELLBEING_SUBJECT = "Checking In — Hope You Feel Better"
_META_LEAD_RE = re.compile(
    r"(?i)^(?:please\s+)*(?:"
    r"frame\s+it(?:\s+according\s+to\s+you)?"
    r"|according\s+to\s+you"
    r"|you\s+decide"
    r"|decide\s+(?:it\s+)?yourself"
    r"|frame\s+a\s+subject"
    r"|suggest\s+a\s+(?:subject|title)"
    r"|anything\s+suitable"
    r"|write\s+it\s+yourself"
    r"|you\s+choose"
    r")\b[\s:,-]*"
)
_META_ANY_RE = re.compile(
    r"(?i)\b(?:"
    r"frame\s+it(?:\s+according\s+to\s+you)?"
    r"|according\s+to\s+you"
    r"|you\s+decide"
    r"|decide\s+(?:it\s+)?yourself"
    r"|frame\s+a\s+subject"
    r"|suggest\s+a\s+(?:subject|title)"
    r"|anything\s+suitable"
    r"|write\s+it\s+yourself"
    r"|you\s+choose"
    r")\b"
)
_TOPIC_LEAD_RE = re.compile(
    r"(?i)^(?:please\s+)*(?:for|about|regarding|asking(?:\s+about)?|to)\s+"
)
_HOLLOW_TOPIC = frozenset(
    {"it", "this", "that", "them", "yourself", "subject", "a subject", "the subject"}
)
_BANNED_SUBJECT = re.compile(r"(?i)frame it|according to you|asking about")
_COMMAND_START_RE = re.compile(
    r"(?i)^(send|e-?mail|mail|message|write|contact)\b"
)


def compose_missing_body(instruction: str, fields: EmailExtraction) -> EmailExtraction:
    """Draft a titled subject and a full body when the user stated an intent."""
    topic = _topic(instruction, fields)
    if not _has_text(topic):
        subject = fields.subject
        if _has_text(subject) and is_meta_subject_instruction(subject):
            subject = None
        return EmailExtraction(
            recipient=fields.recipient,
            recipient_mention=fields.recipient_mention,
            subject=subject,
            body=_without_friend_placeholder(fields.body, fields, instruction),
        )
    subject = _professional_subject(topic)
    body = fields.body
    if _is_fragment(body, topic):
        body = _full_email(topic, fields, instruction)
    return EmailExtraction(
        recipient=fields.recipient,
        recipient_mention=fields.recipient_mention,
        subject=subject,
        body=_without_friend_placeholder(body, fields, instruction),
    )


def is_meta_subject_instruction(text: str) -> bool:
    """True when the user asked the agent to invent a subject."""
    folded = " ".join(text.split())
    return bool(_META_LEAD_RE.search(folded) or _META_ANY_RE.search(folded))


def underlying_topic(text: str) -> str | None:
    """Strip meta-instructions and leftover 'asking about' / 'for' leads."""
    cleaned = _strip_topic_leads(_strip_meta(text))
    if not cleaned or cleaned.lower() in _HOLLOW_TOPIC:
        return None
    return cleaned


def _topic(instruction: str, fields: EmailExtraction) -> str | None:
    last = _last_nonempty_line(instruction)
    if last:
        follow = _followup_topic(last)
        if follow:
            return follow
        if is_meta_subject_instruction(last):
            return _topic_from_context(_without_last_line(instruction), fields)
    return _topic_from_context(instruction, fields)


def _followup_topic(text: str) -> str | None:
    """A short last-line reply after a clarification is the topic, not a new command."""
    cleaned = " ".join(text.split())
    if not cleaned or "@" in cleaned or len(cleaned) > 200:
        return None
    if not (1 <= len(cleaned.split()) <= 20):
        return None
    if is_meta_subject_instruction(cleaned):
        return underlying_topic(cleaned)
    if _COMMAND_START_RE.search(cleaned):
        return None
    return underlying_topic(cleaned) or cleaned


def _topic_from_context(instruction: str, fields: EmailExtraction) -> str | None:
    subject = fields.subject
    if _has_text(subject) and is_meta_subject_instruction(subject):
        cleaned = underlying_topic(subject)
        if cleaned:
            return cleaned
        subject = None
    if _has_text(subject) and _grounded(subject, instruction):
        return underlying_topic(subject) or _strip_for(subject)
    about = _about_phrase(instruction)
    if about:
        return underlying_topic(about) or about
    asking = _asking_phrase(instruction)
    if asking:
        return underlying_topic(asking) or asking
    if _has_text(subject):
        return underlying_topic(subject) or _strip_for(subject)
    if _has_text(fields.body) and _is_fragment(fields.body, fields.body):
        return underlying_topic(fields.body) or _strip_for(fields.body)
    return None


def _professional_subject(topic: str) -> str:
    topic = underlying_topic(topic) or _strip_for(topic)
    titled = _normalize_clock(_title_case(_strip_for(topic)))
    # A longer user phrase is already a subject. Keep their words so the
    # title stays grounded instead of swapping in a generic template.
    if len(topic.split()) >= 4:
        return titled
    kind = _kind(topic)
    if kind == "sick_leave":
        return "Request for Sick Leave Approval"
    if kind == "leave":
        when = _when(topic, topic)
        if when:
            return f"Leave Request for {_title_case(when)}"
        if "vacation" in topic.lower():
            return "Request for Vacation Permission"
        return "Request for Leave Approval"
    if kind == "wellbeing":
        return _WELLBEING_SUBJECT
    if kind == "invitation":
        if "wedding" in topic.lower():
            return "Wedding Invitation"
        return titled if "invitation" in titled.lower() else f"{titled} Invitation"
    if kind == "meeting":
        return titled if "meeting" in titled.lower() else f"Meeting: {titled}"
    if kind == "project":
        if "submission" in topic.lower():
            return "Regarding Project Submission"
        lower = titled.lower()
        if "update" in lower:
            return titled
        return f"{titled} Update"
    if kind == "outfit":
        return titled if "wear" in titled.lower() or "outfit" in titled.lower() else "Outfit"
    if _BANNED_SUBJECT.search(titled):
        return _title_case(topic) if topic and not _BANNED_SUBJECT.search(topic) else titled
    return titled


def _full_email(topic: str, fields: EmailExtraction, instruction: str) -> str:
    name = _addressee(fields, instruction)
    when = _when(instruction, topic)
    paragraph = _paragraph(_kind(topic), topic, when)
    signer = _signer_name()
    closing = f"Best regards,\n{signer}" if signer else "Best regards,"
    return f"{_greeting(name)}\n\n{paragraph}\n\n{closing}"


def _paragraph(kind: str, topic: str, when: str) -> str:
    extra = f" {when.strip()}." if when else "."
    if kind == "sick_leave":
        return (
            "I am writing to request approval for sick leave as I am currently "
            "unwell and unable to attend work or classes today. Please let me "
            "know if any additional details are needed."
        )
    if kind == "leave":
        if "vacation" in topic.lower():
            return (
                "I am writing to request permission to go on vacation. "
                "Please let me know if any additional details are needed."
            )
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
        if "submission" in topic.lower():
            return (
                "I am writing regarding the project submission. Please let me "
                "know if any additional details are needed."
            )
        return (
            "I am writing to share a project update. Please let me know if you "
            "would like more detail on progress, blockers, or next steps."
        )
    if kind == "outfit":
        return (
            "I wanted to ask about your outfit and what you will be wearing "
            "so I can plan accordingly. Please let me know when you have a chance."
        )
    if kind == "wellbeing":
        return (
            "I wanted to check in and hope you feel better soon. "
            "Please take care, and let me know if there is anything I can do."
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
    if _OUTFIT_RE.search(topic):
        return "outfit"
    if _HEADACHE_RE.search(topic) or _SICK_RE.search(topic):
        return "wellbeing"
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


_MAX_FIRST_NAME = 10
_CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])")
_SURNAMES = frozenset(
    {
        "aggarwal",
        "agrawal",
        "arora",
        "banerjee",
        "bhatia",
        "bhatt",
        "chauhan",
        "chatterjee",
        "chopra",
        "choudhary",
        "desai",
        "dhillon",
        "dubey",
        "gill",
        "goel",
        "goyal",
        "gupta",
        "iyer",
        "jain",
        "johnson",
        "joshi",
        "kapoor",
        "kaur",
        "khan",
        "kohli",
        "kumar",
        "malhotra",
        "mehta",
        "menon",
        "mishra",
        "mukherjee",
        "nair",
        "nanda",
        "pandey",
        "patel",
        "punjabi",
        "reddy",
        "saxena",
        "shah",
        "sharma",
        "singh",
        "smith",
        "thakur",
        "tiwari",
        "tripathi",
        "verma",
        "williams",
        "yadav",
    }
)
_SURNAMES_BY_LENGTH = tuple(sorted(_SURNAMES, key=len, reverse=True))


def _greeting(name: str | None) -> str:
    return f"Hi {name}," if name else "Hi there,"


def _addressee(fields: EmailExtraction, instruction: str) -> str | None:
    mention = fields.recipient_mention or span_mention(instruction)
    if mention:
        token = mention.split()[0]
        name = _plausible_first(token) or _first_name_from_local(token)
        if name:
            return name
    local = (fields.recipient or "").split("@", 1)[0]
    return _first_name_from_local(local)


def _first_name_from_local(local: str) -> str | None:
    """Derive a short first name from jane.doe, palakpunjabi6, PalakPunjabi."""
    tokens = _split_local_tokens(local)
    if not tokens:
        return None
    first = _letters_prefix(tokens[0])
    if len(tokens) >= 2:
        return _plausible_first(first)
    stripped = _strip_surname_suffix(first.lower())
    if stripped:
        return _plausible_first(stripped)
    return _plausible_first(first)


def _split_local_tokens(local: str) -> list[str]:
    trimmed = re.sub(r"[^A-Za-z._-]+$", "", local).strip("._-")
    if not trimmed:
        return []
    tokens: list[str] = []
    for part in re.split(r"[._-]+", trimmed):
        if not part:
            continue
        chunks = _CAMEL_RE.findall(part)
        if chunks and "".join(chunks) == part:
            tokens.extend(chunks)
        else:
            tokens.append(part)
    return tokens


def _letters_prefix(token: str) -> str:
    match = re.match(r"[A-Za-z]+", token)
    return match.group(0) if match else ""


def _strip_surname_suffix(word: str) -> str | None:
    for surname in _SURNAMES_BY_LENGTH:
        if word.endswith(surname) and len(word) > len(surname):
            return word[: -len(surname)]
    return None


def _plausible_first(name: str) -> str | None:
    if not name or not name.isalpha() or name.lower() == "friend":
        return None
    if 2 <= len(name) <= _MAX_FIRST_NAME:
        return name[:1].upper() + name[1:].lower()
    return None


def _signer_name() -> str | None:
    explicit = os.environ.get("APP_SIGNER_NAME", "").strip()
    if not explicit:
        return None
    first = explicit.split()[0]
    if first.lower() == "friend":
        return None
    return first


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


def _asking_phrase(instruction: str) -> str | None:
    match = _ASKING_RE.search(" ".join(instruction.split()))
    if match is None:
        return None
    text = " ".join(match.group(1).split())
    return text or None


def subject_is_grounded(value: str | None, instruction: str) -> bool:
    """True when a titled subject is grounded in words the user wrote."""
    if occurs_in(value, instruction):
        return True
    if not isinstance(value, str):
        return False
    if _BANNED_SUBJECT.search(value):
        return False
    if value == _WELLBEING_SUBJECT and _HEADACHE_RE.search(instruction):
        return True
    last = _last_nonempty_line(instruction)
    if last:
        topic = underlying_topic(last) or last
        if _token_overlap(value, topic):
            return True
        if _kind(topic) != "general" and _kind(value) == _kind(topic):
            return True
    folded = " ".join(instruction.split()).lower()
    tokens = [token.strip(".,:;!?") for token in value.lower().split()]
    content = [token for token in tokens if token not in _SUBJECT_STOP and len(token) > 2]
    if not content:
        return False
    hits = sum(1 for token in content if token in folded)
    return hits >= min(2, len(content))


def _token_overlap(subject: str, topic: str) -> bool:
    subject_parts = {
        token.strip(".,:;!?")
        for token in subject.lower().split()
        if token not in _SUBJECT_STOP and len(token) > 2
    }
    topic_parts = {
        token.strip(".,:;!?")
        for token in topic.lower().split()
        if token not in _SUBJECT_STOP and len(token) > 2
    }
    return bool(subject_parts & topic_parts)


def _grounded(value: str, instruction: str) -> bool:
    return subject_is_grounded(value, instruction)


def _has_text(value: str | None) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strip_meta(text: str) -> str:
    cleaned = " ".join(text.split()).strip()
    cleaned = _META_LEAD_RE.sub("", cleaned).strip()
    cleaned = _META_ANY_RE.sub(" ", cleaned)
    return " ".join(cleaned.split())


def _strip_topic_leads(text: str) -> str:
    cleaned = _strip_for(" ".join(text.split()))
    while True:
        nxt = _TOPIC_LEAD_RE.sub("", cleaned).strip(" ,:-")
        nxt = " ".join(nxt.split())
        if nxt == cleaned:
            return cleaned
        cleaned = nxt


def _last_nonempty_line(instruction: str) -> str | None:
    lines = [" ".join(part.split()) for part in instruction.splitlines() if part.strip()]
    if len(lines) < 2:
        return None
    return lines[-1]


def _without_last_line(instruction: str) -> str:
    lines = [part.strip() for part in instruction.splitlines() if part.strip()]
    if len(lines) < 2:
        return instruction
    return "\n".join(lines[:-1])


def _without_friend_placeholder(
    body: str | None, fields: EmailExtraction, instruction: str
) -> str | None:
    if not _has_text(body):
        return body
    name = _addressee(fields, instruction)
    signer = _signer_name()
    text = body
    greet = _greeting(name)
    text = re.sub(r"(?i)^Hi\s+Friend\s*,", greet, text)
    if signer:
        text = re.sub(r"(?i)(Best regards,)\s*Friend\s*$", rf"\1\n{signer}", text)
    else:
        text = re.sub(r"(?i)(Best regards,)\s*Friend\s*$", r"\1", text)
    return text
