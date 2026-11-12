"""FastAPI application factory for chat extraction and the decision layer."""

from __future__ import annotations

from fastapi import FastAPI

from app.config import load_dispatch_settings, load_settings
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router


def create_app() -> FastAPI:
    """Build the API.

    Settings load here so a bad APP_PORT or an enabled but unsafe dispatch
    configuration stops startup before any request is served. A missing
    Gemini key does not stop startup; POST /chat returns an error instead
    of guessing fields.
    """
    load_settings()
    load_dispatch_settings()
    application = FastAPI(
        title="UNCERTAIN-EMAIL",
        version="0.5.0",
        description=(
            "Copies email fields with one Gemini free-tier call, then Python "
            "applies a slot-sufficiency threshold and returns ASK or SEND. "
            "A SEND is delivered through Gmail only when APP_DISPATCH_ENABLED "
            "is true."
        ),
    )
    application.include_router(chat_router)
    application.include_router(health_router)
    application.include_router(auth_router)
    return application


app = create_app()
