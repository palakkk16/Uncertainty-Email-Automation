"""Contract tests for POST /chat.

These hit the ASGI app in-process. The Gemini client is replaced, so the
suite does not use the network, Gmail, or a live model. ASK vs SEND is
decided in Python after the mocked extraction returns. Dispatch goes to a
recording FakeSender through dependency_overrides, never to Gmail.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from google.genai.errors import ClientError

from app.config import DEFAULT_GEMINI_MODEL, Settings
from app.dispatch import (
    DispatchFailed,
    Dispatcher,
    DispatchUnavailable,
    DuplicateGuard,
    get_dispatcher,
)
from app.main import app

client = TestClient(app)

_CLEAR = (
    "Send an email to rahul@example.com with subject Lab meeting "
    "and body Tomorrow at 10 AM"
)
_PARTIAL = "Email Rahul about tomorrow"
_FULL_JSON = json.dumps(
    {
        "recipient": "rahul@example.com",
        "subject": "Lab meeting",
        "body": "Tomorrow at 10 AM",
    }
)


@pytest.fixture
def gemini_payload() -> dict[str, object]:
    """Mutable stand-in for one generate_content response."""
    return {
        "text": json.dumps(
            {"recipient": None, "subject": None, "body": None}
        ),
        "calls": 0,
        "constructed": 0,
        "error": None,
        "errors": {},
        "model": None,
        "list_calls": 0,
        "listed_models": [],
    }


@pytest.fixture(autouse=True)
def _patch_gemini_client(
    monkeypatch: pytest.MonkeyPatch,
    gemini_payload: dict[str, object],
) -> None:
    """Replace the SDK client so /chat never opens a socket."""

    class _Models:
        def generate_content(self, *, model: str, contents: str, config: object):
            gemini_payload["calls"] = int(gemini_payload["calls"]) + 1
            gemini_payload["model"] = model
            gemini_payload["contents"] = contents
            errors = gemini_payload["errors"]
            if isinstance(errors, dict) and model in errors:
                raise errors.pop(model)
            error = gemini_payload["error"]
            if error is not None:
                raise error
            return SimpleNamespace(text=gemini_payload["text"])

        def list(self, *, config: object = None):
            gemini_payload["list_calls"] = int(gemini_payload["list_calls"]) + 1
            names = gemini_payload["listed_models"]
            assert isinstance(names, list)
            return [
                SimpleNamespace(name=name, supported_actions=["generateContent"])
                for name in names
            ]

    class _Client:
        def __init__(self, *, api_key: str) -> None:
            # Presence only. Do not retain the key on the instance.
            if not api_key:
                raise RuntimeError("empty api key")
            gemini_payload["constructed"] = int(gemini_payload["constructed"]) + 1
            self.models = _Models()

    monkeypatch.setattr("app.extraction.gemini.genai.Client", _Client)


class FakeSender:
    """Records each send. Set `error` to make the next sends raise it."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.error: Exception | None = None

    def send(self, recipient: str, subject: str, body: str) -> str:
        self.calls.append((recipient, subject, body))
        if self.error is not None:
            raise self.error
        return f"fake-id-{len(self.calls)}"


@pytest.fixture
def mail() -> FakeSender:
    return FakeSender()


@pytest.fixture
def guard() -> DuplicateGuard:
    """Fresh per test, so one test's send is not another test's duplicate."""
    return DuplicateGuard()


@pytest.fixture(autouse=True)
def _fake_dispatch(mail: FakeSender, guard: DuplicateGuard) -> Iterator[None]:
    _use_dispatcher(Dispatcher(mail, frozenset(), guard))
    yield
    app.dependency_overrides.pop(get_dispatcher, None)


def _use_dispatcher(dispatcher: Dispatcher | None) -> None:
    app.dependency_overrides[get_dispatcher] = lambda: dispatcher


def _post_clear(gemini_payload: dict[str, object]):
    gemini_payload["text"] = _FULL_JSON
    return client.post("/chat", json={"message": _CLEAR})


