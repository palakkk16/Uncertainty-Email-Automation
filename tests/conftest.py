"""Offline defaults for the whole suite.

POST /chat refuses to extract when GEMINI_API_KEY is empty. The chat tests
replace the SDK client and do not use the network. A placeholder satisfies
that guard. It is not a credential and it is not sent anywhere.

Dispatch is forced off here, not defaulted: load_dotenv never overrides a
variable that is already set, so APP_DISPATCH_ENABLED=true in a developer's
.env cannot reach the tests. The Gmail send and token refresh are also
replaced, so a test that wires dispatch by mistake fails instead of sending.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

if not os.environ.get("GEMINI_API_KEY", "").strip():
    os.environ["GEMINI_API_KEY"] = "test-not-a-real-key"
os.environ["APP_DISPATCH_ENABLED"] = "false"
os.environ["APP_ALLOW_ALL_RECIPIENTS"] = "false"
os.environ["APP_REQUIRE_USER_GMAIL_TOKEN"] = "false"
os.environ["APP_GOOGLE_CLIENT_ID"] = "test-google-client.apps.googleusercontent.com"
# Pin the model so a retired id in a developer's .env cannot reach the suite.
os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"
os.environ["APP_SIGNER_NAME"] = "Palak"
os.environ["APP_USERS_PATH"] = str(
    Path(tempfile.gettempdir()) / f"uncertain-email-users-{os.getpid()}.json"
)


def _refuse_network(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("tests must not call Gmail or the Google token endpoint")


@pytest.fixture(autouse=True)
def _block_gmail_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.dispatch.gmail._deliver", _refuse_network)
    monkeypatch.setattr("app.dispatch.gmail.Request", _refuse_network)


@pytest.fixture(autouse=True)
def _reset_gemini_model_cache() -> None:
    from app.extraction.gemini import reset_model_cache

    reset_model_cache()
    yield
    reset_model_cache()


@pytest.fixture(autouse=True)
def _isolate_password_users() -> None:
    path = Path(os.environ["APP_USERS_PATH"])
    if path.exists():
        path.unlink()
    yield
    if path.exists():
        path.unlink()
