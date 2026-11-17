"""FastAPI application factory for chat extraction and the decision layer."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_cors_origins, load_dispatch_settings, load_settings
from app.local_auth import seed_demo_users
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
    origins = load_cors_origins()
    seed_demo_users()
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
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_credentials=False,
        allow_methods=["GET", "HEAD", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Gmail-Token"],
    )
    application.include_router(chat_router)
    application.include_router(health_router)
    application.include_router(auth_router)
    return application


app = create_app()
