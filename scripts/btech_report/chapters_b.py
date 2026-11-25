"""Chapters 4–7, appendix, and IEEE bibliography."""

from __future__ import annotations

from pathlib import Path

from scripts.btech_report.docx_utils import (
    add_picture,
    body,
    bullet,
    caption_figure,
    caption_table,
    chapter,
    left,
    make_table,
    numbered,
    run,
    section_heading,
    subsection,
)

ASSETS = Path(__file__).resolve().parents[2] / "docs" / "report_assets"


def add_chapter_4(doc) -> None:
    chapter(doc, 4, "Implementation, Testing, and Maintenance")
    section_heading(doc, "4.1 Introduction to Languages, IDEs, Tools and Technologies Used")
    body(
        doc,
        "The implementation language on the server is Python 3.10+. The web framework is FastAPI "
        "0.141.1 on Starlette 1.7.0, served by Uvicorn 0.54.0. Request and response bodies are "
        "Pydantic v2 models in strict mode so a number cannot be coerced into an email address. "
        "Blocking Gemini and Gmail I/O is wrapped in starlette.concurrency.run_in_threadpool. "
        "The Gemini client is google-genai 2.25.0 with HttpOptions api_version=v1beta. Gmail uses "
        "google-api-python-client and google-auth. Tests use pytest 9.1.1 with FastAPI’s TestClient. "
        "The IDE used throughout development is Cursor.",
    )
    body(
        doc,
        "The browser application is TypeScript on React 19.2.8, bundled by Vite 8.3.0, linted with "
        "oxlint, and hosted as a static SPA on Vercel (vercel.json rewrites every path to "
        "index.html). Google Identity Services loads accounts.google.com/gsi/client. The Gmail "
        "token client requests only https://www.googleapis.com/auth/gmail.send.",
    )
    caption_table(doc, "4.1", "Pinned technologies used in the submitted tree")
    make_table(
        doc,
        ["Layer", "Technology", "Pinned version / note"],
        [
            ["API", "FastAPI / Uvicorn", "0.141.1 / 0.54.0"],
            ["Validation", "Pydantic", "2.13.5 strict models"],
            ["LLM", "google-genai", "2.25.0; gemini-flash-latest, gemini-2.0-flash"],
            ["Mail", "Gmail API", "gmail.send scope, users.messages.send"],
            ["Auth", "GIS + PBKDF2-SHA256", "200 000 iterations, 16-byte salt"],
            ["UI", "React + Vite", "19.2.8 / 8.3.0"],
            ["Hosting", "Render + Vercel", "API + SPA"],
            ["Tests", "pytest", "9.1.1, 147 collected tests"],
            ["Monitor", "UptimeRobot", "HEAD /health every 5 minutes"],
        ],
    )

    section_heading(doc, "4.2 Testing Techniques and Test Plans")
    body(
        doc,
        "The test plan is automated, offline, and secret-free. tests/conftest.py injects a "
        "placeholder GEMINI_API_KEY so a missing .env cannot leak a real key into CI. Chat tests "
        "replace the Gemini client and the Gmail sender. Dispatch tests never open a browser. The "
        "suite was collected at 147 tests, all passing at the time of this report. Techniques in "
        "use are: unit tests of decide() and compose(); contract tests of POST /chat; negative "
        "tests of 404/429/503/timeout fallback; security tests that hashes are stored rather than "
        "passwords and that exception text is not copied to clients; and an evaluation test that "
        "recomputes the Phase-6 metrics independently of the written note.",
    )
    caption_table(doc, "4.2", "Collected pytest tests by file (147 total)")
    make_table(
        doc,
        ["File", "Concern", "Examples of behaviour"],
        [
            ["tests/test_extraction.py", "Gemini budget, heuristic, dates", "6 s cap, 2 models, vacation follow-up, 5 Dec–8 Dec"],
            ["tests/test_decision.py", "ASK/SEND threshold", "bare name, two addresses, no repeat subject question"],
            ["tests/test_chat.py", "HTTP contract + dispatch", "HEAD /health, 35 s path, duplicate send, Gmail 401"],
            ["tests/test_dispatch.py", "CORS, tokens, guard", "wildcard CORS refused, user token required"],
            ["tests/test_auth.py", "GIS + password", "401 invalid, 409 duplicate, hash not plaintext"],
            ["tests/test_eval.py", "18-case offline eval", "12/12 prevented misfires, 18/18 task success"],
        ],
    )
    caption_table(doc, "4.3", "Representative black-box test cases")
    make_table(
        doc,
        ["TC", "Input", "Expected", "Result"],
        [
            ["TC-01", "Full address + topic", "SEND, titled subject, full body", "Pass"],
            ["TC-02", "Bare name Rahul", "ASK for Rahul’s email address", "Pass"],
            ["TC-03", "Two addresses", "ASK which address", "Pass"],
            ["TC-04", "Address only, then “permission to go on vacation”", "One subject question, then SEND", "Pass"],
            ["TC-05", "Leave from 5 dec to 8 dec", "Dates in subject and body", "Pass"],
            ["TC-06", "Gemini 503 on both models", "HTTP 200, local heuristic", "Pass"],
            ["TC-07", "Same SEND twice in 600 s", "dispatch.status already_sent", "Pass"],
            ["TC-08", "APP_REQUIRE_USER_GMAIL_TOKEN, no header", "HTTP 403 Connect Gmail", "Pass"],
            ["TC-09", "Unknown password", "HTTP 401, generic copy", "Pass"],
            ["TC-10", "Empty / whitespace message", "HTTP 422, Gemini not called", "Pass"],
        ],
    )
    caption_table(doc, "4.4", "Offline evaluation against the gap-filling baseline (eval/dataset.json)")
    make_table(
        doc,
        ["Metric", "Value"],
        [
            ["Cases (complete / partial / ambiguous)", "18 (6 / 6 / 6)"],
            ["Task success (proposed = gold)", "18/18 (1.0000)"],
            ["Incorrect execution, baseline", "12/18 (0.6667)"],
            ["Incorrect execution, proposed", "0/18 (0.0000)"],
            ["Prevented misfires among gold ASK", "12/12 (1.0000)"],
            ["Clarification accuracy among gold ASK", "12/12 (1.0000)"],
            ["Over-clarification among gold SEND", "0/6 (0.0000)"],
            ["Average clarification turns (single-shot)", "1.0000"],
        ],
    )
    body(
        doc,
        "Maintenance: UptimeRobot hits HEAD /health every five minutes. A failing probe is an "
        "operator signal, not an automatic send. Model identifiers that 404 are cached as "
        "unavailable for the process lifetime so Render does not walk a dead list. Working model "
        "ids are cached so the next request starts on a known-good Flash model. Logs record "
        "exception types, never tokens, passwords, or draft bodies.",
    )

    section_heading(doc, "4.3 Installation Instructions")
    numbered(doc, "Clone the repository and create a Python 3.10+ virtual environment.")
    numbered(doc, "pip install -r requirements.txt")
    numbered(doc, "Copy .env.example to .env. Set GEMINI_API_KEY, APP_GOOGLE_CLIENT_ID, GMAIL_SENDER, TOKEN_PATH as required.")
    numbered(doc, "uvicorn app.main:app --host 127.0.0.1 --port 8741")
    numbered(doc, "npm --prefix frontend install && npm --prefix frontend run dev  (http://127.0.0.1:43123)")
    numbered(doc, "pytest  — expect 147 passed.")
    numbered(doc, "Production: set APP_DISPATCH_ENABLED=true, APP_REQUIRE_USER_GMAIL_TOKEN=true, APP_CORS_ORIGINS to the Vercel origin, VITE_API_BASE_URL to the Render origin.")
    numbered(doc, "Optional: python -m eval.run writes docs/phase-6-evaluation.md without calling Gemini or Gmail.")

    section_heading(doc, "4.4 End User Instructions")
    numbered(doc, "Open https://uncertainty-email-automation.vercel.app")
    numbered(doc, "Sign in with Google or with a seeded demo account (for example palak@gmail.com) or register a new email/password pair.")
    numbered(doc, "Click Connect Gmail to Send and approve the gmail.send scope if live dispatch is enabled.")
    numbered(doc, "On Compose Agent, describe the email in ordinary English. Press Enter or Check.")
    numbered(doc, "If the agent asks a question (address, subject, or body), answer in the next turn. It will not ask the same question twice.")
    numbered(doc, "When the decision is SEND, read the draft. The audit log records SENT or PREVIEW.")
    numbered(doc, "Sign Out clears the session, Gmail token, and in-memory thread.")


