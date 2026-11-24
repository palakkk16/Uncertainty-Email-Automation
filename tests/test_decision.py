"""Unit tests for the ASK vs SEND threshold.

These call the decision function directly. They do not mock Gemini and
they do not use the network. The threshold is slot completeness, not a
probability.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.decision import Draft, decide
from app.extraction.heuristic import local_regex_extract
from app.schemas.chat import EmailExtraction

_CLEAR = (
    "Send an email to rahul@example.com with subject Lab meeting "
    "and body Tomorrow at 10 AM"
)
_RAHUL = "Email Rahul about tomorrow"


def test_should_send_when_recipient_subject_and_body_are_resolved() -> None:
    result = decide(
        _CLEAR,
        EmailExtraction(
            recipient="rahul@example.com",
            subject="Lab meeting",
            body="Tomorrow at 10 AM",
        ),
    )

    assert result.decision == "SEND"
    assert result.clarification is None
    assert result.reply == "The decision is SEND. No email was sent."
    assert result.assessment.method == "slot_sufficiency_threshold"
    assert result.assessment.recipient == "resolved"
    assert result.assessment.subject == "resolved"
    assert result.assessment.body == "resolved"
    assert result.assessment.resolved_fraction == 1.0
    assert result.draft == Draft("rahul@example.com", "Lab meeting", "Tomorrow at 10 AM")


def test_should_draft_only_the_bare_address_when_recipient_has_extra_text() -> None:
    result = decide(
        _CLEAR,
        EmailExtraction(
            recipient="to rahul@example.com",
            subject="Lab meeting",
            body="Tomorrow at 10 AM",
        ),
    )

    assert result.decision == "SEND"
    assert result.draft is not None
    assert result.draft.recipient == "rahul@example.com"


def test_should_not_repeat_the_subject_question_after_the_user_replies() -> None:
    instruction = (
        "send mail to palakpunjabi6@gmail.com\n"
        "permission to go on vacation"
    )
    fields = local_regex_extract(instruction)
    result = decide(instruction, fields)

    assert result.decision == "SEND"
    assert result.clarification is None
    assert result.assessment.subject == "resolved"
    assert result.assessment.body == "resolved"
    assert result.draft is not None
    assert "vacation" in result.draft.subject.lower() or "permission" in result.draft.subject.lower()


def test_should_ask_about_subject_when_subject_is_missing() -> None:
    result = decide(
        "Send an email to rahul@example.com with body Tomorrow at 10 AM",
        EmailExtraction(
            recipient="rahul@example.com",
            subject=None,
            body="Tomorrow at 10 AM",
        ),
    )

    assert result.decision == "ASK"
    assert result.draft is None
    assert result.clarification == result.reply
    assert "subject" in result.clarification.lower()
    assert "rahul@example.com" not in result.clarification
    assert result.assessment.subject == "missing"
    assert result.assessment.recipient == "resolved"
    assert result.assessment.body == "resolved"
    assert result.assessment.resolved_fraction == pytest.approx(2 / 3)


def test_should_ask_about_body_when_body_is_missing() -> None:
    result = decide(
        "Send an email to rahul@example.com with subject Lab meeting",
        EmailExtraction(
            recipient="rahul@example.com",
            subject="Lab meeting",
            body=None,
        ),
    )

    assert result.decision == "ASK"
    assert result.clarification == result.reply
    assert "body" in result.clarification.lower()
    assert result.assessment.body == "missing"
    assert result.assessment.subject == "resolved"
    assert result.assessment.resolved_fraction == pytest.approx(2 / 3)


def test_should_send_when_body_was_generated_and_is_not_in_the_instruction() -> None:
    generated = (
        "Dear Hitu,\n\n"
        "I am writing to request approval for leave. "
        "Please let me know if any further details are required.\n\n"
        "Best regards,"
    )
    result = decide(
        "send mail to hitu@example.com for leave approval",
        EmailExtraction(
            recipient="hitu@example.com",
            subject="leave approval",
            body=generated,
        ),
    )

    assert result.decision == "SEND"
    assert result.clarification is None
    assert result.assessment.body == "resolved"
    assert result.assessment.subject == "resolved"
    assert result.assessment.resolved_fraction == 1.0
    assert result.draft == Draft(
        "hitu@example.com",
        "leave approval",
        generated,
    )


def test_should_ask_for_an_address_when_only_a_name_is_given() -> None:
    instruction = "send mail to palak"
    fields = local_regex_extract(instruction)
    result = decide(instruction, fields)

    assert fields.recipient is None
    assert fields.recipient_mention == "palak"
    assert result.decision == "ASK"
    assert result.clarification == (
        "Who should I send this email to? Please provide their email address."
    )


def test_should_ask_for_rahul_address_when_instruction_names_him_without_email() -> None:
    result = decide(
        _RAHUL,
        EmailExtraction(recipient_mention="Rahul"),
    )

    assert result.decision == "ASK"
    assert result.assessment.recipient == "bare_name"
    assert result.clarification == (
        "Who should I send this email to? Please provide their email address."
    )
    assert "@" not in result.clarification
    assert "example.com" not in result.clarification
    assert result.assessment.resolved_fraction == 0.0


def test_should_ask_for_rahul_when_mention_was_not_copied() -> None:
    """A name after the email verb is enough. The model does not decide."""
    result = decide(_RAHUL, EmailExtraction())

    assert result.decision == "ASK"
    assert result.assessment.recipient == "bare_name"
    assert result.clarification == (
        "Who should I send this email to? Please provide their email address."
    )
    assert "@" not in result.clarification


def test_should_ignore_a_mention_that_is_not_in_the_instruction() -> None:
    result = decide(_RAHUL, EmailExtraction(recipient_mention="Priya"))

    assert result.assessment.recipient == "bare_name"
    assert result.clarification == (
        "Who should I send this email to? Please provide their email address."
    )
    assert "Priya" not in result.clarification
    assert "@" not in result.clarification


def test_should_ask_which_address_when_two_emails_are_present() -> None:
    instruction = (
        "Email rahul@example.com or priya@example.com with subject "
        "Lab meeting and body Tomorrow at 10 AM"
    )
    result = decide(
        instruction,
        EmailExtraction(
            recipient="rahul@example.com",
            subject="Lab meeting",
            body="Tomorrow at 10 AM",
        ),
    )

    assert result.decision == "ASK"
    assert result.assessment.recipient == "ambiguous"
    assert result.assessment.subject == "resolved"
    assert result.assessment.body == "resolved"
    assert result.clarification is not None
    assert "rahul@example.com" in result.clarification
    assert "priya@example.com" in result.clarification
    assert result.assessment.resolved_fraction == pytest.approx(2 / 3)


def test_should_treat_subject_outside_the_instruction_as_missing() -> None:
    result = decide(
        _CLEAR,
        EmailExtraction(
            recipient="rahul@example.com",
            subject="Not stated",
            body="Tomorrow at 10 AM",
        ),
    )

    assert result.decision == "ASK"
    assert result.assessment.subject == "missing"
    assert result.clarification is not None
    assert "subject" in result.clarification.lower()


def test_should_ask_about_recipient_before_a_missing_subject() -> None:
    result = decide(
        "Tell the lab the draft is ready",
        EmailExtraction(subject=None, body="the draft is ready"),
    )

    assert result.decision == "ASK"
    assert result.assessment.recipient == "missing"
    assert result.assessment.body == "resolved"
    assert result.clarification == (
        "Who should I send this email to? Please provide their email address."
    )
    assert "subject" not in result.clarification.lower()
    assert result.assessment.resolved_fraction == pytest.approx(1 / 3)


def test_send_decision_does_not_import_or_call_gmail() -> None:
    root = Path(__file__).resolve().parents[1] / "app" / "decision"
    source = "\n".join(path.read_text() for path in root.rglob("*.py"))
    assert "gmail" not in source.lower()
    assert "googleapiclient" not in source

    result = decide(
        _CLEAR,
        EmailExtraction(
            recipient="rahul@example.com",
            subject="Lab meeting",
            body="Tomorrow at 10 AM",
        ),
    )

    assert result.decision == "SEND"
    assert "googleapiclient" not in sys.modules
    assert "googleapiclient.discovery" not in sys.modules
    loaded = [name for name in sys.modules if "gmail_send_test" in name]
    assert loaded == []
