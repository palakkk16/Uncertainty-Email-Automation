"""One Gemini API call that copies the recipient and drafts subject and body.

The client lives here so tests can replace `google.genai` without touching
the route. This module does not decide ASK vs SEND and does not send mail.
At most two stable Flash models are tried, with a 6s wall-clock budget.
Preview, experimental, and known-dead ids are never called.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections.abc import Iterable

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.config import (
    DEFAULT_GEMINI_FALLBACK_MODEL,
    DEFAULT_GEMINI_MODEL,
    GEMINI_EXTRACT_BUDGET_S,
    GEMINI_HTTP_RETRY_ATTEMPTS,
    GEMINI_HTTP_TIMEOUT_MS,
    GEMINI_MAX_MODELS,
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
    "gemini-1.5-flash",
)
_PREFERRED_LITE = (
    DEFAULT_GEMINI_FALLBACK_MODEL,
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash-lite",
)
_BUSY_FLASH = frozenset(
    {DEFAULT_GEMINI_MODEL, "gemini-2.5-flash", "gemini-flash-latest"}
)
_STABLE_MODELS = (DEFAULT_GEMINI_MODEL, DEFAULT_GEMINI_FALLBACK_MODEL)
_BLOCKED_MARKERS = (
    "preview",
    "exp",
    "2.5-flash-lite",
    "flash-lite-latest",
    "gemini-3.1",
    "gemini-3.5",
)
_MIN_CALL_TIMEOUT_MS = 500
_CACHE_LOCK = threading.Lock()
_working_model: str | None = None
_unavailable: set[str] = set()


class ExtractionError(Exception):
    """Gemini failed or returned output that must not be guessed into fields."""


class ExtractionUnavailable(ExtractionError):
    """No Gemini API key is configured, so the call must not be attempted."""


class ExtractionRateLimited(ExtractionError):
    """Gemini returned HTTP 429. The message is the type name, not the client text."""


def reset_model_cache() -> None:
    """Drop the working model id. Tests isolate each case this way."""
    global _working_model
    with _CACHE_LOCK:
        _working_model = None
        _unavailable.clear()


def extract_email_fields(instruction: str, model_name: str | None = None) -> EmailExtraction:
    """Run at most two Gemini calls, then polish subject and body.

    Any API, parse, timeout, 404, 429, or 5xx failure — or a 6s budget miss —
    falls back to local regex copy so POST /chat still receives EmailExtraction.
    A missing API key stays ExtractionUnavailable. Recipient addresses stay copy-only.
    """
    settings = load_settings()
    if not settings.gemini_api_key:
        raise ExtractionUnavailable("GEMINI_API_KEY is not set")
    deadline = time.monotonic() + GEMINI_EXTRACT_BUDGET_S
    try:
        raw = _generate(settings.gemini_api_key, instruction, deadline)
        fields = parse_extraction(raw, instruction)
    except ExtractionUnavailable:
        raise
    except Exception as exc:
        _log_local_fallback(exc)
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


def _generate(api_key: str, instruction: str, deadline: float) -> str:
    last_exc: Exception | None = None
    remaining = _model_candidates()
    for index, candidate in enumerate(remaining):
        timeout_ms = _call_timeout_ms(deadline)
        if timeout_ms is None:
            raise ExtractionError("budget")
        try:
            text = _call(_gemini_client(api_key, timeout_ms), candidate, instruction)
        except Exception as exc:
            last_exc = exc
            _log_failure(candidate, exc)
            if _is_not_found(exc) or _is_not_found_failure(exc):
                _mark_unavailable(candidate)
            nxt = remaining[index + 1] if index + 1 < len(remaining) else "local heuristic"
            logger.warning(
                "Gemini model %s failed once; moving on to %s",
                candidate,
                nxt,
            )
            continue
        _remember_working(candidate)
        return text
    if isinstance(last_exc, ExtractionError):
        raise last_exc
    if last_exc is not None:
        mapped = _map_exception(last_exc)
        if mapped is not None:
            raise mapped from last_exc
        raise ExtractionError(type(last_exc).__name__) from last_exc
    raise ExtractionError("model_not_found")


def _model_candidates() -> list[str]:
    """At most two stable Flash ids. Working cache first, then flash-latest."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add(model_id: str | None) -> None:
        if not model_id:
            return
        mid = _normalize_model_id(model_id)
        if (
            not mid
            or mid in seen
            or _is_unavailable(mid)
            or _is_blocked_model(mid)
        ):
            return
        seen.add(mid)
        ordered.append(mid)

    add(_peek_working())
    for model_id in _STABLE_MODELS:
        add(model_id)
    return ordered[:GEMINI_MAX_MODELS]