def add_chapter_5(doc, figs: dict) -> None:
    chapter(doc, 5, "Results and Discussions")
    section_heading(doc, "5.1 User Interface Representation")
    body(
        doc,
        "The workspace is a two-pane SaaS shell. The sidebar shows the UNCERTAIN-EMAIL brand, "
        "navigation to Compose Agent and Sent & Audit Log, the signed-in name and email, the "
        "Connect Gmail control, and Sign Out. The main pane is a paper sheet with the product "
        "palette (navy, cream, maroon accent) documented in the frontend CSS. Login is a split "
        "layout: product copy on one side, GIS button plus email/password tabs on the other. "
        "Compose uses a transcript of user and assistant turns, a 4000-character meter, and a "
        "Check button that disables while loading. After a delivered SEND, a New email bar resets "
        "the thread without losing the audit row.",
    )

    section_heading(doc, "5.2 Brief Description of Various Modules of the System")
    body(
        doc,
        "Authentication module. POST /auth/google verifies a GIS ID token against "
        "APP_GOOGLE_CLIENT_ID. POST /auth/login and POST /auth/register use the JSON user store. "
        "Invalid logins return the same 401 copy so account enumeration is not trivial.",
    )
    body(
        doc,
        "Extraction module. gemini.py owns the circuit breaker and model cache. heuristic.py copies "
        "addresses and names with regular expressions and binds a last-line follow-up to the open "
        "slot. compose.py titles subjects, drafts Gmail-style bodies, greets with a plausible first "
        "name rather than the raw local-part, signs with APP_SIGNER_NAME, and injects date/time "
        "clauses extracted from the topic.",
    )
    body(
        doc,
        "Decision module. sufficiency.py is the only place that may set decision. It infers the "
        "last question from prior user text because the client does not post assistant turns.",
    )
    body(
        doc,
        "Dispatch module. Dispatcher checks the optional allow-list, claims a SHA-256 key, and "
        "calls GmailSender. Failures release the claim so a retry is possible. Gmail 401 on a user "
        "token maps to Reconnect Gmail.",
    )
    body(
        doc,
        "Frontend module. useChat.ts stitches user turns, aborts at 35 s, and records audit "
        "entries. gmailToken.ts scopes sessionStorage by email so a second Google account on the "
        "same browser does not reuse the previous access token.",
    )
    caption_table(doc, "5.1", "HTTP routes actually mounted by create_app()")
    make_table(
        doc,
        ["Method", "Path", "Auth", "Purpose"],
        [
            ["POST", "/chat", "none; optional X-Gmail-Token", "Extract, decide, maybe send"],
            ["GET, HEAD", "/health", "public", "Liveness for UptimeRobot"],
            ["GET", "/health/config", "public", "Dispatch mode, no secrets"],
            ["POST", "/auth/google", "GIS credential", "Verify ID token, return profile"],
            ["POST", "/auth/login", "email+password", "Verify PBKDF2 hash"],
            ["POST", "/auth/register", "name+email+password", "Create hash; 409 on duplicate"],
        ],
    )

    section_heading(doc, "5.3 Snapshots of the System with Brief Detail of Each")
    body(
        doc,
        "Live screenshots should be pasted into the bordered frames below before hard-binding. "
        "Each figure corresponds to a route a faculty examiner can open on Vercel without a local "
        "build.",
    )
    add_picture(doc, figs["ui1"], 150)
    caption_figure(doc, "5.1", "Login page — Google Identity Services button and email/password form")
    body(
        doc,
        "Figure 5.1 is the unauthenticated shell. GIS is initialised with auto_select false and "
        "popup UX. If VITE_GOOGLE_CLIENT_ID is missing, the page still offers email/password so a "
        "demo is not blocked on OAuth configuration.",
    )
    add_picture(doc, figs["ui2"], 150)
    caption_figure(doc, "5.2", "Compose Agent — instruction box, Check control, and conversation transcript")
    body(
        doc,
        "Figure 5.2 is the primary workspace. Placeholder copy asks who the mail is for and what "
        "it should say. Shift+Enter inserts a line; Enter submits.",
    )
    add_picture(doc, figs["ui3"], 150)
    caption_figure(doc, "5.3", "ASK turn — agent requesting a missing subject after an address-only prompt")
    body(
        doc,
        "Figure 5.3 documents the uncertainty policy in the UI. The assistant message is the "
        "clarification string from decide(), not a free-form chat completion.",
    )
    add_picture(doc, figs["ui4"], 150)
    caption_figure(doc, "5.4", "SEND confirmation — recipient, titled subject, drafted body, dispatch status")
    body(
        doc,
        "Figure 5.4 is shown when all three slots resolve. If dispatch is disabled the copy states "
        "that no email was sent. If Gmail accepts the raw message, the reply names the recipient.",
    )
    add_picture(doc, figs["ui5"], 150)
    caption_figure(doc, "5.5", "Sent & Audit Log — timestamp, recipient, subject, status, clarification turns")
    body(
        doc,
        "Figure 5.5 is the examiner-facing accountability view. Clarification turns count ASK "
        "questions before the agent acted. Clear History wipes only this browser’s localStorage array.",
    )

    section_heading(doc, "5.4 Back-End Representation")
    body(
        doc,
        "The back end is a single FastAPI process. It does not run PostgreSQL, Redis, or Celery. "
        "Gemini and Gmail are remote APIs. Local durability is data/users.json. Configuration is "
        "fail-fast at startup for APP_PORT, CORS, and an enabled-but-unsafe dispatch setup. A "
        "missing Gemini key does not prevent /health; it fails POST /chat with 503 rather than "
        "inventing fields. Render should set APP_REQUIRE_USER_GMAIL_TOKEN=true so a public bind "
        "cannot send from credentials/token.json.",
    )

    section_heading(doc, "5.5 Snapshots of Database Tables with Brief Description")
    body(
        doc,
        "Because the physical stores are JSON documents rather than pgAdmin tables, the snapshots "
        "below are the record shapes an examiner will find on disk and in DevTools. They match "
        "Chapter 3.4 exactly.",
    )
    caption_table(doc, "5.2", "Physical USER document in data/users.json (secrets redacted)")
    make_table(
        doc,
        ["JSON field", "Example (redacted)", "Description"],
        [
            ["email", "palak@gmail.com", "Lowercased primary key"],
            ["name", "Palak", "Sidebar display name"],
            ["password", "pbkdf2_sha256$200000$<salt>$<digest>", "Never the login password"],
        ],
    )
    body(
        doc,
        "SESSION in localStorage is {name, email, picture}. GMAIL_TOKEN in sessionStorage is "
        "{accessToken, expiresAt, email} under uncertain-email-gmail:<email>. AUDIT_ENTRY rows "
        "are {id, timestamp, recipient, subject, bodyPreview, status, clarificationTurns}. "
        "DISPATCH_CLAIM has no file snapshot; it is a dict of hex digests to monotonic timestamps "
        "inside DuplicateGuard. These four snapshots, together with the ER diagram, are the "
        "database documentation of the submitted system.",
    )


