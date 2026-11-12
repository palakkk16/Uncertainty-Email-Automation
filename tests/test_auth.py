"""POST /auth/google verifies a GIS ID token. It does not call /chat or Gmail."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_PROFILE = {
    "email": "ada@example.com",
    "name": "Ada Lovelace",
    "picture": "https://example.com/ada.png",
}


def test_should_return_the_google_profile_when_the_id_token_is_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda *_a, **_k: _PROFILE,
    )

    response = client.post("/auth/google", json={"credential": "header.payload.sig"})

    assert response.status_code == 200
    assert response.json() == _PROFILE


def test_should_return_401_when_the_id_token_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _reject(*_a: object, **_k: object) -> dict[str, str]:
        raise ValueError("invalid")

    monkeypatch.setattr("app.routers.auth.verify_google_id_token", _reject)

    response = client.post("/auth/google", json={"credential": "header.payload.sig"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Google sign-in was not accepted."}
    assert "header.payload.sig" not in response.text


def test_should_return_503_when_google_client_id_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.routers.auth.load_google_client_id", lambda: None)

    response = client.post("/auth/google", json={"credential": "header.payload.sig"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Google sign-in is not configured."}


def test_should_reject_a_blank_credential() -> None:
    response = client.post("/auth/google", json={"credential": "   "})

    assert response.status_code == 422
