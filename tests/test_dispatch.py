"""Unit tests for dispatch config, the duplicate guard, and the Gmail sender.

Nothing here uses the network. Token files live in tmp_path. The Gmail
client is replaced with fake modules in sys.modules, so the real
googleapiclient is never imported and later tests can still assert that.
"""

from __future__ import annotations

import base64
import json
import stat
import sys
import types
from datetime import datetime, timedelta, timezone
from email import message_from_bytes, policy
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from app.config import ConfigError, load_dispatch_settings
from app.decision import Draft
from app.dispatch import (
    DispatchFailed,
    Dispatcher,
    DispatchRejected,
    DispatchUnavailable,
    DuplicateGuard,
)
from app.dispatch.gmail import (
    GMAIL_SEND_SCOPE,
    GmailSender,
    _deliver as real_deliver,
    build_raw_message,
    load_credentials,
)
from app.main import create_app

_DRAFT = Draft("rahul@example.com", "Lab meeting", "Tomorrow at 10 AM")
_DISPATCH_ENV = (
    "APP_HOST",
    "APP_PORT",
    "GMAIL_SENDER",
    "TOKEN_PATH",
    "APP_DISPATCH_ALLOWED_RECIPIENTS",
    "DISPATCH_ALLOWLIST",
    "ALLOWED_RECIPIENTS",
)


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Enabled dispatch with valid values, isolated from the developer's .env."""
    monkeypatch.setattr("app.config.load_dotenv", lambda *_a, **_k: None)
    for name in _DISPATCH_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_DISPATCH_ENABLED", "true")
    monkeypatch.setenv("GMAIL_SENDER", "me@example.com")
    monkeypatch.setenv("TOKEN_PATH", "credentials/token.json")
    return monkeypatch


def test_should_return_none_when_dispatch_is_disabled(env: pytest.MonkeyPatch) -> None:
    env.setenv("APP_DISPATCH_ENABLED", "FALSE")
    assert load_dispatch_settings() is None


def test_should_load_settings_when_dispatch_is_enabled(env: pytest.MonkeyPatch) -> None:
    env.setenv("APP_DISPATCH_ALLOWED_RECIPIENTS", " Rahul@Example.com, priya@example.com ")

    settings = load_dispatch_settings()

    assert settings is not None
    assert settings.sender == "me@example.com"
    assert settings.token_path == Path(__file__).resolve().parents[1] / "credentials/token.json"
    assert settings.allowed_recipients == {"rahul@example.com", "priya@example.com"}


def test_should_merge_dispatch_allowlist_aliases(env: pytest.MonkeyPatch) -> None:
    env.setenv("APP_DISPATCH_ALLOWED_RECIPIENTS", "rahul@example.com")
    env.setenv("DISPATCH_ALLOWLIST", "priya@example.com")
    env.setenv("ALLOWED_RECIPIENTS", "palakpunjabi10d7583@gmail.com")

    settings = load_dispatch_settings()

    assert settings is not None
    assert settings.allowed_recipients == {
        "rahul@example.com",
        "priya@example.com",
        "palakpunjabi10d7583@gmail.com",
    }


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("APP_DISPATCH_ENABLED", "yes"),
        ("APP_HOST", "0.0.0.0"),
        ("GMAIL_SENDER", "your-sender@gmail.com"),
        ("GMAIL_SENDER", "not an address"),
        ("TOKEN_PATH", " "),
        ("APP_DISPATCH_ALLOWED_RECIPIENTS", "rahul@example.com, rahul"),
    ],
)
def test_should_raise_config_error_when_enabled_dispatch_is_unsafe(
    env: pytest.MonkeyPatch, name: str, value: str
) -> None:
    env.setenv(name, value)
    with pytest.raises(ConfigError):
        load_dispatch_settings()


def test_should_stop_startup_when_dispatch_config_is_unsafe(env: pytest.MonkeyPatch) -> None:
    env.setenv("APP_HOST", "0.0.0.0")
    with pytest.raises(ConfigError):
        create_app()


