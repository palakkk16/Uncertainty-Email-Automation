"""One Gemini API call that copies recipient, subject, and body.

The client lives here so tests can replace `google.genai` without touching
the route. This module does not decide ASK vs SEND and does not send mail.
Calls use the Gemini API (Google AI Studio), not Vertex AI.
"""

from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.config import load_settings
from app.extraction.mentions import copied_mention
from app.schemas.chat import EmailExtraction

logger = logging.getLogger(__name__)

# Copy-only. Do not ask the model for a confidence score or for ASK vs SEND.
_SYSTEM = (
    "Extract email fields from the user instruction. "
    "Return JSON with exactly these keys: recipient, subject, body, recipient_mention. "
    "recipient is an email address copied verbatim from the instruction, or null. "
    "Never invent an email address. A person's name is not an email address. "
    "recipient_mention is a person's name copied verbatim from the instruction, or null. "
    "Never invent a name. "
    "subject is the subject line copied verbatim only if the instruction states one, or null. "
    "body is the message body copied verbatim only if the instruction states one, or null. "
    "Do not draft, paraphrase, or fill gaps. Do not add a confidence score. "
    "Do not choose whether to ask or send."
)


class ExtractionError(Exception):
    """Gemini failed or returned output that must not be guessed into fields."""


class ExtractionUnavailable(ExtractionError):
    """No Gemini API key is configured, so the call must not be attempted."""


class ExtractionRateLimited(ExtractionError):
    """Gemini returned HTTP 429. The message is the type name, not the client text."""


def extract_email_fields(instruction: str) -> EmailExtraction:
    """Run one free-tier Gemini call and keep only text the user wrote."""
    settings = load_settings()
    if not settings.gemini_api_key:
        raise ExtractionUnavailable("GEMINI_API_KEY is not set")
    raw = _generate(settings.gemini_api_key, settings.gemini_model, instruction)
    return parse_extraction(raw, instruction)


def _generate(api_key: str, model: str, instruction: str) -> str:
    """Call Gemini once. Exception text is dropped because it can echo the key."""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=instruction,
            config=_generation_config(),
        )
    except Exception as exc:
        logger.warning("Gemini request failed: %s", type(exc).__name__)
        # ClientError.code is the HTTP status. status is a label such as
        # RESOURCE_EXHAUSTED, and the exception text can include the request URL.
        if _is_rate_limited(exc):
            raise ExtractionRateLimited(type(exc).__name__) from exc
        raise ExtractionError(type(exc).__name__) from exc
    text = response.text
    if not isinstance(text, str) or not text.strip():
        raise ExtractionError("empty_response")
    return text


def _is_rate_limited(exc: BaseException) -> bool:
    """True only for HTTP 429. Do not read the exception string."""
    code = getattr(exc, "code", None)
    status = getattr(exc, "status", None)
    return code == 429 or status == 429


def _generation_config() -> types.GenerateContentConfig:
    """JSON schema only. Low thinking avoids a large free-tier token spend."""
    return types.GenerateContentConfig(
        system_instruction=_SYSTEM,
        temperature=0,
        max_output_tokens=1024,
        response_mime_type="application/json",
        response_schema=EmailExtraction,
        # The SDK turns automatic function calling on unless this is set, and
        # that path is for tools. Extraction is one structured generateContent.
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,
            thinking_level=types.ThinkingLevel.LOW,
        ),
    )


def parse_extraction(raw: str, instruction: str) -> EmailExtraction:
    """Accept only copied fields. Invalid JSON is a failure, not a guess."""
    payload = _load_object(raw)
    try:
        parsed = EmailExtraction.model_validate(
            {
                "recipient": payload.get("recipient"),
                "subject": payload.get("subject"),
                "body": payload.get("body"),
                "recipient_mention": payload.get("recipient_mention"),
            }
        )
    except ValidationError as exc:
        raise ExtractionError("unparseable") from exc
    return EmailExtraction(
        recipient=_stated_address(parsed.recipient, instruction),
        subject=_stated_text(parsed.subject, instruction),
        body=_stated_text(parsed.body, instruction),
        recipient_mention=copied_mention(parsed.recipient_mention, instruction),
    )


def _load_object(raw: str) -> dict[str, object]:
    """Reject anything that is not a JSON object."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtractionError("unparseable") from exc
    if not isinstance(payload, dict):
        raise ExtractionError("unparseable")
    return payload


def _stated_address(value: str | None, instruction: str) -> str | None:
    """Keep an address only when the user actually wrote that address."""
    text = _stated_text(value, instruction)
    if text is None or "@" not in text:
        return None
    return text


def _stated_text(value: str | None, instruction: str) -> str | None:
    """Drop blanks and strings the instruction does not contain."""
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    if _folded(cleaned) not in _folded(instruction):
        return None
    return cleaned


def _folded(value: str) -> str:
    return " ".join(value.split()).lower()
