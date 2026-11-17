"""Public sign-in. Google Identity Services plus email/password. No /chat or Gmail."""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, HTTPException
from starlette.concurrency import run_in_threadpool
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, ConfigDict, field_validator

from app.config import load_google_client_id
from app.local_auth import DuplicateUserError, authenticate, register_user

logger = logging.getLogger(__name__)

_MAX_CREDENTIAL_LENGTH = 8000
_MAX_PASSWORD_LENGTH = 128
_MAX_NAME_LENGTH = 80
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_INVALID_LOGIN = "Invalid email or password."
_DUPLICATE_EMAIL = "An account with that email already exists."

router = APIRouter()


class GoogleAuthRequest(BaseModel):
    """GIS ID token from the browser. Never logged."""

    model_config = ConfigDict(strict=True)

    credential: str

    @field_validator("credential")
    @classmethod
    def strip_and_bound(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 1:
            raise ValueError("credential must not be empty")
        if len(stripped) > _MAX_CREDENTIAL_LENGTH:
            raise ValueError("credential is too long")
        return stripped


class GoogleProfile(BaseModel):
    """Safe profile fields for the sidebar. No token."""

    name: str
    email: str
    picture: str


class PasswordLoginRequest(BaseModel):
    """Email/password sign-in. The password is never logged."""

    model_config = ConfigDict(strict=True)

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _require_email(value)

    @field_validator("password")
    @classmethod
    def require_password(cls, value: str) -> str:
        if not isinstance(value, str) or not (1 <= len(value) <= _MAX_PASSWORD_LENGTH):
            raise ValueError("password is invalid")
        return value


class RegisterRequest(BaseModel):
    """Create an email/password account."""

    model_config = ConfigDict(strict=True)

    name: str
    email: str
    password: str

    @field_validator("name")
    @classmethod
    def require_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped or len(stripped) > _MAX_NAME_LENGTH:
            raise ValueError("name is invalid")
        return stripped

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _require_email(value)

    @field_validator("password")
    @classmethod
    def require_strong_password(cls, value: str) -> str:
        if len(value) < 8 or len(value) > _MAX_PASSWORD_LENGTH:
            raise ValueError("password is too short")
        if not any(ch.isalpha() for ch in value) or not any(ch.isdigit() for ch in value):
            raise ValueError("password is too weak")
        return value


@router.post("/auth/login", response_model=GoogleProfile)
async def password_login(body: PasswordLoginRequest) -> GoogleProfile:
    """Grant a workspace profile only when the password hash matches."""
    profile = await run_in_threadpool(authenticate, body.email, body.password)
    if profile is None:
        raise HTTPException(status_code=401, detail=_INVALID_LOGIN)
    return GoogleProfile(
        name=profile["name"],
        email=profile["email"],
        picture=profile["picture"],
    )


@router.post("/auth/register", response_model=GoogleProfile)
async def password_register(body: RegisterRequest) -> GoogleProfile:
    """Create an account and return the same profile shape as Google Sign-In."""
    try:
        profile = await run_in_threadpool(
            register_user, body.name, body.email, body.password
        )
    except DuplicateUserError as exc:
        raise HTTPException(status_code=409, detail=_DUPLICATE_EMAIL) from exc
    return GoogleProfile(
        name=profile["name"],
        email=profile["email"],
        picture=profile["picture"],
    )


@router.post("/auth/google", response_model=GoogleProfile)
async def google_auth(body: GoogleAuthRequest) -> GoogleProfile:
    """Verify a GIS ID token and return the user's name, email, and photo."""
    audience = load_google_client_id()
    if not audience:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured.",
        )
    try:
        claims = await run_in_threadpool(
            verify_google_id_token, body.credential, audience
        )
        return _profile_from_claims(claims)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("google auth failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=401,
            detail="Google sign-in was not accepted.",
        ) from exc


def verify_google_id_token(credential: str, audience: str) -> dict[str, object]:
    """Check the token with Google. Tests replace this function."""
    claims = id_token.verify_oauth2_token(
        credential,
        google_requests.Request(),
        audience=audience,
    )
    if not isinstance(claims, dict):
        raise ValueError("invalid_claims")
    return claims


def _require_email(value: str) -> str:
    stripped = value.strip().lower()
    if not _EMAIL_RE.match(stripped) or len(stripped) > 254:
        raise ValueError("email is invalid")
    return stripped


def _profile_from_claims(claims: dict[str, object]) -> GoogleProfile:
    email = claims.get("email")
    if not isinstance(email, str) or not email.strip() or "@" not in email:
        raise ValueError("email_missing")
    name = claims.get("name")
    picture = claims.get("picture")
    return GoogleProfile(
        email=email.strip(),
        name=name.strip() if isinstance(name, str) and name.strip() else email.strip(),
        picture=picture.strip() if isinstance(picture, str) else "",
    )
