"""POST /chat field extraction and the ASK versus SEND threshold.

One Gemini call copies fields. Python then applies the slot-sufficiency
threshold. This router does not import the mail sender and does not send.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from app.decision import decide
from app.extraction.gemini import (
    ExtractionError,
    ExtractionRateLimited,
    ExtractionUnavailable,
    extract_email_fields,
)
from app.schemas.chat import ChatRequest, ChatResponse, EmailExtraction

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    """Extract stated fields, then choose ASK or SEND in Python."""
    fields = _extract(body.message)
    outcome = decide(body.message, fields)
    return ChatResponse(
        reply=outcome.reply,
        phase="decision_layer",
        decision=outcome.decision,
        clarification=outcome.clarification,
        extraction=fields,
        assessment=outcome.assessment,
    )


def _extract(message: str) -> EmailExtraction:
    """Map extractor failures to HTTP without copying the exception text.

    Gemini client errors can include the request URL, which may carry the key.
    """
    try:
        return extract_email_fields(message)
    except ExtractionUnavailable as exc:
        _log_type(exc)
        raise HTTPException(
            status_code=503,
            detail="Gemini extraction is unavailable.",
        ) from exc
    except ExtractionRateLimited as exc:
        _log_type(exc)
        raise HTTPException(
            status_code=429,
            detail="Gemini rate limit.",
        ) from exc
    except ExtractionError as exc:
        _log_type(exc)
        raise HTTPException(
            status_code=502,
            detail="Gemini extraction failed.",
        ) from exc


def _log_type(exc: Exception) -> None:
    logger.warning("extraction error: %s", type(exc).__name__)
