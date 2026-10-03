# Phase 3 — Gemini structured field extraction

Phase 4 replaces the response contract below. This page records the copy-only extraction Phase 3 added. Current `POST /chat` behavior is in [phase-4-decision-layer.md](phase-4-decision-layer.md).

`POST /chat` makes one Gemini API call and copies `recipient`, `subject`, and `body` from the instruction. A field the instruction does not state is `null`. In Phase 3, `decision` stayed `null`.

This phase does not decide ASK versus SEND.

## Model and cost

The default model id is `gemini-3.8-flash`.

That id is a Flash model on the [Gemini API free tier](https://ai.google.dev/gemini-api/docs/pricing) (Google AI Studio). Standard input and output are free of charge on that tier, with rate limits. It is not a Pro model.

- One `generateContent` call per `POST /chat`
- Gemini API with an API key, not Vertex AI
- No paid model and no billing account required for this call
- Do not change `GEMINI_MODEL` to a Pro or paid-only id

The Python package is `google-genai` (`import google.genai`). The legacy `google-generativeai` package is not used.

## Environment

| Variable | Role |
| --- | --- |
| `GEMINI_API_KEY` | Google AI Studio key. Required for `POST /chat`. Never log it. |
| `GEMINI_MODEL` | Optional. Defaults to `gemini-3.8-flash`. |

`GET /health` does not need the key. If the key is missing, `POST /chat` returns **503** and does not guess fields. If Gemini returns an error or the output is not the expected JSON object, `POST /chat` returns **502** and does not guess fields. Neither error body includes the key.

## Request and response

`POST /chat`

```json
{"message": "Send an email to rahul@example.com with subject Lab meeting and body Tomorrow at 10 AM"}
```

`message` is required. It is trimmed, then it must be 1 to 4000 characters. Empty or whitespace-only text returns **422** and does not call Gemini.

**200**

```json
{
  "reply": "Extracted recipient, subject, and body. Missing none. The ASK vs SEND decision is not implemented.",
  "phase": "gemini_extraction",
  "decision": null,
  "extraction": {
    "recipient": "rahul@example.com",
    "subject": "Lab meeting",
    "body": "Tomorrow at 10 AM"
  }
}
```

`reply` lists which of `recipient`, `subject`, and `body` were extracted and which are missing, and states that the ASK vs SEND decision is not implemented.

`recipient` is an email address only when that address appears in the instruction. A name such as "Rahul" is not an address, and an address the model adds is discarded. `subject` and `body` are kept only when that text appears in the instruction. The model is not asked for a confidence score.

`decision` is always `null` in this phase.

## What this phase does not do

- No ASK vs SEND decision
- No uncertainty score, entropy, or confidence score
- No clarification question
- No Gmail send, and no import of `scripts/gmail_send_test.py`
- No Vertex AI
- No paid Gemini model
- No React UI
- No database

Phase 1 (`python scripts/gmail_send_test.py`) is still the only path that can send mail. The API never calls it.
