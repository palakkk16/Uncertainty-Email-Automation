"""One Gemini API call that copies the recipient and drafts subject and body.

The client lives here so tests can replace `google.genai` without touching
the route. This module does not decide ASK vs SEND and does not send mail.
A retired model id is replaced once from `client.models.list()`, not guessed
into a Pro or paid model.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterable

from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.config import (
    DEFAULT_GEMINI_FALLBACK_MODEL,
    DEFAULT_GEMINI_MODEL,
    GEMINI_HTTP_RETRY_ATTEMPTS,
    GEMINI_HTTP_TIMEOUT_MS,
    load_settings,
)
from app.extraction.heuristic import (
    apply_followup_slots,
    compose_missing_body,
    local_regex_extract,
)
from app.extraction.mentions import copied_mention
from app.schemas.chat import EmailExtraction

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Extract email fields and draft a complete email, like Gmail Help me write. "
    "Return JSON with exactly these keys: recipient, subject, body, recipient_mention. "
    "recipient is an email address copied verbatim from the instruction, or null. "
    "Never invent an email address. A person's name is not an email address. "
    "recipient_mention is a person's name copied verbatim from the instruction, or null. "
    "Never invent a name. "
    "subject is a clean Title Case subject line expanded from the user's topic "
    "(for example 'sick leave approval' becomes 'Request for Sick Leave Approval'). "
    "Never leave a raw lowercase fragment as the subject. "
    "body is a complete professional email: greeting (Hi FirstName, when the name "
    "is known), one or two natural paragraphs that expand the user's intent, and "
    "a sign-off of Best regards plus the sender's first name if known. "
    "Never use the user's raw fragment as the entire body. "
    "Do not invent facts the user did not imply. Do not add a confidence score. "
    "Do not choose whether to ask or send."
)
_PREFERRED_FLASH = (
    DEFAULT_GEMINI_MODEL,
    "gemini-2.5-flash",
    DEFAULT_GEMINI_FALLBACK_MODEL,
    "gemini-2.0-flash",
)
_PREFERRED_LITE = (
    DEFAULT_GEMINI_FALLBACK_MODEL,
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-flash-lite-latest",
)
_BUSY_FLASH = frozenset(
    {DEFAULT_GEMINI_MODEL, "gemini-2.5-flash", "gemini-flash-latest"}
)
_ATTEMPTS = 2
_RETRY_SECONDS = 0.5
_RETRYABLE_CODES = frozenset({500, 502, 503})


class ExtractionError(Exception):
    """Gemini failed or returned output that must not be guessed into fields."""


class ExtractionUnavailable(ExtractionError):
    """No Gemini API key is configured, so the call must not be attempted."""


class ExtractionRateLimited(ExtractionError):
    """Gemini returned HTTP 429. The message is the type name, not the client text."""


def extract_email_fields(instruction: str, model_name: str | None = None) -> EmailExtraction:
    """Run one free-tier Gemini call, then polish subject and body.

    Persistent 404/429/500/502/503 errors fall back to local regex copy so
    the chat route still receives EmailExtraction instead of HTTP 429 or 502.
    A short topic is expanded into a titled subject and a complete email.
    Recipient addresses stay copy-only.
    """
    settings = load_settings()
    if not settings.gemini_api_key:
        raise ExtractionUnavailable("GEMINI_API_KEY is not set")
    model = (model_name or settings.gemini_model).strip() or DEFAULT_GEMINI_MODEL
    client = _gemini_client(settings.gemini_api_key)
    try:
        raw = _generate(client, model, instruction)
        fields = parse_extraction(raw, instruction)
    except ExtractionUnavailable:
        raise
    except (errors.APIError, ExtractionError) as exc:
        if _is_rate_failure(exc):
            logger.warning(
                "Gemini API rate limited (429); falling back to local heuristic extraction"
            )
            return local_regex_extract(instruction)
        if _is_not_found_failure(exc):
            logger.warning(
                "Gemini model not found (404); falling back to local heuristic extraction"
            )
            return local_regex_extract(instruction)
        if not _is_capacity_failure(exc):
            raise
        logger.warning("Gemini API unavailable; falling back to local heuristic extraction")
        return local_regex_extract(instruction)
    copied = apply_followup_slots(instruction, fields)
    return compose_missing_body(instruction, copied)


def parse_extraction(raw: str, instruction: str) -> EmailExtraction:
    """Keep a copied recipient. Subject and body may be drafted."""
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
        subject=_single_line(parsed.subject),
        body=_keep_body(parsed.body),
        recipient_mention=copied_mention(parsed.recipient_mention, instruction),
    )


def pick_flash_model(
    listed: Iterable[object],
    failed: str,
    *,
    prefer_lite: bool = False,
) -> str | None:
    """Choose a generateContent flash id from a ListModels page, skipping `failed`.

    Capacity spikes on standard flash skip those busy ids and prefer lite.
    """
    skip = {_normalize_model_id(failed)}
    if prefer_lite:
        skip.update(_BUSY_FLASH)
    usable: list[str] = []
    for item in listed:
        model_id = _usable_model_id(item, skip)
        if model_id is not None:
            usable.append(model_id)
    preferred = _PREFERRED_LITE if prefer_lite else _PREFERRED_FLASH
    for model_id in preferred:
        if model_id in usable:
            return model_id
    if prefer_lite:
        for model_id in usable:
            if "lite" in model_id.lower() and "flash" in model_id.lower():
                return model_id
    for model_id in usable:
        if prefer_lite and model_id in _BUSY_FLASH:
            continue
        if "flash" in model_id.lower():
            return model_id
    return None


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _generate(client: object, model: str, instruction: str) -> str:
    try:
        return _call_with_retries(client, model, instruction)
    except (ExtractionRateLimited, ExtractionError):
        raise
    except Exception as exc:
        fallback = _fallback_model(client, model, exc)
        logger.warning("Gemini model %s is unavailable; retrying with %s", model, fallback)
        try:
            return _call_with_retries(client, fallback, instruction)
        except (ExtractionRateLimited, ExtractionError):
            raise
        except Exception as retry_exc:
            _raise_mapped(retry_exc, fallback)


def _fallback_model(client: object, model: str, exc: Exception) -> str:
    mapped = _map_exception(exc)
    if mapped is not None:
        raise mapped from exc
    if not (_is_not_found(exc) or _is_retryable(exc)):
        _raise_mapped(exc, model)
    fallback = pick_flash_model(
        _list_models(client),
        failed=model,
        prefer_lite=_is_retryable(exc),
    )
    if fallback is None:
        reason = "model_not_found" if _is_not_found(exc) else type(exc).__name__
        _log_failure(model, exc)
        raise ExtractionError(reason) from exc
    return fallback


def _raise_mapped(exc: Exception, model: str) -> None:
    mapped = _map_exception(exc)
    if mapped is not None:
        raise mapped from exc
    _log_failure(model, exc)
    raise ExtractionError(type(exc).__name__) from exc


def _call_with_retries(client: object, model: str, instruction: str) -> str:
    """Retry 500/502/503 once. 404 and 429 leave this loop immediately."""
    for attempt in range(_ATTEMPTS):
        try:
            return _call(client, model, instruction)
        except ExtractionError:
            raise
        except Exception as exc:
            mapped = _map_exception(exc)
            if mapped is not None:
                raise mapped from exc
            if _is_not_found(exc) or not _is_retryable(exc) or attempt == _ATTEMPTS - 1:
                raise
            logger.warning(
                "Gemini retry %s/%s: %s model=%s code=%s",
                attempt + 1,
                _ATTEMPTS,
                type(exc).__name__,
                model,
                getattr(exc, "code", None),
            )
            _sleep(_RETRY_SECONDS)
    raise ExtractionError("retry_exhausted")


def _gemini_client(api_key: str) -> genai.Client:
    """One client per extraction. Timeouts and retries are capped so Render cannot hang."""
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=GEMINI_HTTP_TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=GEMINI_HTTP_RETRY_ATTEMPTS),
        ),
    )


def _call(client: object, model: str, instruction: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=instruction,
        config=_generation_config(),
    )
    text = response.text
    if not isinstance(text, str) or not text.strip():
        raise ExtractionError("empty_response")
    return text


def _list_models(client: object) -> list[object]:
    try:
        return list(client.models.list())
    except Exception as exc:
        logger.warning("Gemini model list failed: %s", type(exc).__name__)
        return []


def _generation_config() -> types.GenerateContentConfig:
    """JSON schema only. AFC stays off so generate_content is not treated as a tool call."""
    return types.GenerateContentConfig(
        system_instruction=_SYSTEM,
        temperature=0.4,
        max_output_tokens=1024,
        response_mime_type="application/json",
        response_schema=EmailExtraction,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        thinking_config=types.ThinkingConfig(
            include_thoughts=False,
            thinking_level=types.ThinkingLevel.LOW,
        ),
    )


def _usable_model_id(item: object, skip: set[str]) -> str | None:
    name = getattr(item, "name", None)
    if not isinstance(name, str):
        return None
    model_id = _normalize_model_id(name)
    lower = model_id.lower()
    if not lower.startswith("gemini") or model_id in skip:
        return None
    if any(part in lower for part in ("pro", "embed", "image", "tts", "robotics")):
        return None
    actions = getattr(item, "supported_actions", None) or ()
    if actions:
        normalized = {str(action).replace("_", "").lower() for action in actions}
        if "generatecontent" not in normalized:
            return None
    return model_id


def _normalize_model_id(value: str) -> str:
    text = value.strip()
    if "/models/" in text:
        text = text.rsplit("/models/", 1)[1]
    elif text.startswith("models/"):
        text = text[len("models/") :]
    return text


def _map_exception(exc: BaseException) -> ExtractionError | None:
    if _is_rate_limited(exc):
        return ExtractionRateLimited(type(exc).__name__)
    if _is_timeout(exc):
        return ExtractionError("timeout")
    return None


def _is_timeout(exc: BaseException) -> bool:
    """True for SDK/HTTP deadlines. Do not read the exception string."""
    code = getattr(exc, "code", None)
    if code in {408, 504}:
        return True
    return type(exc).__name__ in {
        "TimeoutException",
        "ReadTimeout",
        "ConnectTimeout",
        "ConnectTimeoutError",
        "DeadlineExceeded",
        "TimeoutError",
    }


def _is_retryable(exc: BaseException) -> bool:
    code = getattr(exc, "code", None)
    status = getattr(exc, "status", None)
    return code in _RETRYABLE_CODES or status in _RETRYABLE_CODES


def _is_capacity_failure(exc: BaseException) -> bool:
    """True for 500/502/503, including ExtractionError wrapping those codes."""
    if _is_retryable(exc):
        return True
    cause = exc.__cause__
    return cause is not None and cause is not exc and _is_capacity_failure(cause)


def _is_rate_limited(exc: BaseException) -> bool:
    """True only for HTTP 429. Do not read the exception string."""
    code = getattr(exc, "code", None)
    status = getattr(exc, "status", None)
    return code == 429 or status == 429


def _is_rate_failure(exc: BaseException) -> bool:
    """True for 429, including ExtractionRateLimited wrapping that code."""
    if isinstance(exc, ExtractionRateLimited) or _is_rate_limited(exc):
        return True
    cause = exc.__cause__
    return cause is not None and cause is not exc and _is_rate_failure(cause)


def _is_not_found(exc: BaseException) -> bool:
    code = getattr(exc, "code", None)
    if code is not None:
        return code == 404
    return getattr(exc, "status", None) in {404, "NOT_FOUND"}


def _is_not_found_failure(exc: BaseException) -> bool:
    """True for HTTP 404, including ExtractionError wrapping that code."""
    if _is_not_found(exc):
        return True
    cause = exc.__cause__
    return cause is not None and cause is not exc and _is_not_found_failure(cause)


def _log_failure(model: str, exc: BaseException) -> None:
    """Log the model id and exception type. Provider text can include the API key."""
    logger.warning(
        "Gemini request failed: %s model=%s code=%s",
        type(exc).__name__,
        model,
        getattr(exc, "code", None),
    )


def _load_object(raw: str) -> dict[str, object]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtractionError("unparseable") from exc
    if not isinstance(payload, dict):
        raise ExtractionError("unparseable")
    return payload


def _stated_address(value: str | None, instruction: str) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    if not cleaned or "@" not in cleaned:
        return None
    if _folded(cleaned) not in _folded(instruction):
        return None
    return cleaned


def _single_line(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _keep_body(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    lines = [line.rstrip() for line in value.strip().splitlines()]
    cleaned = "\n".join(lines).strip()
    return cleaned or None


def _folded(value: str) -> str:
    return " ".join(value.split()).lower()