def _is_blocked_model(model_id: str) -> bool:
    lower = model_id.lower()
    return any(marker in lower for marker in _BLOCKED_MARKERS)


def _call_timeout_ms(deadline: float) -> int | None:
    remaining_ms = int((deadline - time.monotonic()) * 1000)
    if remaining_ms < _MIN_CALL_TIMEOUT_MS:
        return None
    return min(GEMINI_HTTP_TIMEOUT_MS, remaining_ms)


def _gemini_client(api_key: str, timeout_ms: int = GEMINI_HTTP_TIMEOUT_MS) -> genai.Client:
    """One client per model attempt. Timeouts are capped so Render cannot hang."""
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            api_version="v1beta",
            timeout=timeout_ms,
            retry_options=types.HttpRetryOptions(attempts=GEMINI_HTTP_RETRY_ATTEMPTS),
        ),
    )


def _call(client: object, model: str, instruction: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=instruction,
        config=_generation_config(model),
    )
    text = response.text
    if not isinstance(text, str) or not text.strip():
        raise ExtractionError("empty_response")
    return text


def _peek_working() -> str | None:
    with _CACHE_LOCK:
        return _working_model


def _remember_working(model_id: str) -> None:
    global _working_model
    with _CACHE_LOCK:
        _working_model = model_id


def _is_unavailable(model_id: str) -> bool:
    with _CACHE_LOCK:
        return model_id in _unavailable


def _mark_unavailable(model_id: str) -> None:
    global _working_model
    with _CACHE_LOCK:
        _unavailable.add(model_id)
        if _working_model == model_id:
            _working_model = None


def _generation_config(model: str) -> types.GenerateContentConfig:
    """JSON schema only. AFC stays off so generate_content is not treated as a tool call."""
    config: dict[str, object] = {
        "system_instruction": _SYSTEM,
        "temperature": 0.4,
        "max_output_tokens": 1024,
        "response_mime_type": "application/json",
        "response_schema": EmailExtraction,
        "automatic_function_calling": types.AutomaticFunctionCallingConfig(
            disable=True
        ),
    }
    model_id = _normalize_model_id(model)
    if model_id.startswith(("gemini-2.5", "gemini-3")):
        config["thinking_config"] = types.ThinkingConfig(
            include_thoughts=False,
            thinking_level=types.ThinkingLevel.LOW,
        )
    return types.GenerateContentConfig(**config)


def _usable_model_id(item: object, skip: set[str]) -> str | None:
    name = getattr(item, "name", None)
    if not isinstance(name, str):
        return None
    model_id = _normalize_model_id(name)
    lower = model_id.lower()
    if not lower.startswith("gemini") or model_id in skip:
        return None
    if any(part in lower for part in ("embed", "image", "tts", "robotics")):
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
        "Gemini request failed: %s model=%s code=%s status=%s",
        type(exc).__name__,
        model,
        getattr(exc, "code", None),
        getattr(exc, "status", None),
    )


def _log_local_fallback(exc: BaseException) -> None:
    if _is_rate_failure(exc):
        logger.warning(
            "Gemini API rate limited (429); falling back to local heuristic extraction"
        )
        return
    if _is_not_found_failure(exc):
        logger.warning(
            "Gemini model not found (404); falling back to local heuristic extraction"
        )
        return
    logger.warning(
        "Gemini extraction failed: %s; falling back to local heuristic extraction",
        type(exc).__name__,
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
