"""Unit tests for Gemini extraction. The SDK client is replaced; no network."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from google.genai.errors import ClientError, ServerError

from app.config import (
    DEFAULT_GEMINI_MODEL,
    GEMINI_HTTP_RETRY_ATTEMPTS,
    GEMINI_HTTP_TIMEOUT_MS,
    Settings,
)
from app.extraction.gemini import (
    extract_email_fields,
    local_regex_extract,
    parse_extraction,
    pick_flash_model,
)
from app.decision import decide
from app.extraction.heuristic import apply_followup_slots, compose_missing_body
from app.schemas.chat import EmailExtraction

_CLEAR = (
    "Send an email to rahul@example.com with subject Lab meeting "
    "and body Tomorrow at 10 AM"
)
_RAHUL = "Email Rahul about tomorrow"


def _settings(model: str = DEFAULT_GEMINI_MODEL) -> Settings:
    return Settings(
        host="127.0.0.1",
        port=8741,
        gemini_api_key="test-not-a-real-key",
        gemini_model=model,
    )


def _client_error(code: int, message: str, status: str = "NOT_FOUND") -> ClientError:
    return ClientError(
        code,
        {"error": {"message": message, "status": status}},
    )


@pytest.fixture
def gemini(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    state: dict[str, object] = {
        "text": json.dumps(
            {
                "recipient": "rahul@example.com",
                "subject": "Lab meeting",
                "body": "Tomorrow at 10 AM",
                "recipient_mention": None,
            }
        ),
        "calls": [],
        "listed": [
            "models/gemini-2.5-flash",
            "models/gemini-flash-latest",
            "models/gemini-2.5-flash-lite",
            "models/gemini-2.0-flash",
        ],
        "http_options": None,
        "errors": {},
        "fail_times": {},
        "fail_code": 503,
        "server_error": False,
        "list_calls": 0,
        "config": None,
        "sleeps": [],
    }

    class _Models:
        def generate_content(self, *, model: str, contents: str, config: object):
            state["calls"].append(model)
            state["config"] = config
            remaining = state["fail_times"]
            assert isinstance(remaining, dict)
            if remaining.get(model, 0) > 0:
                remaining[model] = int(remaining[model]) - 1
                payload = {"error": {"message": "high demand", "status": "UNAVAILABLE"}}
                if state.get("server_error"):
                    raise ServerError(int(state["fail_code"]), payload)
                raise _client_error(
                    int(state["fail_code"]), "high demand", status="UNAVAILABLE"
                )
            errors = state["errors"]
            assert isinstance(errors, dict)
            if model in errors:
                raise errors.pop(model)
            return SimpleNamespace(text=state["text"])

        def list(self, *, config: object = None):
            state["list_calls"] = int(state["list_calls"]) + 1
            listed = state["listed"]
            assert isinstance(listed, list)
            return [
                SimpleNamespace(name=name, supported_actions=["generateContent"])
                for name in listed
            ]

    class _Client:
        def __init__(self, *, api_key: str, http_options: object = None) -> None:
            if not api_key:
                raise RuntimeError("empty api key")
            state["http_options"] = http_options
            self.models = _Models()

    monkeypatch.setattr("app.extraction.gemini.genai.Client", _Client)
    monkeypatch.setattr("app.extraction.gemini.load_settings", _settings)
    return state


def test_should_return_email_extraction_with_copied_fields(gemini: dict[str, object]) -> None:
    result = extract_email_fields(_CLEAR)

    assert isinstance(result, EmailExtraction)
    assert result.recipient == "rahul@example.com"
    assert result.subject == "Lab Meeting"
    assert result.recipient_mention is None
    _assert_full_email(result.body, name="Rahul", needle="meeting")
    assert gemini["calls"] == [DEFAULT_GEMINI_MODEL]
    assert gemini["list_calls"] == 0
    options = gemini["http_options"]
    assert options is not None
    assert options.timeout == GEMINI_HTTP_TIMEOUT_MS
    assert options.retry_options.attempts == GEMINI_HTTP_RETRY_ATTEMPTS
    config = gemini["config"]
    assert config.automatic_function_calling.disable is True
    assert config.response_mime_type == "application/json"


def test_should_keep_a_copied_name_as_recipient_mention(gemini: dict[str, object]) -> None:
    gemini["text"] = json.dumps(
        {
            "recipient": None,
            "subject": None,
            "body": "tomorrow",
            "recipient_mention": "Rahul",
        }
    )

    result = extract_email_fields(_RAHUL)

    assert result.recipient is None
    assert result.recipient_mention == "Rahul"
    _assert_full_email(result.body, name="Rahul", needle="tomorrow")


def test_should_fall_back_to_gemini_2_0_flash_when_flash_latest_is_gone(
    gemini: dict[str, object],
) -> None:
    gemini["errors"] = {
        "gemini-flash-latest": _client_error(
            404,
            "This model models/gemini-flash-latest is no longer available to new users.",
        )
    }

    result = extract_email_fields(_CLEAR)

    assert result.recipient == "rahul@example.com"
    assert gemini["calls"] == ["gemini-flash-latest", "gemini-2.0-flash"]
    assert gemini["list_calls"] == 0
    assert len(gemini["calls"]) <= 2


def test_should_try_the_next_model_on_a_gemini_timeout_without_retrying(
    gemini: dict[str, object],
) -> None:
    gemini["errors"] = {DEFAULT_GEMINI_MODEL: TimeoutError()}

    result = extract_email_fields(_CLEAR)

    assert result.recipient == "rahul@example.com"
    assert gemini["calls"] == [DEFAULT_GEMINI_MODEL, "gemini-2.0-flash"]
    assert gemini["list_calls"] == 0


def test_should_move_on_after_one_503_without_retrying_the_same_model(
    gemini: dict[str, object],
) -> None:
    gemini["fail_times"] = {DEFAULT_GEMINI_MODEL: 1}

    result = extract_email_fields(_CLEAR)

    assert result.recipient == "rahul@example.com"
    assert gemini["calls"] == [DEFAULT_GEMINI_MODEL, "gemini-2.0-flash"]
    assert gemini["list_calls"] == 0


def test_should_try_the_next_model_when_gemini_returns_429(
    gemini: dict[str, object],
) -> None:
    gemini["errors"] = {
        DEFAULT_GEMINI_MODEL: _client_error(
            429, "quota", status="RESOURCE_EXHAUSTED"
        )
    }

    result = extract_email_fields(_CLEAR)

    assert result.recipient == "rahul@example.com"
    assert gemini["calls"] == [DEFAULT_GEMINI_MODEL, "gemini-2.0-flash"]
    assert gemini["list_calls"] == 0


def test_should_use_local_regex_when_every_model_returns_429(
    gemini: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gemini["errors"] = {
        name: _client_error(429, "quota", status="RESOURCE_EXHAUSTED")
        for name in ("gemini-flash-latest", "gemini-2.0-flash")
    }

    with caplog.at_level("WARNING"):
        result = extract_email_fields(_CLEAR)

    assert isinstance(result, EmailExtraction)
    assert result.recipient == "rahul@example.com"
    assert "rate limited (429)" in caplog.text
    assert gemini["calls"] == ["gemini-flash-latest", "gemini-2.0-flash"]
    assert gemini["list_calls"] == 0


def test_should_use_local_regex_when_every_model_returns_503(
    gemini: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gemini["fail_times"] = {
        "gemini-flash-latest": 1,
        "gemini-2.0-flash": 1,
    }

    with caplog.at_level("WARNING"):
        result = extract_email_fields(_CLEAR)

    assert isinstance(result, EmailExtraction)
    assert result.recipient == "rahul@example.com"
    assert result.subject == "Lab Meeting"
    _assert_full_email(result.body, name="Rahul", needle="meeting")
    assert "falling back to local heuristic extraction" in caplog.text
    assert gemini["calls"] == ["gemini-flash-latest", "gemini-2.0-flash"]
    assert "gemini-2.5-flash-lite" not in gemini["calls"]
    assert "preview" not in " ".join(gemini["calls"])
    assert "ClientError" in caplog.text
    assert f"model={DEFAULT_GEMINI_MODEL} code=503" in caplog.text


def test_should_use_local_regex_when_both_stable_models_return_404(
    gemini: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gemini["errors"] = {
        "gemini-flash-latest": _client_error(404, "gone"),
        "gemini-2.0-flash": _client_error(404, "gone"),
        "gemini-2.5-flash-lite": _client_error(404, "gone"),
        "gemini-3-flash-preview": _client_error(404, "gone"),
    }
    gemini["listed"] = [
        "models/gemini-flash-lite-latest",
        "models/gemini-3-flash-preview",
        "models/gemini-3.1-flash-lite",
        "models/gemini-3.5-flash",
        "models/gemini-2.5-flash-lite",
    ]

    with caplog.at_level("WARNING"):
        result = extract_email_fields(_CLEAR)

    assert isinstance(result, EmailExtraction)
    assert result.recipient == "rahul@example.com"
    assert "falling back to local heuristic extraction" in caplog.text
    assert gemini["calls"] == ["gemini-flash-latest", "gemini-2.0-flash"]
    assert gemini["list_calls"] == 0


def test_should_extract_outfit_leave_and_project_topics_without_gemini() -> None:
    outfit = local_regex_extract(
        "send mail to palak asking what she will be wearing"
    )
    assert outfit.recipient is None
    assert outfit.recipient_mention == "palak"
    assert outfit.subject is not None
    assert "wear" in outfit.subject.lower()
    _assert_full_email(outfit.body, name="Palak", needle="wearing")

    leave = local_regex_extract(
        "send mail to hitu@example.com regarding leave tomorrow"
    )
    assert leave.recipient == "hitu@example.com"
    assert leave.subject == "Leave Request for Tomorrow"
    _assert_full_email(leave.body, name="Hitu", needle="leave")
    assert "tomorrow" in (leave.body or "").lower()

    project = local_regex_extract(
        "email priya@example.com about project submission"
    )
    assert project.recipient == "priya@example.com"
    assert project.subject is not None
    assert "project" in project.subject.lower()
    _assert_full_email(project.body, name="Priya", needle="submission")


def test_should_greet_with_a_first_name_not_the_raw_email_local_part() -> None:
    named = local_regex_extract(
        "send mail to palak for leave approval\n"
        "palakpunjabi6@gmail.com"
    )
    assert named.recipient == "palakpunjabi6@gmail.com"
    assert named.recipient_mention == "palak"
    assert named.body is not None
    assert "Hi Palak," in named.body
    assert "Palakpunjabi" not in named.body

    varsha = local_regex_extract(
        "send mail to varshapunjabi1995@gmail.com regarding leave tomorrow"
    )
    assert varsha.body is not None
    assert "Hi Varsha," in varsha.body
    assert "Varshapunjabi" not in varsha.body

    hiteshi = local_regex_extract(
        "send mail to hiteshipunjabi03@gmail.com about project submission"
    )
    assert hiteshi.body is not None
    assert "Hi Hiteshi," in hiteshi.body

    dotted = local_regex_extract(
        "send mail to jane.doe@example.com for leave approval"
    )
    assert dotted.body is not None
    assert "Hi Jane," in dotted.body

    long_local = local_regex_extract(
        "send mail to abcdefghijklmnop@gmail.com for leave approval"
    )
    assert long_local.body is not None
    assert "Hi there," in long_local.body
    assert "Hi Abcdefghijklmnop," not in long_local.body


def test_should_bind_followup_address_without_reasking_the_topic() -> None:
    instruction = (
        "send mail to palak asking what she will be wearing\n"
        "palak@example.com"
    )
    result = local_regex_extract(instruction)
    merged = apply_followup_slots(
        instruction,
        EmailExtraction(
            recipient_mention="palak",
            subject="What She Will Be Wearing",
        ),
    )

    assert result.recipient == "palak@example.com"
    assert merged.recipient == "palak@example.com"
    assert result.subject is not None
    assert "wear" in result.subject.lower()
    _assert_full_email(result.body, name="Palak", needle="wearing")


def test_local_regex_extract_copies_address_name_and_quoted_fields() -> None:
    instruction = (
        "Email Rahul about tomorrow with subject 'Lab meeting' "
        "and body \"Tomorrow at 10 AM\""
    )
    result = local_regex_extract(instruction)

    assert result.recipient is None
    assert result.recipient_mention == "Rahul"
    assert result.subject == "Lab Meeting"
    _assert_full_email(result.body, name="Rahul", needle="meeting")

    addressed = local_regex_extract(
        "Send an email to palak@example.com with subject 'Hi'"
    )
    assert addressed.recipient == "palak@example.com"
    assert addressed.recipient_mention is None
    assert addressed.subject == "Hi"
    _assert_full_email(addressed.body, name="Palak", needle="Hi")


def test_local_regex_extract_uses_for_phrase_and_followup_line_as_subject() -> None:
    first = local_regex_extract("Send mail to palak for leave approval")
    assert first.recipient is None
    assert first.recipient_mention == "palak"
    assert first.subject == "Request for Leave Approval"
    _assert_full_email(first.body, name="Palak", needle="leave")

    stitched = (
        "Send mail to palak for leave approval\n"
        "palakpunjabi10d7583@gmail.com\n"
        "leave approval"
    )
    filled = local_regex_extract(stitched)
    assert filled.recipient == "palakpunjabi10d7583@gmail.com"
    assert filled.subject == "Request for Leave Approval"
    assert filled.body is not None
    assert filled.body.strip().lower() != "leave approval"
    _assert_full_email(filled.body, name="Palak", needle="leave")

    merged = apply_followup_slots(
        stitched,
        EmailExtraction(recipient="palakpunjabi10d7583@gmail.com"),
    )
    assert merged.subject == "Request for Leave Approval"


def test_should_strip_meta_subject_instructions_into_a_clean_title() -> None:
    headache = local_regex_extract(
        "send mail to hitu@example.com\n"
        "frame it according to you for asking about their headache"
    )
    assert headache.subject == "Checking In — Hope You Feel Better"
    assert "frame it" not in (headache.subject or "").lower()
    assert "according to you" not in (headache.subject or "").lower()
    assert "asking about" not in (headache.subject or "").lower()
    _assert_full_email(headache.body, name="Hitu", needle="feel better")
    assert "Friend" not in (headache.body or "")

    leave = local_regex_extract(
        "send mail to hitu@example.com\n"
        "decide yourself about leave tomorrow"
    )
    assert leave.subject == "Leave Request for Tomorrow"
    _assert_full_email(leave.body, name="Hitu", needle="leave")

    project = local_regex_extract(
        "send mail to hitu@example.com\n"
        "suggest a subject for project submission"
    )
    assert project.subject == "Regarding Project Submission"
    _assert_full_email(project.body, name="Hitu", needle="submission")

    reuse = local_regex_extract(
        "send mail to hitu@example.com for leave approval\n"
        "frame it according to you"
    )
    assert reuse.subject == "Request for Leave Approval"
    assert "frame" not in (reuse.subject or "").lower()
    _assert_full_email(reuse.body, name="Hitu", needle="leave")

    written = local_regex_extract(
        "send mail to hitu@example.com\n"
        "write it yourself for project submission"
    )
    assert written.subject == "Regarding Project Submission"


def test_should_omit_friend_from_the_signoff_when_signer_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_SIGNER_NAME", raising=False)
    result = local_regex_extract(
        "send mail to hitu@example.com for leave approval"
    )
    assert result.body is not None
    assert "Friend" not in result.body
    assert "Best regards," in result.body


def test_should_greet_with_a_first_name_not_a_raw_email_local_part() -> None:
    prior_name = local_regex_extract(
        "send mail to palak for leave approval\n"
        "palakpunjabi6@gmail.com"
    )
    assert "Hi Palak," in (prior_name.body or "")
    assert "Palakpunjabi" not in (prior_name.body or "")
    assert prior_name.recipient_mention == "palak"

    varsha = local_regex_extract(
        "send mail to varshapunjabi1995@gmail.com regarding leave tomorrow"
    )
    assert "Hi Varsha," in (varsha.body or "")
    assert "Varshapunjabi" not in (varsha.body or "")

    hiteshi = local_regex_extract(
        "send mail to hiteshipunjabi03@gmail.com about project submission"
    )
    assert "Hi Hiteshi," in (hiteshi.body or "")

    dotted = local_regex_extract(
        "send mail to jane.doe@example.com for leave approval"
    )
    assert "Hi Jane," in (dotted.body or "")

    camel = local_regex_extract(
        "send mail to PalakPunjabi@example.com for leave approval"
    )
    assert "Hi Palak," in (camel.body or "")

    unknown = local_regex_extract(
        "send mail to abcdefghijklmnop@example.com for leave approval"
    )
    assert "Hi there," in (unknown.body or "")
    assert "Hi Abcdefghijklmnop," not in (unknown.body or "")


def test_should_fill_subject_and_body_from_a_topic_reply_without_reasking() -> None:
    instruction = (
        "send mail to palakpunjabi6@gmail.com\n"
        "permission to go on vacation"
    )
    fields = local_regex_extract(instruction)
    result = decide(instruction, fields)

    assert fields.subject is not None
    assert "vacation" in fields.subject.lower() or "permission" in fields.subject.lower()
    assert "frame" not in fields.subject.lower()
    assert fields.body is not None
    assert fields.body.strip() != "permission to go on vacation"
    assert "vacation" in fields.body.lower() or "leave" in fields.body.lower()
    assert result.decision == "SEND"
    assert result.clarification is None
    assert result.draft is not None
    assert result.draft.subject == fields.subject


def test_should_bind_a_plain_followup_reply_to_the_open_subject_slot() -> None:
    instruction = "Send an email to palak@example.com for leave\nyour outfit"

    filled = local_regex_extract(instruction)
    merged = apply_followup_slots(
        instruction,
        EmailExtraction(recipient="palak@example.com", subject="Request for Leave Approval"),
    )

    assert filled.recipient == "palak@example.com"
    assert filled.subject == "Your Outfit"
    assert merged.subject == "Your Outfit"
    _assert_full_email(filled.body, name="Palak", needle="outfit")


def test_should_compose_a_professional_body_when_intent_is_clear() -> None:
    result = local_regex_extract("send mail to hitu@example.com for leave approval")

    assert result.recipient == "hitu@example.com"
    assert result.subject == "Request for Leave Approval"
    _assert_full_email(result.body, name="Hitu", needle="leave")


def test_should_keep_dates_and_times_in_heuristic_subject_and_body() -> None:
    leave = local_regex_extract(
        "send mail to palakpunjabi6@gmail.com regarding leave approval "
        "from 5 dec to 8 dec"
    )
    assert leave.subject is not None
    assert leave.subject != "Request for Leave Approval"
    assert "5" in leave.subject and "8" in leave.subject
    assert "dec" in leave.subject.lower()
    _assert_full_email(leave.body, name="Palak", needle="leave")
    folded = (leave.body or "").lower()
    assert "from 5 dec to 8 dec" in folded
    assert folded != (
        "i am writing to request approval for leave. please let me know if "
        "any additional details are needed."
    )

    meeting = local_regex_extract(
        "send mail to hitu@example.com for meeting tomorrow at 3 pm"
    )
    assert meeting.subject is not None
    assert "tomorrow" in meeting.subject.lower()
    assert "3" in meeting.subject
    _assert_full_email(meeting.body, name="Hitu", needle="meeting")
    assert "tomorrow" in (meeting.body or "").lower()
    assert "3 PM" in (meeting.body or "") or "3 pm" in (meeting.body or "").lower()

    monday = local_regex_extract(
        "send mail to hitu@example.com regarding leave on Monday"
    )
    assert "monday" in (monday.subject or "").lower()
    _assert_full_email(monday.body, name="Hitu", needle="leave")
    assert "monday" in (monday.body or "").lower()


def test_should_draft_sick_leave_invitation_and_meeting_templates() -> None:
    sick = local_regex_extract("send mail to hitu@example.com for sick leave approval")
    assert sick.subject == "Request for Sick Leave Approval"
    _assert_full_email(sick.body, name="Hitu", needle="sick leave")
    assert sick.body is not None
    assert sick.body.strip().lower() != "for sick leave approval"

    invite = local_regex_extract("email hitu@example.com wedding invitation")
    assert invite.subject == "Wedding Invitation"
    _assert_full_email(invite.body, name="Hitu", needle="wedding")

    meeting = local_regex_extract(
        "send mail to hitu@example.com for meeting tomorrow at 4pm"
    )
    assert meeting.subject == "Meeting Tomorrow at 4 PM"
    _assert_full_email(meeting.body, name="Hitu", needle="meeting")
    assert meeting.body is not None
    assert "4 PM" in meeting.body or "4pm" in meeting.body.lower()


def test_should_expand_a_short_stated_body_into_a_full_email() -> None:
    result = local_regex_extract(
        "Email hitu@example.com with subject 'Leave' and body \"Out tomorrow\""
    )

    assert result.subject == "Request for Leave Approval"
    _assert_full_email(result.body, name="Hitu", needle="leave")
    assert result.body is not None
    assert result.body.strip() != "Out tomorrow"


def test_compose_missing_body_keeps_a_complete_email() -> None:
    complete = (
        "Hi Hitu,\n\n"
        "I am writing to request approval for leave. Please let me know if "
        "any additional details are needed.\n\n"
        "Best regards,\n"
        "Palak"
    )
    fields = EmailExtraction(
        recipient="hitu@example.com",
        subject="leave approval",
        body=complete,
    )

    filled = compose_missing_body(
        "send mail to hitu@example.com for leave approval",
        fields,
    )

    assert filled.subject == "Request for Leave Approval"
    assert filled.body == complete


def test_should_compose_body_after_copy_only_gemini_when_intent_is_present(
    gemini: dict[str, object],
) -> None:
    instruction = "send mail to hitu@example.com for leave approval"
    gemini["text"] = json.dumps(
        {
            "recipient": "hitu@example.com",
            "subject": None,
            "body": None,
            "recipient_mention": None,
        }
    )

    result = extract_email_fields(instruction)

    assert result.recipient == "hitu@example.com"
    assert result.subject == "Request for Leave Approval"
    _assert_full_email(result.body, name="Hitu", needle="leave")


def test_should_use_local_regex_when_listed_flash_latest_returns_server_error_503(
    gemini: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gemini["server_error"] = True
    gemini["fail_times"] = {
        "gemini-flash-latest": 1,
        "gemini-2.0-flash": 1,
    }

    with caplog.at_level("WARNING"):
        result = extract_email_fields(_CLEAR)

    assert isinstance(result, EmailExtraction)
    assert result.recipient == "rahul@example.com"
    assert "falling back to local heuristic extraction" in caplog.text
    assert "model=gemini-flash-latest code=503" in caplog.text
    assert "ServerError" in caplog.text
    assert gemini["calls"] == ["gemini-flash-latest", "gemini-2.0-flash"]


def test_should_skip_known_404_models_on_the_next_request(
    gemini: dict[str, object],
) -> None:
    gemini["errors"] = {
        "gemini-flash-latest": _client_error(404, "gone"),
    }

    first = extract_email_fields(_CLEAR)

    assert first.recipient == "rahul@example.com"
    assert gemini["calls"] == ["gemini-flash-latest", "gemini-2.0-flash"]
    gemini["calls"] = []
    gemini["list_calls"] = 0
    gemini["errors"] = {
        "gemini-flash-latest": _client_error(404, "should not be called"),
    }

    second = extract_email_fields(_CLEAR)

    assert second.recipient == "rahul@example.com"
    assert gemini["calls"][0] == "gemini-2.0-flash"
    assert "gemini-flash-latest" not in gemini["calls"]
    assert gemini["list_calls"] == 0


def test_should_use_local_regex_when_every_model_returns_404(
    gemini: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gemini["errors"] = {
        DEFAULT_GEMINI_MODEL: _client_error(
            404, "https://generativelanguage.googleapis.com?key=AIza-secret"
        ),
        "gemini-2.0-flash": _client_error(404, "gone"),
    }

    with caplog.at_level("WARNING"):
        result = extract_email_fields(_CLEAR)

    assert isinstance(result, EmailExtraction)
    assert result.recipient == "rahul@example.com"
    assert "AIza-secret" not in caplog.text
    assert f"model={DEFAULT_GEMINI_MODEL} code=404" in caplog.text
    assert "falling back to local heuristic extraction" in caplog.text
    assert len(gemini["calls"]) <= 2


def test_should_stop_after_the_llm_budget_and_use_local_regex(
    gemini: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = {"now": 0.0}

    def monotonic() -> float:
        return clock["now"]

    monkeypatch.setattr("app.extraction.gemini.time.monotonic", monotonic)
    gemini["errors"] = {
        "gemini-flash-latest": _client_error(503, "busy", status="UNAVAILABLE")
    }

    def bump(*_args: object, **_kwargs: object):
        clock["now"] = 6.1
        raise _client_error(503, "busy", status="UNAVAILABLE")

    class _Models:
        def generate_content(self, *, model: str, contents: str, config: object):
            gemini["calls"].append(model)
            return bump()

        def list(self, *, config: object = None):
            return []

    class _Client:
        def __init__(self, *, api_key: str, http_options: object = None) -> None:
            gemini["http_options"] = http_options
            self.models = _Models()

    monkeypatch.setattr("app.extraction.gemini.genai.Client", _Client)
    clock["now"] = 0.0

    result = extract_email_fields(_CLEAR)

    assert result.recipient == "rahul@example.com"
    assert gemini["calls"] == ["gemini-flash-latest"]
    assert "gemini-2.0-flash" not in gemini["calls"]


def test_parse_extraction_drops_text_the_instruction_does_not_contain() -> None:
    raw = json.dumps(
        {
            "recipient": "rahul@example.com",
            "subject": "Invented",
            "body": "See you then",
            "recipient_mention": "Priya",
        }
    )

    parsed = parse_extraction(raw, _RAHUL)

    assert parsed.recipient is None
    assert parsed.subject == "Invented"
    assert parsed.body == "See you then"
    assert parsed.recipient_mention is None


def _assert_full_email(body: str | None, *, name: str, needle: str) -> None:
    assert body is not None
    folded = body.strip().lower()
    assert folded != needle.lower()
    assert f"Hi {name}," in body
    assert needle.lower() in folded
    assert "Best regards" in body
    assert "Palak" in body


def test_pick_flash_model_prefers_gemini_2_5_flash() -> None:
    listed = [
        SimpleNamespace(name="models/gemini-2.0-flash", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-2.5-flash-lite", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-2.5-flash", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-3-pro", supported_actions=["generateContent"]),
    ]

    assert pick_flash_model(listed, failed="gemini-1.5-flash") == "gemini-2.5-flash"


def test_pick_flash_model_prefers_lite_when_standard_flash_is_busy() -> None:
    listed = [
        SimpleNamespace(name="models/gemini-flash-latest", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-2.5-flash", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-2.5-flash-lite", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-2.0-flash", supported_actions=["generateContent"]),
    ]

    assert (
        pick_flash_model(listed, failed="gemini-2.5-flash", prefer_lite=True)
        == "gemini-2.0-flash"
    )
