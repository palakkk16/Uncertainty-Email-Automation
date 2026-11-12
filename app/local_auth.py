"""Email/password accounts for the demo workspace. Never logs secrets."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SCHEME = "pbkdf2_sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16
_LOCK = threading.Lock()
_DUMMY_HASH: str | None = None

_DEMO_ACCOUNTS = (
    ("Admin", "admin@uncertain.ai", "Demo@1234"),
    ("Palak", "palak@gmail.com", "Palak@123"),
)


class DuplicateUserError(Exception):
    """The email is already registered."""


def users_path() -> Path:
    raw = os.environ.get("APP_USERS_PATH", "").strip()
    if raw:
        return Path(raw)
    return _PROJECT_ROOT / "data" / "users.json"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
    )
    return f"{_SCHEME}${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iter_s, salt_hex, digest_hex = encoded.split("$")
        if scheme != _SCHEME:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iter_s),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def seed_demo_users() -> None:
    """Add faculty demo accounts if they are missing. Does not reset passwords."""
    with _LOCK:
        users = _read_users()
        changed = False
        for name, email, password in _DEMO_ACCOUNTS:
            key = email.lower()
            if key in users:
                continue
            users[key] = {
                "email": key,
                "name": name,
                "password": hash_password(password),
            }
            changed = True
        if changed:
            _write_users(users)


def authenticate(email: str, password: str) -> dict[str, str] | None:
    key = email.strip().lower()
    with _LOCK:
        record = _read_users().get(key)
        encoded = record["password"] if record else _dummy_hash()
    if not verify_password(password, encoded) or record is None:
        return None
    return _public_profile(record)


def register_user(name: str, email: str, password: str) -> dict[str, str]:
    key = email.strip().lower()
    display = name.strip()
    with _LOCK:
        users = _read_users()
        if key in users:
            raise DuplicateUserError
        users[key] = {
            "email": key,
            "name": display,
            "password": hash_password(password),
        }
        _write_users(users)
    return {"name": display, "email": key, "picture": ""}


def _read_users() -> dict[str, dict[str, str]]:
    path = users_path()
    if not path.exists():
        return {}
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("user store unreadable; starting empty")
        return {}
    if not isinstance(payload, dict):
        return {}
    users: dict[str, dict[str, str]] = {}
    for key, value in payload.items():
        if isinstance(key, str) and _is_user_record(value):
            users[key.lower()] = value
    return users


def _write_users(users: dict[str, dict[str, str]]) -> None:
    path = users_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(users, indent=2), encoding="utf-8")
    tmp.replace(path)


def _is_user_record(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    return (
        isinstance(value.get("email"), str)
        and isinstance(value.get("name"), str)
        and isinstance(value.get("password"), str)
    )


def _public_profile(record: dict[str, str]) -> dict[str, str]:
    return {
        "name": record["name"],
        "email": record["email"],
        "picture": "",
    }


def _dummy_hash() -> str:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("dummy")
    return _DUMMY_HASH