def test_should_expire_a_guard_claim_after_the_window() -> None:
    now = [0.0]
    guard = DuplicateGuard(window_seconds=10, clock=lambda: now[0])

    assert guard.claim("k") is True
    assert guard.claim("k") is False
    now[0] = 10.0
    assert guard.claim("k") is True


class _Recorder:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.error = error

    def send(self, recipient: str, subject: str, body: str) -> str:
        self.calls.append((recipient, subject, body))
        if self.error is not None:
            raise self.error
        return "id-1"


def test_should_release_the_claim_when_the_send_fails() -> None:
    sender = _Recorder(DispatchFailed("gmail_http_error"))
    dispatcher = Dispatcher(sender, frozenset(), DuplicateGuard())

    with pytest.raises(DispatchFailed):
        dispatcher.dispatch(_DRAFT)
    sender.error = None

    assert dispatcher.dispatch(_DRAFT).status == "sent"
    assert len(sender.calls) == 2


def test_should_reject_before_claiming_when_recipient_is_not_allowed() -> None:
    sender = _Recorder()
    guard = DuplicateGuard()
    dispatcher = Dispatcher(sender, frozenset({"priya@example.com"}), guard)

    with pytest.raises(DispatchRejected):
        dispatcher.dispatch(_DRAFT)

    assert sender.calls == []
    assert Dispatcher(sender, frozenset(), guard).dispatch(_DRAFT).status == "sent"


def test_should_build_a_raw_message_with_the_draft_fields() -> None:
    raw = build_raw_message("me@example.com", *_fields())

    parsed = message_from_bytes(base64.urlsafe_b64decode(raw["raw"]), policy=policy.default)
    assert parsed["To"] == "rahul@example.com"
    assert parsed["From"] == "me@example.com"
    assert parsed["Subject"] == "Lab meeting"
    assert parsed.get_content().strip() == "Tomorrow at 10 AM"


def test_should_refuse_a_header_with_a_line_break() -> None:
    with pytest.raises(DispatchFailed):
        build_raw_message("me@example.com", "rahul@example.com", "Hi\nBcc: x@y.com", "b")


def _fields() -> tuple[str, str, str]:
    return (_DRAFT.recipient, _DRAFT.subject, _DRAFT.body)


def _write_token(path: Path, **overrides: object) -> Path:
    expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    info: dict[str, object] = {
        "token": "access-token",
        "refresh_token": "refresh-token",
        "client_id": "client-id",
        "client_secret": "client-secret",
        "scopes": [GMAIL_SEND_SCOPE],
        "expiry": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    info.update(overrides)
    path.write_text(json.dumps(info))
    return path


def test_should_load_a_valid_send_only_token(tmp_path: Path) -> None:
    creds = load_credentials(_write_token(tmp_path / "token.json"))
    assert creds.token == "access-token"


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        (lambda p: p, "token_missing"),
        (lambda p: p.write_text("not json") and p, "token_unreadable"),
        (
            lambda p: _write_token(
                p, scopes=[GMAIL_SEND_SCOPE, "https://www.googleapis.com/auth/gmail.readonly"]
            ),
            "token_scope",
        ),
        (lambda p: _write_token(p, token=None), "token_invalid"),
    ],
)
def test_should_be_unavailable_when_the_token_cannot_be_used(
    tmp_path: Path, setup, reason: str
) -> None:
    path = tmp_path / "token.json"
    setup(path)
    with pytest.raises(DispatchUnavailable, match=reason):
        load_credentials(path)