def add_chapter_6(doc) -> None:
    chapter(doc, 6, "Summary and Conclusions")
    body(
        doc,
        "This Project-1 report presented the design and implementation of an uncertainty-aware "
        "multi-user email automation system. The motivating failure is an LLM that treats a "
        "fluent draft as a licence to send. The response is a hybrid architecture: Gemini Flash "
        "copies and drafts under a six-second, two-model circuit breaker; a local heuristic "
        "guarantees availability; Python, not the model, chooses ASK or SEND; Gmail runs only "
        "after SEND, only with OAuth, and only once per digest in ten minutes.",
    )
    body(
        doc,
        "The implementation is complete enough to demonstrate on faculty hardware. The UI is on "
        "Vercel; the API is on Render; 147 pytest tests passed; an eighteen-case offline "
        "evaluation reported 18/18 task success and 12/12 prevented misfires against a baseline "
        "that always records a send. Dates such as “from 5 Dec to 8 Dec” survive into both "
        "subject and body. A topic reply after “What subject should I use?” fills subject and "
        "body together so the same question is not asked twice.",
    )
    body(
        doc,
        "The limits are stated rather than hidden. resolved_fraction is not a probability. The "
        "offline eval does not call Gemini. Persistence is JSON and Web Storage, not PostgreSQL. "
        "Semantic entropy remains future work. Those limits are consistent with a B.Tech Project-1 "
        "scope: a working, testable, deployable agent with a clear uncertainty policy.",
    )
    body(
        doc,
        "The principal conclusion is that extraction and policy should not share a prompt. When "
        "the language model is confined to copy-and-draft, and when send is a Python predicate "
        "over grounded slots, an email agent can be both helpful and conservative. That separation "
        "is the contribution of UNCERTAIN-EMAIL.",
    )


