"""Contract tests for POST /chat.

These hit the ASGI app in-process. The Gemini client is replaced, so the
suite does not use the network, Gmail, or a live model. ASK vs SEND is
decided in Python after the mocked extraction returns.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from google.genai.errors import ClientError

from app.config import DEFAULT_GEMINI_MODEL, Settings
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
        "model": None,
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
            error = gemini_payload["error"]
            if error is not None:
                raise error
            return SimpleNamespace(text=gemini_payload["text"])

    class _Client:
        def __init__(self, *, api_key: str) -> None:
            # Presence only. Do not retain the key on the instance.
            if not api_key:
                raise RuntimeError("empty api key")
            gemini_payload["constructed"] = int(gemini_payload["constructed"]) + 1
            self.models = _Models()

    monkeypatch.setattr("app.extraction.gemini.genai.Client", _Client)


def test_health_returns_ok(gemini_payload: dict[str, object]) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert gemini_payload["calls"] == 0


def test_chat_full_extraction_decides_send(
    gemini_payload: dict[str, object],
) -> None:
    gemini_payload["text"] = _FULL_JSON

    response = client.post("/chat", json={"message": _CLEAR})

    assert response.status_code == 200
    body = response.json()
    assert body["phase"] == "decision_layer"
    assert body["decision"] == "SEND"
    assert body["clarification"] is None
    assert body["reply"] == "The decision is SEND. No email was sent."
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
    _assert_gmail_not_loaded()


def test_chat_bare_name_asks_for_that_person(
    gemini_payload: dict[str, object],
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
    assert gemini_payload["calls"] == 1
    _assert_gmail_not_loaded()


def test_chat_drops_an_address_the_user_did_not_write(
    gemini_payload: dict[str, object],
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


def test_chat_invalid_json_is_502_and_does_not_send(
    gemini_payload: dict[str, object],
) -> None:
    gemini_payload["text"] = "not json"

    response = client.post("/chat", json={"message": _CLEAR})

    assert response.status_code == 502
    assert response.json() == {"detail": "Gemini extraction failed."}
    assert response.json().get("decision") != "SEND"
    assert gemini_payload["calls"] == 1
    _assert_gmail_not_loaded()


def test_chat_gemini_429_is_http_429_and_does_not_send(
    gemini_payload: dict[str, object],
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

    assert response.status_code == 429
    assert response.json() == {"detail": "Gemini rate limit."}
    assert "AIza-secret" not in response.text
    assert "generativelanguage" not in response.text
    assert "RESOURCE_EXHAUSTED" not in response.text
    assert response.json().get("decision") != "SEND"
    _assert_gmail_not_loaded()


def test_chat_model_error_is_502_without_secrets(
    gemini_payload: dict[str, object],
) -> None:
    gemini_payload["error"] = RuntimeError("boom token sk-secret")

    response = client.post("/chat", json={"message": _CLEAR})

    assert response.status_code == 502
    assert "sk-secret" not in response.text
    assert "boom" not in response.text
    assert response.json().get("decision") != "SEND"
    _assert_gmail_not_loaded()


def test_chat_missing_key_is_503_and_does_not_call_gemini(
    monkeypatch: pytest.MonkeyPatch,
    gemini_payload: dict[str, object],
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
    assert gemini_payload["calls"] == 1
    _assert_gmail_not_loaded()


def test_chat_path_does_not_use_gmail_or_legacy_sdk() -> None:
    root = Path(__file__).resolve().parents[1] / "app"
    source = "\n".join(path.read_text() for path in root.rglob("*.py"))
    assert "gmail_send_test" not in source
    assert "googleapiclient" not in source
    assert "google.generativeai" not in source
    assert "vertexai" not in source
    _assert_gmail_not_loaded()


def _assert_gmail_not_loaded() -> None:
    assert "googleapiclient" not in sys.modules
    assert "googleapiclient.discovery" not in sys.modules
    loaded = [name for name in sys.modules if "gmail_send_test" in name]
    assert loaded == []
