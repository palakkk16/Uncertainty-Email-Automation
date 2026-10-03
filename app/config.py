"""Bind settings and the optional Gemini free-tier configuration.

A missing GEMINI_API_KEY must not stop /health. POST /chat reports that
as unavailable instead of inventing fields. The key is never logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Repo root, so `.env` is found when uvicorn is started from another cwd.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8741

# Google AI Studio free tier (standard), confirmed on the Gemini API pricing
# page. Not a Pro model and not a Vertex AI model id.
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"


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