def test_health_returns_ok(gemini_payload: dict[str, object]) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert gemini_payload["calls"] == 0


def test_health_config_reports_guardrails_without_secrets(
    gemini_payload: dict[str, object],
) -> None:
    response = client.get("/health/config")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "extraction_engine",
        "dispatch_enabled",
        "allow_all_recipients",
        "dispatch_mode",
        "uncertainty_policy",
    }
    assert body["extraction_engine"] == "Gemini + Local Heuristic Fallback"
    assert body["dispatch_enabled"] is False
    assert body["allow_all_recipients"] is False
    assert "preview" in body["dispatch_mode"].lower()
    assert "Ask on missing recipient" in body["uncertainty_policy"]
    dumped = str(body)
    assert "GEMINI_API_KEY" not in dumped
    assert "token.json" not in dumped
    assert "AIza" not in dumped
    assert gemini_payload["calls"] == 0


def test_should_dispatch_once_with_the_draft_when_decision_is_send(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    response = _post_clear(gemini_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["phase"] == "decision_layer"
    assert body["decision"] == "SEND"
    assert body["clarification"] is None
    assert body["reply"] == "Email sent to rahul@example.com."
    assert body["dispatch"] == {"status": "sent", "message_id": "fake-id-1"}
    assert mail.calls == [("rahul@example.com", "Lab meeting", "Tomorrow at 10 AM")]
    assert body["extraction"] == {
        "recipient": "rahul@example.com",
        "subject": "Lab meeting",
        "body": "Tomorrow at 10 AM",
        "recipient_mention": None,
    }
    assert body["assessment"]["method"] == "slot_sufficiency_threshold"
    assert body["assessment"]["resolved_fraction"] == 1.0
    assert gemini_payload["calls"] == 1
    assert gemini_payload["model"] == DEFAULT_GEMINI_MODEL
    assert "pro" not in str(gemini_payload["model"])
    assert gemini_payload["list_calls"] == 0
    _assert_gmail_not_loaded()


def test_should_fall_back_when_the_configured_model_returns_404(
    gemini_payload: dict[str, object],
    mail: FakeSender,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gemini_payload["text"] = _FULL_JSON
    gemini_payload["listed_models"] = ["models/gemini-3.8-flash"]
    gemini_payload["errors"] = {
        "gemini-2.5-flash": ClientError(
            404,
            {
                "error": {
                    "message": "This model models/gemini-2.5-flash is no longer available.",
                    "status": "NOT_FOUND",
                }
            },
        )
    }
    monkeypatch.setattr(
        "app.extraction.gemini.load_settings",
        lambda: Settings(
            host="127.0.0.1",
            port=8741,
            gemini_api_key="test-not-a-real-key",
            gemini_model="gemini-2.5-flash",
        ),
    )

    response = client.post("/chat", json={"message": _CLEAR})

    assert response.status_code == 200
    assert response.json()["decision"] == "SEND"
    assert response.json()["extraction"]["recipient"] == "rahul@example.com"
    assert gemini_payload["model"] == "gemini-3.8-flash"
    assert gemini_payload["list_calls"] == 1
    assert mail.calls == [("rahul@example.com", "Lab meeting", "Tomorrow at 10 AM")]


def test_should_not_dispatch_when_app_dispatch_enabled_is_false(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    """The real dependency, reading the APP_DISPATCH_ENABLED=false that conftest forces."""
    app.dependency_overrides.pop(get_dispatcher)

    response = _post_clear(gemini_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "SEND"
    assert body["reply"] == "The decision is SEND. No email was sent."
    assert body["dispatch"] == {"status": "disabled", "message_id": None}
    assert mail.calls == []
    _assert_gmail_not_loaded()


def test_should_not_send_again_when_the_same_send_is_posted_twice(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    first = _post_clear(gemini_payload)
    second = _post_clear(gemini_payload)

    assert first.json()["dispatch"]["status"] == "sent"
    assert second.status_code == 200
    assert second.json()["dispatch"] == {"status": "already_sent", "message_id": None}
    assert "not sent again" in second.json()["reply"]
    assert len(mail.calls) == 1


def test_should_return_send_preview_when_recipient_is_not_on_the_allowlist(
    gemini_payload: dict[str, object],
    mail: FakeSender,
    guard: DuplicateGuard,
) -> None:
    _use_dispatcher(Dispatcher(mail, frozenset({"priya@example.com"}), guard))

    response = _post_clear(gemini_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "SEND"
    assert body["dispatch"] == {"status": "rejected", "message_id": None}
    assert body["extraction"]["recipient"] == "rahul@example.com"
    assert body["extraction"]["subject"] == "Lab meeting"
    assert body["extraction"]["body"] == "Tomorrow at 10 AM"
    assert "allowlist" in body["reply"].lower()
    assert "No email was sent." in body["reply"]
    assert mail.calls == []


def test_should_send_to_any_address_when_dispatcher_allowlist_is_empty(
    gemini_payload: dict[str, object],
    mail: FakeSender,
    guard: DuplicateGuard,
) -> None:
    _use_dispatcher(Dispatcher(mail, frozenset(), guard))

    response = _post_clear(gemini_payload)

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "SEND"
    assert body["dispatch"]["status"] == "sent"
    assert mail.calls == [("rahul@example.com", "Lab meeting", "Tomorrow at 10 AM")]


def test_should_send_when_recipient_matches_the_allowlist_in_another_case(
    gemini_payload: dict[str, object],
    mail: FakeSender,
    guard: DuplicateGuard,
) -> None:
    _use_dispatcher(Dispatcher(mail, frozenset({"rahul@example.com"}), guard))
    gemini_payload["text"] = json.dumps(
        {
            "recipient": "Rahul@Example.com",
            "subject": "Lab meeting",
            "body": "Tomorrow at 10 AM",
        }
    )
    message = _CLEAR.replace("rahul@example.com", "Rahul@Example.com")

    response = client.post("/chat", json={"message": message})

    assert response.status_code == 200
    assert response.json()["dispatch"]["status"] == "sent"
    assert mail.calls == [("Rahul@Example.com", "Lab meeting", "Tomorrow at 10 AM")]


def test_should_return_503_when_the_gmail_token_is_unavailable(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    mail.error = DispatchUnavailable("token_missing")

    response = _post_clear(gemini_payload)

    assert response.status_code == 503
    assert response.json() == {"detail": "Email dispatch is unavailable."}


def test_should_return_502_without_provider_text_when_gmail_fails(
    gemini_payload: dict[str, object],
    mail: FakeSender,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mail.error = DispatchFailed("gmail_http_error")

    with caplog.at_level(logging.DEBUG):
        response = _post_clear(gemini_payload)

    assert response.status_code == 502
    assert response.json() == {"detail": "Email dispatch failed."}
    assert "gmail_http_error" in caplog.text
    assert "rahul@example.com" not in caplog.text
    assert "Tomorrow at 10 AM" not in caplog.text
    assert "Lab meeting" not in caplog.text


def test_should_allow_a_retry_when_the_previous_send_failed(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    mail.error = DispatchFailed("gmail_http_error")
    failed = _post_clear(gemini_payload)
    mail.error = None

    retried = _post_clear(gemini_payload)

    assert failed.status_code == 502
    assert retried.status_code == 200
    assert retried.json()["dispatch"] == {"status": "sent", "message_id": "fake-id-2"}
    assert len(mail.calls) == 2


def test_should_send_preview_without_asking_for_body_when_intent_is_clear(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    message = "send mail to hitu@example.com for leave approval"
    gemini_payload["text"] = json.dumps(
        {
            "recipient": "hitu@example.com",
            "subject": None,
            "body": None,
            "recipient_mention": "hitu",
        }
    )

    response = client.post("/chat", json={"message": message})

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "SEND"
    assert body["clarification"] is None
    assert body["assessment"]["body"] == "resolved"
    assert body["extraction"]["subject"] == "leave approval"
    assert body["extraction"]["body"] is not None
    assert "Dear Hitu" in body["extraction"]["body"]
    assert "leave" in body["extraction"]["body"].lower()
    assert mail.calls[0][0] == "hitu@example.com"
    assert mail.calls[0][1] == "leave approval"
    assert mail.calls[0][2] == body["extraction"]["body"]


def test_chat_followup_subject_is_resolved_and_does_not_ask_again(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    message = (
        "Send mail to palak for leave approval\n"
        "palakpunjabi10d7583@gmail.com\n"
        "leave approval"
    )
    gemini_payload["text"] = json.dumps(
        {
            "recipient": "palakpunjabi10d7583@gmail.com",
            "subject": None,
            "body": None,
            "recipient_mention": "palak",
        }
    )

    response = client.post("/chat", json={"message": message})

    assert response.status_code == 200
    body = response.json()
    assert body["extraction"]["subject"] == "leave approval"
    assert body["assessment"]["subject"] == "resolved"
    assert body["decision"] == "SEND"
    assert body["clarification"] is None
    assert mail.calls[0][0] == "palakpunjabi10d7583@gmail.com"
    assert mail.calls[0][1] == "leave approval"


def test_chat_bare_name_asks_for_that_person(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    gemini_payload["text"] = json.dumps(
        {
            "recipient": None,
            "subject": None,
            "body": "tomorrow",
            "recipient_mention": "Rahul",
        }
    )

    response = client.post("/chat", json={"message": _PARTIAL})

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "ASK"
    assert body["phase"] == "decision_layer"
    assert body["extraction"]["recipient"] is None
    assert body["extraction"]["subject"] is None
    assert body["extraction"]["body"] == "tomorrow"
    assert body["extraction"]["recipient_mention"] == "Rahul"
    assert body["assessment"]["recipient"] == "bare_name"
    assert body["clarification"] == body["reply"]
    assert "Rahul" in body["clarification"]
    assert "@" not in body["clarification"]
    assert body["dispatch"] is None
    assert mail.calls == []
    assert gemini_payload["calls"] == 1
    _assert_gmail_not_loaded()


def test_chat_drops_an_address_the_user_did_not_write(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    gemini_payload["text"] = json.dumps(
        {
            "recipient": "rahul@example.com",
            "subject": "Status",
            "body": "See you then",
        }
    )

    response = client.post("/chat", json={"message": _PARTIAL})

    assert response.status_code == 200
    body = response.json()
    assert body["phase"] == "decision_layer"
    assert body["decision"] == "ASK"
    assert body["extraction"]["recipient"] is None
    assert body["extraction"]["subject"] is None
    assert body["extraction"]["body"] is None
    assert "Rahul" in body["clarification"]
    assert "@" not in body["clarification"]
    assert mail.calls == []


def test_chat_invalid_json_is_502_and_does_not_send(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    gemini_payload["text"] = "not json"

    response = client.post("/chat", json={"message": _CLEAR})

    assert response.status_code == 502
    assert response.json() == {"detail": "Gemini extraction failed."}
    assert response.json().get("decision") != "SEND"
    assert mail.calls == []
    assert gemini_payload["calls"] == 1
    _assert_gmail_not_loaded()


def test_chat_gemini_429_falls_back_to_local_extraction_and_does_not_send(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    gemini_payload["error"] = ClientError(
        429,
        {
            "error": {
                "message": (
                    "https://generativelanguage.googleapis.com/v1beta"
                    "?key=AIza-secret"
                ),
                "status": "RESOURCE_EXHAUSTED",
            }
        },
    )

    response = client.post("/chat", json={"message": _CLEAR})

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "ASK"
    assert body["extraction"]["recipient"] == "rahul@example.com"
    assert "AIza-secret" not in response.text
    assert "generativelanguage" not in response.text
    assert "RESOURCE_EXHAUSTED" not in response.text
    assert mail.calls == []
    _assert_gmail_not_loaded()


def test_chat_model_error_is_502_without_secrets(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    gemini_payload["error"] = RuntimeError("boom token sk-secret")

    response = client.post("/chat", json={"message": _CLEAR})

    assert response.status_code == 502
    assert "sk-secret" not in response.text
    assert "boom" not in response.text
    assert response.json().get("decision") != "SEND"
    assert mail.calls == []
    _assert_gmail_not_loaded()


def test_chat_missing_key_is_503_and_does_not_call_gemini(
    monkeypatch: pytest.MonkeyPatch,
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    monkeypatch.setattr(
        "app.extraction.gemini.load_settings",
        lambda: Settings(
            host="127.0.0.1",
            port=8741,
            gemini_api_key=None,
            gemini_model=DEFAULT_GEMINI_MODEL,
        ),
    )

    response = client.post("/chat", json={"message": _PARTIAL})

    assert response.status_code == 503
    assert response.json() == {"detail": "Gemini extraction is unavailable."}
    assert gemini_payload["calls"] == 0
    assert gemini_payload["constructed"] == 0
    assert mail.calls == []


@pytest.mark.parametrize("message", ["", " ", "\n", "\t", "  \n\t  "])
def test_chat_rejects_empty_or_whitespace_message(
    message: str,
    gemini_payload: dict[str, object],
) -> None:
    response = client.post("/chat", json={"message": message})

    assert response.status_code == 422
    assert gemini_payload["calls"] == 0
    assert gemini_payload["constructed"] == 0


def test_chat_rejects_message_longer_than_4000_characters(
    gemini_payload: dict[str, object],
) -> None:
    response = client.post("/chat", json={"message": "a" * 4001})

    assert response.status_code == 422
    assert gemini_payload["calls"] == 0


def test_chat_accepts_message_at_4000_characters(
    gemini_payload: dict[str, object],
) -> None:
    response = client.post("/chat", json={"message": "b" * 4000})

    assert response.status_code == 200
    assert response.json()["decision"] == "ASK"
    assert response.json()["phase"] == "decision_layer"
    assert gemini_payload["calls"] == 1


def test_chat_rejects_missing_message(
    gemini_payload: dict[str, object],
) -> None:
    response = client.post("/chat", json={})

    assert response.status_code == 422
    assert gemini_payload["calls"] == 0


def test_chat_two_addresses_asks_instead_of_sending(
    gemini_payload: dict[str, object],
    mail: FakeSender,
) -> None:
    message = "Email rahul@example.com or priya@example.com about the draft"
    gemini_payload["text"] = json.dumps(
        {
            "recipient": "rahul@example.com",
            "subject": None,
            "body": None,
        }
    )

    response = client.post("/chat", json={"message": message})

    assert response.status_code == 200
    body = response.json()
    assert body["phase"] == "decision_layer"
    assert body["decision"] == "ASK"
    assert body["assessment"]["recipient"] == "ambiguous"
    assert "rahul@example.com" in body["clarification"]
    assert "priya@example.com" in body["clarification"]
    assert body["dispatch"] is None
    assert mail.calls == []
    assert gemini_payload["calls"] == 1
    _assert_gmail_not_loaded()


def test_chat_path_does_not_use_legacy_sdks_or_the_phase_1_script() -> None:
    root = Path(__file__).resolve().parents[1] / "app"
    source = _source(root)
    assert "gmail_send_test" not in source
    assert "google.generativeai" not in source
    assert "vertexai" not in source
    _assert_gmail_not_loaded()


@pytest.mark.parametrize("package", ["decision", "extraction", "baseline"])
def test_only_the_dispatch_package_reaches_gmail(package: str) -> None:
    source = _source(Path(__file__).resolve().parents[1] / "app" / package)
    assert "app.dispatch" not in source
    assert "googleapiclient" not in source


def _source(root: Path) -> str:
    return "\n".join(path.read_text() for path in root.rglob("*.py"))


def _assert_gmail_not_loaded() -> None:
    assert "googleapiclient" not in sys.modules
    assert "googleapiclient.discovery" not in sys.modules
    loaded = [name for name in sys.modules if "gmail_send_test" in name]
    assert loaded == []
