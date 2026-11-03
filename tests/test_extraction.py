"""Unit tests for Gemini extraction. The SDK client is replaced; no network."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from google.genai.errors import ClientError

from app.config import DEFAULT_GEMINI_MODEL, Settings
from app.extraction.gemini import (
    ExtractionError,
    extract_email_fields,
    local_regex_extract,
    parse_extraction,
    pick_flash_model,
)
from app.extraction.heuristic import apply_followup_slots
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
            "models/gemini-3.8-flash",
            "models/gemini-flash-latest",
            "models/gemini-2.5-flash-lite",
            "models/gemini-2.5-flash",
        ],
        "errors": {},
        "fail_times": {},
        "fail_code": 503,
        "list_calls": 0,
        "config": None,
        "sleeps": [],
    }

    monkeypatch.setattr("app.extraction.gemini._sleep", lambda seconds: state["sleeps"].append(seconds))

    class _Models:
        def generate_content(self, *, model: str, contents: str, config: object):
            state["calls"].append(model)
            state["config"] = config
            remaining = state["fail_times"]
            assert isinstance(remaining, dict)
            if remaining.get(model, 0) > 0:
                remaining[model] = int(remaining[model]) - 1
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
        def __init__(self, *, api_key: str) -> None:
            if not api_key:
                raise RuntimeError("empty api key")
            self.models = _Models()

    monkeypatch.setattr("app.extraction.gemini.genai.Client", _Client)
    monkeypatch.setattr("app.extraction.gemini.load_settings", _settings)
    return state


def test_should_return_email_extraction_with_copied_fields(gemini: dict[str, object]) -> None:
    result = extract_email_fields(_CLEAR)

    assert isinstance(result, EmailExtraction)
    assert result.recipient == "rahul@example.com"
    assert result.subject == "Lab meeting"
    assert result.body == "Tomorrow at 10 AM"
    assert result.recipient_mention is None
    assert gemini["calls"] == [DEFAULT_GEMINI_MODEL]
    assert gemini["list_calls"] == 0
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
    assert result.body == "tomorrow"


def test_should_fall_back_to_a_listed_flash_model_when_the_configured_id_is_gone(
    gemini: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gemini["errors"] = {
        "gemini-2.5-flash": _client_error(
            404,
            "This model models/gemini-2.5-flash is no longer available to new users.",
        )
    }
    monkeypatch.setattr(
        "app.extraction.gemini.load_settings",
        lambda: _settings("gemini-2.5-flash"),
    )

    result = extract_email_fields(_CLEAR)

    assert result.recipient == "rahul@example.com"
    assert gemini["calls"] == ["gemini-2.5-flash", "gemini-3.8-flash"]
    assert gemini["list_calls"] == 1


def test_should_retry_a_503_on_the_same_model_then_succeed(
    gemini: dict[str, object],
) -> None:
    gemini["fail_times"] = {DEFAULT_GEMINI_MODEL: 1}

    result = extract_email_fields(_CLEAR)

    assert result.recipient == "rahul@example.com"
    assert gemini["calls"] == [DEFAULT_GEMINI_MODEL, DEFAULT_GEMINI_MODEL]
    assert gemini["sleeps"] == [0.5]
    assert gemini["list_calls"] == 0


def test_should_fall_back_to_a_lite_flash_model_after_503_retries(
    gemini: dict[str, object],
) -> None:
    gemini["fail_times"] = {DEFAULT_GEMINI_MODEL: 2}

    result = extract_email_fields(_CLEAR)

    assert result.recipient == "rahul@example.com"
    assert gemini["calls"] == [
        DEFAULT_GEMINI_MODEL,
        DEFAULT_GEMINI_MODEL,
        "gemini-2.5-flash-lite",
    ]
    assert gemini["list_calls"] == 1
    assert gemini["sleeps"] == [0.5]
    assert "gemini-flash-latest" not in gemini["calls"]


def test_should_use_local_regex_when_gemini_returns_429(
    gemini: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gemini["errors"] = {
        DEFAULT_GEMINI_MODEL: _client_error(
            429, "quota", status="RESOURCE_EXHAUSTED"
        )
    }

    with caplog.at_level("WARNING"):
        result = extract_email_fields(_CLEAR)

    assert isinstance(result, EmailExtraction)
    assert result.recipient == "rahul@example.com"
    assert "rate limited (429)" in caplog.text
    assert gemini["list_calls"] == 0


def test_should_use_local_regex_when_every_model_returns_503(
    gemini: dict[str, object],
    caplog: pytest.LogCaptureFixture,
) -> None:
    gemini["fail_times"] = {
        DEFAULT_GEMINI_MODEL: 2,
        "gemini-2.5-flash-lite": 2,
    }

    with caplog.at_level("WARNING"):
        result = extract_email_fields(_CLEAR)

    assert isinstance(result, EmailExtraction)
    assert result.recipient == "rahul@example.com"
    assert result.subject is None
    assert result.body is None
    assert "falling back to local heuristic extraction" in caplog.text
    assert gemini["calls"] == [
        DEFAULT_GEMINI_MODEL,
        DEFAULT_GEMINI_MODEL,
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash-lite",
    ]


def test_local_regex_extract_copies_address_name_and_quoted_fields() -> None:
    instruction = (
        "Email Rahul about tomorrow with subject 'Lab meeting' "
        "and body \"Tomorrow at 10 AM\""
    )
    result = local_regex_extract(instruction)

    assert result.recipient is None
    assert result.recipient_mention == "Rahul"
    assert result.subject == "Lab meeting"
    assert result.body == "Tomorrow at 10 AM"

    addressed = local_regex_extract(
        "Send an email to palak@example.com with subject 'Hi'"
    )
    assert addressed.recipient == "palak@example.com"
    assert addressed.recipient_mention is None
    assert addressed.subject == "Hi"
    assert addressed.body is None


def test_local_regex_extract_uses_for_phrase_and_followup_line_as_subject() -> None:
    first = local_regex_extract("Send mail to palak for leave approval")
    assert first.recipient is None
    assert first.recipient_mention == "palak"
    assert first.subject == "leave approval"

    stitched = (
        "Send mail to palak for leave approval\n"
        "palakpunjabi10d7583@gmail.com\n"
        "leave approval"
    )
    filled = local_regex_extract(stitched)
    assert filled.recipient == "palakpunjabi10d7583@gmail.com"
    assert filled.subject == "leave approval"
    assert filled.body == "leave approval"

    merged = apply_followup_slots(
        stitched,
        EmailExtraction(recipient="palakpunjabi10d7583@gmail.com"),
    )
    assert merged.subject == "leave approval"


def test_should_not_put_provider_text_on_extraction_error(gemini: dict[str, object]) -> None:
    gemini["errors"] = {
        DEFAULT_GEMINI_MODEL: _client_error(404, "https://generativelanguage.googleapis.com?key=AIza-secret")
    }
    gemini["listed"] = []

    with pytest.raises(ExtractionError) as info:
        extract_email_fields(_CLEAR)
    assert "AIza-secret" not in str(info.value)
    assert "generativelanguage" not in str(info.value)


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
    assert parsed.subject is None
    assert parsed.body is None
    assert parsed.recipient_mention is None


def test_pick_flash_model_prefers_gemini_3_8_flash() -> None:
    listed = [
        SimpleNamespace(name="models/gemini-2.0-flash", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-3-pro", supported_actions=["generateContent"]),
    ]

    assert pick_flash_model(listed, failed="gemini-2.5-flash") == "gemini-3.8-flash"


def test_pick_flash_model_prefers_lite_when_standard_flash_is_busy() -> None:
    listed = [
        SimpleNamespace(name="models/gemini-flash-latest", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-2.5-flash-lite", supported_actions=["generateContent"]),
        SimpleNamespace(name="models/gemini-2.5-flash", supported_actions=["generateContent"]),
    ]

    assert (
        pick_flash_model(listed, failed="gemini-3.8-flash", prefer_lite=True)
        == "gemini-2.5-flash-lite"
    )
