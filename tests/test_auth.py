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


def test_should_reject_login_when_the_email_is_unknown() -> None:
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "Demo@1234"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}


def test_should_reject_login_when_the_password_does_not_match() -> None:
    from app.local_auth import seed_demo_users

    seed_demo_users()
    response = client.post(
        "/auth/login",
        json={"email": "admin@uncertain.ai", "password": "Wrong@1234"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}
    assert "Wrong@1234" not in response.text


def test_should_return_the_profile_when_the_demo_password_matches() -> None:
    from app.local_auth import seed_demo_users

    seed_demo_users()
    response = client.post(
        "/auth/login",
        json={"email": "admin@uncertain.ai", "password": "Demo@1234"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "email": "admin@uncertain.ai",
        "name": "Admin",
        "picture": "",
    }
    assert "Demo@1234" not in response.text
    assert "password" not in response.json()


def test_should_accept_the_palak_demo_account() -> None:
    from app.local_auth import seed_demo_users

    seed_demo_users()
    response = client.post(
        "/auth/login",
        json={"email": "palak@gmail.com", "password": "Palak@123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "palak@gmail.com"
    assert body["name"] == "Palak"
    assert body["picture"] == ""


def test_should_create_an_account_and_return_the_profile() -> None:
    response = client.post(
        "/auth/register",
        json={
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "password": "AdaPass1",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "email": "ada@example.com",
        "name": "Ada Lovelace",
        "picture": "",
    }
    login = client.post(
        "/auth/login",
        json={"email": "ada@example.com", "password": "AdaPass1"},
    )
    assert login.status_code == 200
    assert login.json()["email"] == "ada@example.com"


def test_should_reject_a_duplicate_registration() -> None:
    payload = {
        "name": "Ada Lovelace",
        "email": "ada@example.com",
        "password": "AdaPass1",
    }
    assert client.post("/auth/register", json=payload).status_code == 200
    response = client.post("/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json() == {"detail": "An account with that email already exists."}


def test_should_store_a_password_hash_not_plaintext() -> None:
    from app.local_auth import seed_demo_users, users_path

    seed_demo_users()
    stored = users_path().read_text()
    assert "Demo@1234" not in stored
    assert "Palak@123" not in stored
    assert "pbkdf2_sha256$" in stored