def add_chapter_7(doc) -> None:
    chapter(doc, 7, "Future Scope")
    numbered(
        doc,
        "PostgreSQL migration. Implement the Chapter 3 logical schema with SQLAlchemy 2.x, "
        "Alembic migrations, and parameterized queries. Move USER, AUDIT_ENTRY, and hashed "
        "refresh-token metadata off JSON and localStorage. Keep Gmail access tokens out of the "
        "database; store only server-side encrypted refresh tokens if long-lived mail is required.",
    )
    numbered(
        doc,
        "Calibrated uncertainty. Add an optional semantic-entropy or self-consistency probe for "
        "subject/body when the heuristic and Gemini disagree, without ever letting that probe "
        "invent a recipient.",
    )
    numbered(
        doc,
        "Durable duplicate detection. Replace the in-process DuplicateGuard with a Redis or SQL "
        "unique constraint so Render’s multiple instances cannot double-send.",
    )
    numbered(
        doc,
        "Richer audit. Persist full drafts server-side for the account owner, with retention and "
        "export, instead of a 50-row browser table.",
    )
    numbered(
        doc,
        "Production auth. Short-lived HTTP-only session cookies, refresh rotation, and rate "
        "limits on /auth/* as required by the organisation’s security standard.",
    )
    numbered(
        doc,
        "Multilingual instructions and additional Google Workspace scopes only after a privacy "
        "review. Keep gmail.send as the default least privilege.",
    )
    numbered(
        doc,
        "User study. Measure whether faculty prefer ASK-first over auto-send on a labelled set of "
        "campus speech acts (leave, meeting, circular).",
    )


