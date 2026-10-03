# UNCERTAIN-EMAIL

How can an AI agent decide when to send an email versus ask for clarification? A language model copies fields from the instruction, Python applies a slot-sufficiency threshold, and the Gmail API runs only from `scripts/gmail_send_test.py`. The threshold sends only when recipient, subject, and body are all resolved. `resolved_fraction` is a completeness ratio (resolved slots / 3), not a calibrated probability. Semantic entropy and information-gain clarification are still open. Phase 1 is the desktop OAuth send script. The API does not send mail.

**Phase 1 status:** the send script and the Google Cloud click-path are in the repo. A real send still needs your own OAuth client JSON and a filled-in `.env`. No credentials are stored here.

**Phase 2 status:** the FastAPI core is in place (`GET /health`, `POST /chat` validation). The Phase 2 ack (`phase: "fastapi_core"`, `decision: null`) is replaced by later phases. See [docs/phase-2-fastapi.md](docs/phase-2-fastapi.md).

**Phase 3 status:** `POST /chat` makes one Gemini API free-tier call and copies `recipient`, `subject`, `body`, and an optional `recipient_mention`. A field the instruction does not contain is null. The model is not asked for a confidence score. See [docs/phase-3-gemini-extraction.md](docs/phase-3-gemini-extraction.md).

**Phase 4 status:** Python applies a slot-sufficiency threshold and returns `decision` `ASK` or `SEND`. `phase` is `"decision_layer"`. `resolved_fraction` counts resolved required slots over 3. It is not a calibrated uncertainty model, not semantic entropy, and not an LLM confidence score. A SEND decision does not call Gmail. See [docs/phase-4-decision-layer.md](docs/phase-4-decision-layer.md).

**Phase 5 status:** the React chat UI is in `frontend/`. Each check posts the user turns to `POST /chat` through a same-origin proxy. `ASK` shows the clarification question. `SEND` shows recipient, subject, and body, and states that no email was sent. The page does not call Gmail. See [docs/phase-5-react-ui.md](docs/phase-5-react-ui.md).

**Phase 6 status:** an offline dataset in `eval/dataset.json` compares the slot-sufficiency threshold with a gap-filling baseline. The baseline always records a send on an in-memory sink. It does not call Gmail. The eval does not call Gemini, and it does not measure semantic entropy or calibrated uncertainty. See [docs/phase-6-evaluation.md](docs/phase-6-evaluation.md).

Cost: one free-tier Gemini call per `POST /chat`. The default model is `gemini-3.8-flash` on the Gemini API (Google AI Studio). No Vertex AI and no paid model.

## Keep this at $0

Do not attach a billing account to the Google Cloud project. Leave the OAuth consent screen in **Testing**, add your own Gmail address as a test user, and enable **only** the Gmail API. A personal Gmail API test send does not require billing. Attaching a billing account, enabling other Google APIs (for example Vertex AI or Maps), or publishing the consent screen is outside this project and can create charges or an app-verification process. Every library in `requirements.txt` is free. This phase calls no paid API.

Refresh tokens issued while the app stays in Testing expire after 7 days. Delete `credentials/token.json` and run the script again to sign in. Do not publish the app to lengthen the token.

## Run

Use Python 3.10 or newer from the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`, following [docs/phase-1-gmail-setup.md](docs/phase-1-gmail-setup.md), then:

```bash
python scripts/gmail_send_test.py
```

If a required variable or the client-secret file is missing, the script exits with an error and does not send. On success it prints the Gmail message id only.

Phase 4 API (copies fields, chooses ASK or SEND in Python, does not send mail):

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8741
pytest
```

Phase 6 eval (offline; does not call Gemini and does not send mail):

```bash
python -m eval.run
pytest
```

`python -m eval.run` prints the metrics and writes `docs/phase-6-evaluation.md`. `pytest` stays offline: `tests/conftest.py` sets a placeholder `GEMINI_API_KEY` when none is set, and the chat tests replace the SDK client.

Phase 5 UI (talks to that API, does not send mail). Start the API first, then:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

The page is at [http://127.0.0.1:43123](http://127.0.0.1:43123). Vite proxies `/chat` and `/health` to `http://127.0.0.1:8741`. See [docs/phase-5-react-ui.md](docs/phase-5-react-ui.md).

`POST /chat` needs `GEMINI_API_KEY` in the environment or `.env`. `GEMINI_MODEL` defaults to the free-tier id `gemini-3.8-flash`. A missing key or a Gemini failure returns an error and does not send mail. The chat page does not send mail either.
