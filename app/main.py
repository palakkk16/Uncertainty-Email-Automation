"""FastAPI application factory for chat extraction and the decision layer."""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import load_settings
from app.routers.chat import router as chat_router


class HealthResponse(BaseModel):
    """Liveness payload. This process does not check Gmail or a model."""

    status: str


def health() -> HealthResponse:
    """Report that the process is up. Nothing else is probed."""
    return HealthResponse(status="ok")


def create_app() -> FastAPI:
    """Build the API.

    Settings load here so a bad APP_PORT stops startup before any request
    is served. A missing Gemini key does not stop startup; POST /chat
    returns an error instead of guessing fields.
    """
    load_settings()
    application = FastAPI(
        title="UNCERTAIN-EMAIL",
        version="0.4.0",
        description=(
            "Phase 4 copies email fields with one Gemini free-tier call, "
            "then Python applies a slot-sufficiency threshold and returns "
            "ASK or SEND. That decision does not send mail."
        ),
    )
    application.include_router(chat_router)
    application.add_api_route(
        "/health",
        health,
        methods=["GET"],
        response_model=HealthResponse,
    )
    return application


app = create_app()
