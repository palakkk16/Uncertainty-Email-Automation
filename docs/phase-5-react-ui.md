# Phase 5 — React chat UI

A local page for one email instruction at a time. Each check is a `POST /chat` to the Phase 4 API. The page shows the clarification question when the decision is `ASK`, and a confirmation when the decision is `SEND`. Gmail is not called. There is no button and no code path that sends mail. `scripts/gmail_send_test.py` is not imported.

The decision layer is unchanged. The browser talks only to the Vite dev server. That server proxies `/chat` and `/health` to the API, so the page stays on one origin and the API does not enable CORS.

## Run

Start the API first, from the repo root:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8741
```

Then install and start the UI, also from the repo root:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Open [http://127.0.0.1:43123](http://127.0.0.1:43123). The dev server binds `127.0.0.1` on port `43123`.

`POST /chat` still needs `GEMINI_API_KEY` in the environment or `.env`. A missing key or a Gemini failure is an error on the page. It does not send mail.

## Proxy

| Browser request | Upstream |
| --- | --- |
| `POST /chat` | `http://127.0.0.1:8741/chat` |
| `GET /health` | `http://127.0.0.1:8741/health` |

The page does not call port 8741 directly.

## What you see

The transcript lives in the browser. The API is stateless, and a copied field is kept only when that text is in the one message string. On each check the page posts the concatenation of every user turn, separated by newlines. Assistant text is not included, so a follow-up such as an email address sits in the same instruction as the original request. If that string would be longer than 4000 characters, the page shows an error and does not post. The draft stays in the box.

`ASK`: the assistant bubble is the clarification question (for example `What is Rahul's email address?`).

`SEND`: the assistant turn shows recipient, subject, and body, and the sentence `The decision is SEND. No email was sent.` That confirmation means the threshold is satisfied. The message did not leave the machine.

Empty: a short prompt to type an email instruction. Loading: the box is disabled while the check is in flight. An error replaces any confirmation for that check. The draft is kept. A failed check never draws a SEND card.

## Errors

`POST /chat` returns HTTP 429 when the Gemini client error status is 429. The detail is `Gemini rate limit.` It does not include the API key, the request URL, or the exception text. Other Gemini failures stay 502. A missing key stays 503.

| Condition | Copy |
| --- | --- |
| HTTP 429 | Gemini rate limit. Wait and try again. |
| HTTP 502 or 503 | Extraction failed. Try again. |
| The request cannot reach the API | Cannot reach the API. |
| Stitched instruction over 4000 characters | That would make the instruction longer than 4000 characters. Shorten it and try again. |

HTTP 422 (empty or oversized message) is also an error, not a SEND confirmation.

## What this phase does not do

- No Gmail send, and no import of `scripts/gmail_send_test.py`
- No change to the slot-sufficiency threshold
- No evaluation dataset
- No auth, no database, and no paid service
