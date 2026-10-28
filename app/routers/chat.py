"""POST /chat field extraction, the ASK versus SEND threshold, and dispatch.

One Gemini call copies fields. Python then applies the slot-sufficiency
threshold. A SEND is delivered through Gmail only when dispatch is enabled.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.decision import Draft, decide
from app.decision.sufficiency import Decision
from app.dispatch import (
    Dispatcher,
    DispatchFailed,
    DispatchRejected,
    DispatchUnavailable,
    get_dispatcher,
)
from app.extraction.gemini import (
    ExtractionError,
    ExtractionRateLimited,
    ExtractionUnavailable,
    extract_email_fields,
)
from app.schemas.chat import ChatRequest, ChatResponse, DispatchResult, EmailExtraction

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    dispatcher: Annotated[Dispatcher | None, Depends(get_dispatcher)],
) -> ChatResponse:
    """Extract stated fields, choose ASK or SEND in Python, then dispatch a SEND."""
    fields = _extract(body.message)
    outcome = decide(body.message, fields)
    dispatch = None
    if outcome.draft is not None:
        dispatch = _dispatch(dispatcher, outcome.draft)
    return ChatResponse(
        reply=_reply(outcome, dispatch),
        phase="decision_layer",
        decision=outcome.decision,
        clarification=outcome.clarification,
        extraction=fields,
        assessment=outcome.assessment,
        dispatch=dispatch,
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


def _dispatch(dispatcher: Dispatcher | None, draft: Draft) -> DispatchResult:
    """Map dispatch failures to fixed HTTP details. Never log the draft."""
    if dispatcher is None:
        return DispatchResult(status="disabled")
    try:
        return dispatcher.dispatch(draft)
    except DispatchRejected as exc:
        _log_reason(exc)
        raise HTTPException(
            status_code=403,
            detail="Recipient is not on the dispatch allowlist.",
        ) from exc
    except DispatchUnavailable as exc:
        _log_reason(exc)
        raise HTTPException(
            status_code=503,
            detail="Email dispatch is unavailable.",
        ) from exc
    except DispatchFailed as exc:
        _log_reason(exc)
        raise HTTPException(
            status_code=502,
            detail="Email dispatch failed.",
        ) from exc


def _reply(outcome: Decision, dispatch: DispatchResult | None) -> str:
    if dispatch is None or outcome.draft is None or dispatch.status == "disabled":
        return outcome.reply
    recipient = outcome.draft.recipient
    if dispatch.status == "already_sent":
        return f"This email was already sent to {recipient}. It was not sent again."
    return f"Email sent to {recipient}."


def _log_type(exc: Exception) -> None:
    logger.warning("extraction error: %s", type(exc).__name__)


def _log_reason(exc: Exception) -> None:
    """Dispatch errors carry a fixed reason code such as token_missing."""
    logger.warning("dispatch error: %s (%s)", type(exc).__name__, exc)