def add_appendix(doc) -> None:
    chapter_like_appendix(doc)
    body(
        doc,
        "This appendix lists the live REST surface. Base URL in production: "
        "https://uncertainty-email-automation.onrender.com . The Vite app calls the same paths "
        "through VITE_API_BASE_URL. No endpoint returns GEMINI_API_KEY, password hashes, or raw "
        "Gmail refresh tokens.",
    )
    subsection(doc, "A.1 POST /chat")
    caption_table(doc, "A.1", "Example SEND request and response (dispatch disabled)")
    make_table(
        doc,
        ["Part", "JSON"],
        [
            [
                "Request",
                '{"message":"send mail to rahul@example.com regarding leave tomorrow"}',
            ],
            [
                "Response (abridged)",
                '{"phase":"decision_layer","decision":"SEND","clarification":null,'
                '"extraction":{"recipient":"rahul@example.com","subject":"Leave Request for Tomorrow",'
                '"body":"Hi Rahul,\\n\\nI am writing to request approval for leave tomorrow. ...",'
                '"recipient_mention":null},"assessment":{"method":"slot_sufficiency_threshold",'
                '"recipient":"resolved","subject":"resolved","body":"resolved","resolved_fraction":1.0},'
                '"dispatch":{"status":"disabled","message_id":null}}',
            ],
        ],
    )
    caption_table(doc, "A.2", "Example ASK response for a bare name")
    make_table(
        doc,
        ["Part", "JSON"],
        [
            ["Request", '{"message":"Email Rahul about tomorrow"}'],
            [
                "Response (abridged)",
                '{"decision":"ASK","clarification":"Who should I send this email to? '
                'Please provide their email address.","extraction":{"recipient":null,'
                '"recipient_mention":"Rahul"},"assessment":{"recipient":"bare_name",'
                '"subject":"resolved","body":"resolved","resolved_fraction":0.666...}}',
            ],
        ],
    )
    subsection(doc, "A.2 Other endpoints")
    bullet(doc, "GET|HEAD /health → {\"status\":\"ok\"}")
    bullet(doc, "GET /health/config → extraction_engine, dispatch_enabled, dispatch_mode, uncertainty_policy")
    bullet(doc, "POST /auth/google {credential} → {name, email, picture}")
    bullet(doc, "POST /auth/login {email, password} → profile or 401")
    bullet(doc, "POST /auth/register {name, email, password} → profile or 409")
    body(
        doc,
        "Headers of interest on POST /chat: Content-Type: application/json; optional "
        "X-Gmail-Token or Authorization: Bearer <access_token>. CORS allows only configured "
        "origins and the headers Authorization, Content-Type, Accept, X-Gmail-Token.",
    )


def chapter_like_appendix(doc) -> None:
    from scripts.btech_report.docx_utils import centered, page_break

    page_break(doc)
    centered(doc, "Appendix", 18, bold=True, space_after=4)
    centered(doc, "REST API Endpoints and Sample JSON Payloads", 18, bold=True, space_after=14)


