"""Liveness and a public, secret-free guardrail summary."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import load_dispatch_public_status

_UNCERTAINTY_POLICY = "Ask on missing recipient/intent; auto-draft body"
_EXTRACTION_ENGINE = "Gemini + Local Heuristic Fallback"

router = APIRouter()


class HealthResponse(BaseModel):
    """Liveness payload. This process does not check Gmail or a model."""

    status: str


class HealthConfigResponse(BaseModel):
    """Read-only guardrails for the telemetry view. No secrets."""

    extraction_engine: str
    dispatch_enabled: bool
    allow_all_recipients: bool
    dispatch_mode: str
    uncertainty_policy: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report that the process is up. Nothing else is probed."""
    return HealthResponse(status="ok")


@router.get("/health/config", response_model=HealthConfigResponse)
def health_config() -> HealthConfigResponse:
    """Report extraction and dispatch policy. Never includes keys or paths."""
    status = load_dispatch_public_status()
    return HealthConfigResponse(
        extraction_engine=_EXTRACTION_ENGINE,
        dispatch_enabled=status.enabled,
        allow_all_recipients=status.allow_all_recipients,
        dispatch_mode=status.mode,
        uncertainty_policy=_UNCERTAINTY_POLICY,
    )
