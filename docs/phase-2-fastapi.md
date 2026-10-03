# Phase 2 — FastAPI chat core

Phase 3 replaced the `fastapi_core` response, and Phase 4 replaced that response again. This page records what Phase 2 shipped: request validation, `GET /health`, and `decision: null`. Current `POST /chat` behavior is in [phase-4-decision-layer.md](phase-4-decision-layer.md).

This phase accepts one instruction over HTTP and answers that it was received. It does not decide whether to ask a follow-up or send an email.

## Run

From the project root, with the virtualenv from the README:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8741
```

`APP_HOST` defaults to `127.0.0.1` and `APP_PORT` defaults to `8741`. The process reads those variables at startup (from the environment or `.env`) and exits if the host is empty or the port is not an integer from 1 to 65535. No API key is required. Keep the uvicorn `--host` and `--port` flags aligned with those values.

- Health: [http://127.0.0.1:8741/health](http://127.0.0.1:8741/health)
- OpenAPI: [http://127.0.0.1:8741/docs](http://127.0.0.1:8741/docs)

Tests do not need a live server:

```bash
pytest
```

## Request and response

`POST /chat`

```json
{"message": "Email the lab that the Friday draft is ready."}
```

`message` is required. It is trimmed, then it must be 1 to 4000 characters. Empty or whitespace-only text returns **422**. A trimmed message longer than 4000 characters returns **422**.

**200**

```json
{
  "reply": "Received your message. Parameter extraction and the ASK vs SEND decision are not implemented yet.",
  "phase": "fastapi_core",
  "decision": null
}
```

`decision` is always `null` in this phase.

`GET /health` returns `{"status": "ok"}`.

## What this phase does not do

- No Gemini, and no other language-model call
- No parameter extraction
- No uncertainty score
- No ASK vs SEND decision
- No Gmail send, and no import of `scripts/gmail_send_test.py`
- No React UI
- No database

Phase 1 (`python scripts/gmail_send_test.py`) is unchanged and is still the only path that can send mail. The API never calls it.