def add_bibliography(doc) -> None:
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Mm, Pt

    from scripts.btech_report.docx_utils import page_break as _pb

    _pb(doc)
    p = doc.add_paragraph()
    p.style = doc.styles["Heading 1"]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.page_break_before = False
    p.clear()
    run(p, "Bibliography", 18, bold=True)
    refs = [
        "[1]  S. Kadavath et al., “Language models (mostly) know what they know,” arXiv:2207.05221, 2022.",
        "[2]  L. Kuhn, Y. Gal, and S. Farquhar, “Semantic uncertainty: Linguistic invariances for uncertainty estimation in LLMs,” in Proc. ICLR, 2023.",
        "[3]  G. Mesnil et al., “Using recurrent neural networks for slot filling in spoken language understanding,” IEEE/ACM Trans. Audio, Speech, Lang. Process., vol. 23, no. 3, pp. 530–539, Mar. 2015.",
        "[4]  A. Bordes, Y.-L. Boureau, and J. Weston, “Learning end-to-end goal-oriented dialog,” in Proc. ICLR, 2017.",
        "[5]  S. Amershi et al., “Guidelines for human-AI interaction,” in Proc. CHI, 2019, pp. 1–13.",
        "[6]  E. Horvitz, “Principles of mixed-initiative user interfaces,” in Proc. CHI, 1999, pp. 159–166.",
        "[7]  R. T. Fielding, “Architectural styles and the design of network-based software architectures,” Ph.D. dissertation, Univ. of California, Irvine, 2000.",
        "[8]  S. Ramírez, “FastAPI documentation,” [Online]. Available: https://fastapi.tiangolo.com (accessed Nov. 24, 2026).",
        "[9]  D. Hardt, Ed., “The OAuth 2.0 authorization framework,” RFC 6749, IETF, Oct. 2012.",
        "[10] Google, “Gmail API: Send a message,” [Online]. Available: https://developers.google.com/gmail/api/guides/sending (accessed Nov. 24, 2026).",
        "[11] M. T. Nygard, Release It!, 2nd ed. Raleigh, NC, USA: Pragmatic Bookshelf, 2018.",
        "[12] P. A. Grassi, M. E. Garcia, and J. L. Fenton, “Digital identity guidelines: Authentication and lifecycle management,” NIST SP 800-63B, 2017.",
        "[13] Meta Open Source, “React documentation,” [Online]. Available: https://react.dev (accessed Nov. 24, 2026).",
        "[14] Google, “Google Identity Services JavaScript SDK,” [Online]. Available: https://developers.google.com/identity/gsi/web (accessed Nov. 24, 2026).",
        "[15] K. Greshake et al., “Not what you’ve signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection,” in Proc. AISec, 2023.",
        "[16] F. Perez and I. Ribeiro, “Ignore previous prompt: Attack techniques for language models,” in NeurIPS ML Safety Workshop, 2022.",
        "[17] Pydantic, “Pydantic v2 documentation,” [Online]. Available: https://docs.pydantic.dev (accessed Nov. 24, 2026).",
        "[18] pytest-dev, “pytest documentation,” [Online]. Available: https://docs.pytest.org (accessed Nov. 24, 2026).",
        "[19] Google, “Gemini API: google-genai Python SDK,” [Online]. Available: https://ai.google.dev (accessed Nov. 24, 2026).",
        "[20] Encode, “Uvicorn,” [Online]. Available: https://www.uvicorn.org (accessed Nov. 24, 2026).",
        "[21] C. E. Shannon, “A mathematical theory of communication,” Bell Syst. Tech. J., vol. 27, pp. 379–423, 623–656, 1948.",
        "[22] OWASP, “Authentication cheat sheet,” [Online]. Available: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html (accessed Nov. 24, 2026).",
        "[23] Vite, “Vite documentation,” [Online]. Available: https://vite.dev (accessed Nov. 24, 2026).",
        "[24] Render, “Web services,” [Online]. Available: https://render.com/docs/web-services (accessed Nov. 24, 2026).",
        "[25] Vercel, “Deploying projects,” [Online]. Available: https://vercel.com/docs (accessed Nov. 24, 2026).",
    ]
    for text in refs:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Mm(-12)
        p.paragraph_format.left_indent = Mm(12)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(6)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run(p, text, 12)
