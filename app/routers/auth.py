"""Public Google Identity Services sign-in. Does not touch /chat or Gmail."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, ConfigDict, field_validator

from app.config import load_google_client_id

logger = logging.getLogger(__name__)

_MAX_CREDENTIAL_LENGTH = 8000

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


@router.post("/auth/google", response_model=GoogleProfile)
def google_auth(body: GoogleAuthRequest) -> GoogleProfile:
    """Verify a GIS ID token and return the user's name, email, and photo."""
    audience = load_google_client_id()
    if not audience:
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured.",
        )
    try:
        claims = verify_google_id_token(body.credential, audience)
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