def test_should_refresh_and_save_an_expired_token_with_owner_only_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_token(tmp_path / "token.json", expiry="2000-01-01T00:00:00Z")

    def _refresh(self: Credentials, _request: object) -> None:
        self.token = "fresh-token"
        self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

    monkeypatch.setattr("app.dispatch.gmail.Request", lambda: object())
    monkeypatch.setattr(Credentials, "refresh", _refresh)

    creds = load_credentials(path)

    assert creds.token == "fresh-token"
    assert json.loads(path.read_text())["token"] == "fresh-token"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_should_be_unavailable_without_token_text_when_refresh_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write_token(tmp_path / "token.json", expiry="2000-01-01T00:00:00Z")

    def _reject(self: Credentials, _request: object) -> None:
        raise RefreshError("invalid_grant refresh-token")

    monkeypatch.setattr("app.dispatch.gmail.Request", lambda: object())
    monkeypatch.setattr(Credentials, "refresh", _reject)

    with pytest.raises(DispatchUnavailable) as info:
        load_credentials(path)
    assert "refresh-token" not in str(info.value)


def test_should_send_the_raw_message_through_the_injected_delivery(tmp_path: Path) -> None:
    seen: list[dict[str, str]] = []
    sender = GmailSender(
        "me@example.com",
        _write_token(tmp_path / "token.json"),
        deliver=lambda _creds, raw: seen.append(raw) or "gmail-id",
    )

    assert sender.send(*_fields()) == "gmail-id"
    decoded = base64.urlsafe_b64decode(seen[0]["raw"]).decode()
    assert "To: rahul@example.com" in decoded


def _fake_gmail_client(
    monkeypatch: pytest.MonkeyPatch, result: object = None, rejected: bool = False
) -> list[dict[str, object]]:
    """Install fake googleapiclient modules. monkeypatch removes them afterwards."""
    sent: list[dict[str, object]] = []

    class HttpError(Exception):
        def __init__(self, status: int) -> None:
            super().__init__("https://gmail.googleapis.com ya29.secret")
            self.resp = SimpleNamespace(status=status)

    def execute() -> object:
        if rejected:
            raise HttpError(403)
        return result

    def send(**kwargs: object) -> SimpleNamespace:
        sent.append(kwargs)
        return SimpleNamespace(execute=execute)

    service = SimpleNamespace(
        users=lambda: SimpleNamespace(messages=lambda: SimpleNamespace(send=send))
    )
    discovery = types.ModuleType("googleapiclient.discovery")
    discovery.build = lambda *_a, **_k: service
    errors = types.ModuleType("googleapiclient.errors")
    errors.HttpError = HttpError
    monkeypatch.setitem(sys.modules, "googleapiclient", types.ModuleType("googleapiclient"))
    monkeypatch.setitem(sys.modules, "googleapiclient.discovery", discovery)
    monkeypatch.setitem(sys.modules, "googleapiclient.errors", errors)
    return sent


def test_should_return_the_gmail_message_id(monkeypatch: pytest.MonkeyPatch) -> None:
    sent = _fake_gmail_client(monkeypatch, result={"id": "gmail-123"})

    assert real_deliver(object(), {"raw": "abc"}) == "gmail-123"
    assert sent == [{"userId": "me", "body": {"raw": "abc"}}]


@pytest.mark.parametrize(
    ("result", "rejected", "reason"),
    [
        (None, True, "gmail_http_error"),
        ({"labelIds": []}, False, "no_message_id"),
    ],
)
def test_should_fail_without_provider_text_when_gmail_does_not_confirm(
    monkeypatch: pytest.MonkeyPatch, result: object, rejected: bool, reason: str
) -> None:
    _fake_gmail_client(monkeypatch, result=result, rejected=rejected)

    with pytest.raises(DispatchFailed) as info:
        real_deliver(object(), {"raw": "abc"})
    assert str(info.value) == reason
    assert "ya29" not in str(info.value)


def test_should_never_start_a_browser_sign_in() -> None:
    source = (Path(__file__).resolve().parents[1] / "app" / "dispatch").rglob("*.py")
    text = "\n".join(path.read_text() for path in source)
    assert "InstalledAppFlow" not in text
    assert "run_local_server" not in text
    assert "google_auth_oauthlib" not in text
