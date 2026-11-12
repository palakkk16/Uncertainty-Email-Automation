"""Bind settings, the optional Gemini free-tier configuration, and dispatch.

A missing GEMINI_API_KEY must not stop /health. POST /chat reports that
as unavailable instead of inventing fields. The key is never logged.
Dispatch is off unless APP_DISPATCH_ENABLED is true, and an enabled but
unusable dispatch configuration stops startup.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"

# Repo root, so `.env` is found when uvicorn is started from another cwd.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8741

# POST /chat is unauthenticated. Sending real mail is only allowed when the
# server cannot be reached from another machine.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_PLACEHOLDER_SENDER = "your-sender@gmail.com"
_ADDRESS_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._%+\-]*@[A-Za-z0-9][A-Za-z0-9.\-]*\.[A-Za-z]{2,}"
)
_BOOLEANS = {"true": True, "false": False}

# Google AI Studio free tier (standard), confirmed on the Gemini API pricing
# page. Not a Pro model and not a Vertex AI model id.
GEMINI_MODEL: str = DEFAULT_GEMINI_MODEL


class ConfigError(Exception):
    """APP_HOST or APP_PORT cannot be used to bind the server."""


@dataclass(frozen=True)
class Settings:
    """Bind address plus the Gemini model used by POST /chat."""

    host: str
    port: int
    gemini_api_key: str | None
    gemini_model: str


def load_settings() -> Settings:
    """Read bind settings and refuse to continue when they are unusable.

    Defaults match the documented uvicorn command so a missing `.env` still
    starts on 127.0.0.1:8741. A present but invalid port must not fall
    through to a surprise bind. An empty Gemini key stays None so the chat
    route can fail the request without guessing fields.
    """
    # Missing `.env` is fine. Real environment variables win over the file.
    load_dotenv(_PROJECT_ROOT / ".env")
    host = os.environ.get("APP_HOST", _DEFAULT_HOST).strip()
    port_raw = os.environ.get("APP_PORT", str(_DEFAULT_PORT)).strip()
    if not host:
        raise ConfigError("APP_HOST must be a non-empty hostname or IP")
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
    if not model:
        model = DEFAULT_GEMINI_MODEL
    key = os.environ.get("GEMINI_API_KEY", "").strip() or None
    return Settings(
        host=host,
        port=_parse_port(port_raw),
        gemini_api_key=key,
        gemini_model=model,
    )


def _parse_port(port_raw: str) -> int:
    """Reject anything that is not a TCP port before the server binds."""
    if not port_raw.isdigit():
        raise ConfigError("APP_PORT must be an integer from 1 to 65535")
    port = int(port_raw)
    if port < 1 or port > 65535:
        raise ConfigError("APP_PORT must be an integer from 1 to 65535")
    return port


@dataclass(frozen=True)
class DispatchSettings:
    """Gmail dispatch on SEND.

    An empty allowed_recipients means any address the user wrote may be used.
    APP_ALLOW_ALL_RECIPIENTS=true (default) forces that empty set so a demo
    can send to any valid address. Entries are lowercased.
    """

    sender: str
    token_path: Path
    allowed_recipients: frozenset[str]


def load_dispatch_settings() -> DispatchSettings | None:
    """Return None when dispatch is off. Refuse an enabled but unsafe setup.

    The token file is not required here. It can expire or be created after
    startup, so the sender checks it on each send.
    """
    host = load_settings().host
    enabled = _parse_bool(
        "APP_DISPATCH_ENABLED", os.environ.get("APP_DISPATCH_ENABLED", "false")
    )
    if not enabled:
        return None
    if host.lower() not in _LOOPBACK_HOSTS:
        raise ConfigError(
            "APP_DISPATCH_ENABLED requires APP_HOST to be 127.0.0.1, localhost, or ::1"
        )
    return DispatchSettings(
        sender=_parse_sender(os.environ.get("GMAIL_SENDER", "")),
        token_path=_parse_token_path(os.environ.get("TOKEN_PATH", "")),
        allowed_recipients=_load_allowed_recipients(),
    )


def _parse_bool(name: str, raw: str) -> bool:
    value = _BOOLEANS.get(raw.strip().lower())
    if value is None:
        raise ConfigError(f"{name} must be true or false")
    return value


def _parse_sender(raw: str) -> str:
    sender = raw.strip()
    if sender == _PLACEHOLDER_SENDER or not is_address(sender):
        raise ConfigError(
            "APP_DISPATCH_ENABLED requires GMAIL_SENDER to be your Gmail address"
        )
    return sender


def _parse_token_path(raw: str) -> Path:
    value = raw.strip()
    if not value:
        raise ConfigError("APP_DISPATCH_ENABLED requires TOKEN_PATH")
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return _PROJECT_ROOT / path


def _load_allowed_recipients() -> frozenset[str]:
    """Union APP_DISPATCH_ALLOWED_RECIPIENTS with DISPATCH_ALLOWLIST aliases.

    APP_ALLOW_ALL_RECIPIENTS (alias ALLOW_ALL_RECIPIENTS) defaults to true so
    dispatch is not limited to a named list. Set it false to enforce the list.
    """
    if _allow_all_recipients():
        return frozenset()
    combined = ",".join(
        (
            os.environ.get("APP_DISPATCH_ALLOWED_RECIPIENTS", ""),
            os.environ.get("DISPATCH_ALLOWLIST", ""),
            os.environ.get("ALLOWED_RECIPIENTS", ""),
        )
    )
    return _parse_allowlist(combined)


def _allow_all_recipients() -> bool:
    raw = os.environ.get("APP_ALLOW_ALL_RECIPIENTS")
    if raw is None or not raw.strip():
        raw = os.environ.get("ALLOW_ALL_RECIPIENTS", "true")
    return _parse_bool("APP_ALLOW_ALL_RECIPIENTS", raw)


def _parse_allowlist(raw: str) -> frozenset[str]:
    entries = [item.strip().lower() for item in raw.split(",") if item.strip()]
    invalid = [item for item in entries if not is_address(item)]
    if invalid:
        raise ConfigError(
            "APP_DISPATCH_ALLOWED_RECIPIENTS must be comma-separated email addresses"
        )
    return frozenset(entries)


def is_address(value: str) -> bool:
    """True when value is exactly one email address and nothing else."""
    return _ADDRESS_RE.fullmatch(value) is not None


@dataclass(frozen=True)
class DispatchPublicStatus:
    """Safe-to-display dispatch flags. No addresses, keys, or token paths."""

    enabled: bool
    allow_all_recipients: bool
    mode: str


def load_dispatch_public_status() -> DispatchPublicStatus:
    """Describe dispatch for the telemetry page. Does not send mail."""
    load_settings()
    enabled = _parse_bool(
        "APP_DISPATCH_ENABLED", os.environ.get("APP_DISPATCH_ENABLED", "false")
    )
    allow_all = _allow_all_recipients()
    if not enabled:
        mode = "Preview only (dispatch off)"
    elif allow_all:
        mode = "Live Gmail OAuth / Wildcard Demo Mode"
    else:
        mode = "Live Gmail OAuth"
    return DispatchPublicStatus(
        enabled=enabled,
        allow_all_recipients=allow_all,
        mode=mode,
    )


def load_google_client_id() -> str | None:
    """OAuth web/installed client id for GIS. Never returns a client secret."""
    load_settings()
    for name in (
        "APP_GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_ID",
        "VITE_GOOGLE_CLIENT_ID",
    ):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return _client_id_from_credentials()


def _client_id_from_credentials() -> str | None:
    raw = (
        os.environ.get("CREDENTIALS_PATH", "").strip()
        or os.environ.get("CLIENT_SECRET_PATH", "").strip()
        or "credentials/credentials.json"
    )
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    for block in payload.values():
        if not isinstance(block, dict):
            continue
        client_id = block.get("client_id")
        if isinstance(client_id, str) and client_id.strip():
            return client_id.strip()
    return None
