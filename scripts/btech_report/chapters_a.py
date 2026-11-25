"""Chapters 1–3 of the Project-1 report."""

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
    section_heading,
    subsection,
)

ASSETS = Path(__file__).resolve().parents[2] / "docs" / "report_assets"


def add_chapter_1(doc) -> None:
    chapter(doc, 1, "Introduction", new_page=False)
    section_heading(doc, "1.1 Introduction")
    body(
        doc,
        "Electronic mail remains the default medium for leave requests, meeting invitations, "
        "project updates, and other workplace speech acts. The cost of a wrong send is asymmetric: "
        "a missing comma is embarrassing, a message delivered to the wrong person is a privacy "
        "incident. Recent large language models can expand a four-word prompt into a complete "
        "letter, which creates a new failure mode. An agent that treats fluency as permission will "
        "fill every gap, invent a recipient, and press Send. This project asks a narrower, more "
        "operational question: when should an email agent send, and when must it ask?",
    )
    body(
        doc,
        "The submitted system, UNCERTAIN-EMAIL, is an uncertainty-aware multi-user email "
        "automation agent. A React workspace on Vercel collects a natural-language instruction. A "
        "FastAPI service on Render copies an email address only when the user wrote one, drafts a "
        "titled subject and a full body from the stated topic, and then applies a Python "
        "slot-sufficiency threshold. SEND occurs only when the recipient is a single address that "
        "occurs in the instruction, the subject is grounded in the user’s words, and the body is a "
        "complete professional message. Any other state returns ASK with exactly one question. The "
        "Gmail API is reached only after SEND, only with a user or process OAuth token, and only "
        "once per SHA-256 digest inside a ten-minute window.",
    )
    body(
        doc,
        "Two practical constraints shaped the design. First, Gemini Flash models on the free tier "
        "return 404, 429, and 503 in production; the extractor therefore runs under a six-second "
        "budget, tries at most two stable Flash identifiers, and falls back to a deterministic "
        "local heuristic so that POST /chat still returns HTTP 200. Second, a public Render "
        "process must not send mail from a shared token.json: production sets "
        "APP_REQUIRE_USER_GMAIL_TOKEN so each logged-in user connects Gmail in the browser and "
        "sends from their own account. The remainder of this chapter reviews related work, states "
        "objectives, and outlines the report.",
    )

    section_heading(doc, "1.2 Literature Review")
    body(
        doc,
        "Work on knowing when a model should abstain is older than instruction-tuned chat. "
        "Kadavath et al. showed that large language models can estimate the probability that their "
        "own answer is correct, yet those estimates are not a substitute for a policy [1]. Kuhn, "
        "Gal, and Farquhar introduced semantic entropy: uncertainty over meanings rather than over "
        "token sequences [2]. The present project does not compute semantic entropy. It treats "
        "uncertainty as a discrete slot problem because an email has three required fields, and a "
        "missing address is not a soft probability—it is a hard stop.",
    )
    body(
        doc,
        "Slot filling has a long history in spoken-language understanding. Mesnil et al. trained "
        "recurrent networks to label origin, destination, and date in travel queries [3]. "
        "Production assistants still separate extraction from policy: the recogniser may guess, "
        "the dialog manager decides whether to confirm. Bordes, Boureau, and Weston argued for "
        "end-to-end dialog, but even that line of work evaluates whether the system asked a "
        "useful question rather than whether it executed a side-effecting action [4]. Email is a "
        "side-effecting action. Once Gmail accepts users.messages.send, the act cannot be unsent "
        "by the agent.",
    )
    body(
        doc,
        "Human–AI interaction guidelines therefore put confirmation before irreversible actions. "
        "Amershi et al. recommend that a system “scope services when in doubt” and that it make "
        "clear when it is acting versus asking [5]. Horvitz’s principles of mixed-initiative "
        "interaction likewise treat expected cost of an error as the reason to defer to a person "
        "[6]. The ASK path in this project is that deferral, encoded as three questions with a "
        "fixed priority so the agent never loops on the same slot.",
    )
    body(
        doc,
        "On the systems side, Fielding’s REST constraints and the FastAPI/Starlette stack provide "
        "the request boundary [7], [8]. OAuth 2.0 (RFC 6749) and the Gmail API gmail.send scope "
        "are the only mail path [9], [10]. Nygard’s circuit-breaker pattern is the reason Gemini "
        "is given a wall-clock budget rather than an unbounded retry loop [11]. Password storage "
        "follows NIST SP 800-63B by using a memory-hard-enough PBKDF2-SHA256 construction with a "
        "random salt rather than reversible encryption [12]. React and the Google Identity "
        "Services client are the browser counterparts of that boundary [13], [14].",
    )
    body(
        doc,
        "Commercial “AI email” products typically hide the send decision inside the model prompt. "
        "The literature on prompt injection and tool-use leakage (Greshake et al.; Perez and "
        "Ribeiro) is a warning against that design [15], [16]: if the model both drafts and "
        "decides, an instruction can talk the agent into sending. UNCERTAIN-EMAIL keeps the "
        "language model on the extraction side of a hard Python gate. The model never returns "
        "decision, never returns a confidence score, and never invents an email address. That "
        "separation is the principal research contribution of the implementation.",
    )

    section_heading(doc, "1.3 Objectives")
    numbered(
        doc,
        "To design a deterministic ASK versus SEND policy over three email slots such that a "
        "message is dispatched only when recipient, subject, and body are resolved.",
    )
    numbered(
        doc,
        "To implement hybrid extraction: Google Gemini Flash under a 6 s / 2-model circuit "
        "breaker, with a local heuristic fallback that preserves dates, strips meta-instructions, "
        "and never repeats a clarification.",
    )
    numbered(
        doc,
        "To support multiple users through Google Identity Services and email/password accounts, "
        "with per-user Gmail OAuth (gmail.send) so production dispatch does not share a server token.",
    )
    numbered(
        doc,
        "To enforce human-in-the-loop dispatch: allow-list (optional), SHA-256 duplicate guard, "
        "audit log, and copy-only recipient addresses.",
    )
    numbered(
        doc,
        "To evaluate the policy against a gap-filling baseline on a labelled eighteen-case set "
        "and to protect the implementation with 147 automated pytest tests.",
    )
    numbered(
        doc,
        "To deploy a working faculty demo: React on Vercel, FastAPI on Render, UptimeRobot "
        "HEAD /health every five minutes.",
    )

    section_heading(doc, "1.4 Significance")
    body(
        doc,
        "The significance of the work is practical and pedagogical. Practically, a campus or a "
        "small office can demonstrate an agent that drafts leave letters and meeting notes without "
        "silently mailing the wrong person. Pedagogically, the project is a complete software "
        "engineering artefact: requirements, UML, a test suite, a live deployment, and an honest "
        "account of what the completeness ratio is not. Many undergraduate LLM projects report a "
        "single prompt. This one reports a policy, a fallback, and a refusal to send.",
    )

    section_heading(doc, "1.5 Research Design")
    body(
        doc,
        "The work is an engineering design study, not a randomised user trial. The independent "
        "artefact is the slot-sufficiency threshold in app/decision/sufficiency.py. The comparison "
        "artefact is the gap-filling baseline in app/baseline/direct.py, which always records a "
        "send on an in-memory sink. Gold labels live in eval/dataset.json (six complete, six "
        "partial, six ambiguous instructions). Metrics are defined in eval/metrics.py and were "
        "reproduced by pytest. Live Gemini quality is not part of the offline score, because free-"
        "tier 429 responses make a second sweep unreproducible; the test suite instead stubs the "
        "SDK and asserts fallback behaviour.",
    )

    section_heading(doc, "1.6 Source of Data")
    body(
        doc,
        "No production mailbox was mined. All evaluation addresses are on example.com. Demo "
        "accounts (admin@uncertain.ai, palak@gmail.com) are seeded hashes, not scraped passwords. "
        "Literature is cited from peer-reviewed venues and official RFCs listed in the "
        "Bibliography. Runtime configuration is read from environment variables documented in "
        ".env.example. Uptime observations are the HEAD /health probe described in Chapter 4.",
    )

    section_heading(doc, "1.7 Chapter Scheme")
    body(doc, "Chapter 1 introduces the problem, reviews literature, and states objectives.")
    body(doc, "Chapter 2 specifies users, functional and non-functional requirements, and constraints.")
    body(doc, "Chapter 3 presents algorithms, modules, DFDs, UML diagrams, and the logical/physical data model.")
    body(doc, "Chapter 4 records the implementation stack, 147 tests, installation, and end-user steps.")
    body(doc, "Chapter 5 discusses the interface, modules, snapshots, and backend stores.")
    body(doc, "Chapter 6 summarises conclusions. Chapter 7 lists future work. The Appendix gives REST payloads. The Bibliography follows IEEE style.")


def add_chapter_2(doc) -> None:
    chapter(doc, 2, "Requirement Specification")
    section_heading(doc, "2.1 User Characteristics")
    body(
        doc,
        "Primary users are undergraduate students, faculty, and office staff who can describe an "
        "email in one or two sentences but should not be asked to paste RFC 5322. They have a "
        "Google account or an email/password demo account, and they may connect Gmail in the "
        "browser. Secondary users are operators who set APP_DISPATCH_ENABLED, CORS origins, and "
        "UptimeRobot. The UI copy assumes English instructions; the heuristic recognises common "
        "English date phrases (tomorrow, on Monday, from 5 Dec to 8 Dec).",
    )

    section_heading(doc, "2.2 Functional Requirements")
    caption_table(doc, "2.1", "Functional requirements implemented in the submitted repository")
    make_table(
        doc,
        ["ID", "Requirement", "Where implemented"],
        [
            ["FR-01", "Google GIS and email/password sign-in", "app/routers/auth.py, LoginPage.tsx"],
            ["FR-02", "Register with hashed password (min 8, letter+digit)", "app/local_auth.py"],
            ["FR-03", "Compose natural-language instruction (1–4000 chars)", "ComposeView.tsx, ChatRequest"],
            ["FR-04", "Extract recipient, mention, subject, body", "app/extraction/gemini.py, heuristic.py"],
            ["FR-05", "ASK one missing slot; never repeat the same question", "app/decision/sufficiency.py"],
            ["FR-06", "Auto-draft professional body and titled subject", "app/extraction/compose.py"],
            ["FR-07", "Preserve dates/times in subject and body", "compose.py _when / _paragraph"],
            ["FR-08", "SEND only after threshold; dispatch via Gmail", "chat.py, app/dispatch/"],
            ["FR-09", "Per-user Gmail token (X-Gmail-Token / Bearer)", "gmailToken.ts, gmail.py"],
            ["FR-10", "Duplicate send lock 600 s on SHA-256 key", "app/dispatch/guard.py"],
            ["FR-11", "Audit log of SENT and PREVIEW cards", "auditLog.ts, AuditLogView.tsx"],
            ["FR-12", "Liveness GET and HEAD /health", "app/routers/health.py"],
            ["FR-13", "CORS allow-list, no wildcard in production", "app/config.py, main.py"],
        ],
    )

    section_heading(doc, "2.3 Dependencies")
    body(
        doc,
        "Runtime depends on Python 3.10+, Node.js 20+ for the frontend build, a Google AI Studio "
        "API key for Gemini, a Google Cloud OAuth client with Gmail API and GIS, and HTTPS hosts "
        "on Render and Vercel. Python dependencies are pinned in requirements.txt (FastAPI 0.141.1, "
        "google-genai 2.25.0, pydantic 2.13.5, uvicorn 0.54.0, pytest 9.1.1). Frontend dependencies "
        "are pinned in frontend/package.json (react 19.2.8, vite 8.3.0). There is no SQLAlchemy, "
        "Redis, or message queue in the submitted tree.",
    )

    section_heading(doc, "2.4 Performance Requirements")
    body(
        doc,
        "POST /chat must remain interactive on a faculty demo. The extractor therefore caps Gemini "
        "at T = 6.0 s and M = 2 models, with τ = 4000 ms per HTTP call and no same-model retry. "
        "The React client aborts a stalled check after 35 s. Heuristic extraction on the 147-test "
        "suite completes in well under one second on a laptop. UptimeRobot issues HEAD /health "
        "every five minutes; the handler does not probe Gmail or Gemini. DuplicateGuard is "
        "O(1) expected per claim with periodic expiry of keys older than 600 s.",
    )

    section_heading(doc, "2.5 Hardware Requirements")
    caption_table(doc, "2.2", "Minimum hardware and hosting used for the Project-1 demo")
    make_table(
        doc,
        ["Item", "Specification"],
        [
            ["Student workstation", "macOS or Windows, 8 GB RAM, Python 3.10+, Node 20+"],
            ["API host (Render)", "Web service, Python, environment variables from .env.example"],
            ["UI host (Vercel)", "Static Vite build, VITE_API_BASE_URL pointing at Render"],
            ["Monitoring", "UptimeRobot HTTP(s) HEAD https://…/health every 5 minutes"],
            ["Mail", "Gmail account with gmail.send; no self-hosted SMTP"],
        ],
    )

    section_heading(doc, "2.6 Constraints & Assumptions")
    bullet(doc, "Recipient addresses are copy-only. The model and the heuristic never invent an inbox.")
    bullet(doc, "resolved_fraction is a completeness ratio, not a probability and not semantic entropy.")
    bullet(doc, "Gemini free-tier 429/503 is expected; local fallback is the availability story.")
    bullet(doc, "Production dispatch requires a user Gmail access token; token.json is a loopback fallback.")
    bullet(doc, "The JSON user store and browser storage are the implemented persistence; PostgreSQL is future work (Chapter 7).")
    bullet(doc, "Instructions are English. Character bound is 4000 after trim.")
    bullet(doc, "Secrets are never logged; dispatch errors use fixed reason codes.")
    bullet(doc, "The frontend stitches only user turns into POST /chat; assistant questions are not replayed as instructions.")


def add_chapter_3(doc, figs: dict) -> None:
    chapter(doc, 3, "Design")
    section_heading(doc, "3.1 Algorithm")
    body(
        doc,
        "Two algorithms sit on the critical path. Algorithm A extracts slots under a circuit "
        "breaker. Algorithm B decides ASK or SEND. Neither algorithm sends mail; dispatch is a "
        "separate procedure that runs only when B returns SEND and a Dispatcher is configured.",
    )
    left(doc, "Algorithm A — Hybrid extraction with a 6 s circuit breaker", 12, bold=True, space_after=6)
    body(
        doc,
        "Input: instruction string I, deadline d = now + 6.0 s. If GEMINI_API_KEY is missing, "
        "raise ExtractionUnavailable (HTTP 503). Otherwise, for each of at most two cached Flash "
        "identifiers (gemini-flash-latest, gemini-2.0-flash), skip ids marked unavailable, abort "
        "if now ≥ d, and call generateContent with HTTP timeout 4000 ms and retry attempts = 1. "
        "On a valid JSON object, copy recipient only if it occurs in I, polish subject and body "
        "with compose_missing_body, and return. On 404/429/503/timeout/parse error, mark 404 "
        "models unavailable, try the next id. If the loop exhausts, return local_regex_extract(I) "
        "followed by apply_followup_slots so a last-line clarification answer binds to the open "
        "slot. Output: EmailExtraction. The route maps ExtractionUnavailable to 503 and every "
        "other extractor failure to this local object, never to HTTP 502.",
        indent=True,
    )
    left(doc, "Algorithm B — Slot-sufficiency threshold (decide)", 12, bold=True, space_after=6)
    body(
        doc,
        "Infer the previous clarification from local_regex_extract of all lines except the last. "
        "If that question targeted subject or body, absorb the last line into that slot and "
        "compose. Assess recipient (resolved / missing / bare_name / ambiguous), subject, and "
        "body. Subject is missing when empty or when subject_is_grounded fails. Ask recipient "
        "first (including “which address” when two emails appear), then SUBJECT_QUESTION, then "
        "BODY_QUESTION. If the next question equals the last question, fill from the last reply "
        "and reassess; if it would still repeat, suppress the question. When no question remains, "
        "return SEND with a Draft of the single address, titled subject, and full body. "
        "resolved_fraction = |{R,S,B} that are resolved| / 3.",
        indent=True,
    )

    section_heading(doc, "3.2 Function-Oriented / Modular Design")
    body(
        doc,
        "The repository is split so that Gmail imports exist only under app/dispatch/, Gemini "
        "imports only under app/extraction/gemini.py, and decide() never imports a mail sender. "
        "tests/test_chat.py parametrizes that isolation. Table 3.1 lists the modules.",
    )
    caption_table(doc, "3.1", "Software modules and their responsibilities")
    make_table(
        doc,
        ["Module", "Path", "Responsibility"],
        [
            ["API factory", "app/main.py", "CORS, routers, seed demo users, version 0.5.0"],
            ["Config", "app/config.py", "Fail-fast env: bind, CORS, dispatch, Gemini ids"],
            ["Chat route", "app/routers/chat.py", "threadpool extract, decide, dispatch"],
            ["Auth route", "app/routers/auth.py", "GIS ID token, login, register"],
            ["Health", "app/routers/health.py", "GET/HEAD /health, /health/config"],
            ["Gemini", "app/extraction/gemini.py", "2-model budget, cache, fallback"],
            ["Heuristic", "app/extraction/heuristic.py", "regex copy + follow-up slot bind"],
            ["Compose", "app/extraction/compose.py", "subject/body framing, dates, names"],
            ["Decision", "app/decision/sufficiency.py", "ASK/SEND threshold"],
            ["Dispatch", "app/dispatch/*", "allow-list, DuplicateGuard, GmailSender"],
            ["Local auth", "app/local_auth.py", "PBKDF2 user JSON store"],
            ["Baseline", "app/baseline/direct.py", "always-send eval executor"],
            ["Eval", "eval/*", "18 cases, metrics, note writer"],
            ["UI shell", "frontend/src/App.tsx", "login vs workspace"],
            ["Compose UI", "ComposeView.tsx, useChat.ts", "thread, 35 s abort, stitch"],
            ["Audit UI", "AuditLogView.tsx", "SENT/PREVIEW table"],
            ["Gmail UI", "GmailConnect.tsx, gmailToken.ts", "tokenClient gmail.send"],
        ],
    )
    add_picture(doc, figs["architecture"], 155)
    caption_figure(doc, "3.0", "Layered deployment: Vercel UI, Render API, JSON and browser stores")

    section_heading(doc, "3.3 System Design")
    subsection(doc, "3.3.1 Data Flow Diagrams (Level 0 and Level 1)")
    body(
        doc,
        "Figure 3.1 is the context diagram. The user exchanges natural-language turns with the "
        "system. Google Gemini returns slot JSON or an error. The Gmail API accepts a raw RFC 5322 "
        "payload. Google Identity Services verifies sign-in. Two data stores hold users and "
        "browser session/audit records. Figure 3.2 decomposes the system into authenticate, "
        "capture, extract, decide, dispatch, and audit processes.",
    )
    add_picture(doc, figs["dfd0"], 155)
    caption_figure(doc, "3.1", "Context diagram (DFD Level 0) of UNCERTAIN-EMAIL")
    add_picture(doc, figs["dfd1"], 155)
    caption_figure(doc, "3.2", "Level-1 data flow among authentication, extraction, decision, and dispatch")

    subsection(doc, "3.3.2 Activity Diagram")
    body(
        doc,
        "Figure 3.3 shows the happy path and the clarification loop. After sign-in the user may "
        "connect Gmail. Each Check posts the stitched user turns. Extraction and decide() run "
        "inside run_in_threadpool so the event loop is not blocked. ASK returns to the composer; "
        "SEND goes to Dispatcher.",
    )
    add_picture(doc, figs["activity"], 130)
    caption_figure(doc, "3.3", "Activity diagram from sign-in through ASK loop or Gmail send")

    subsection(doc, "3.3.3 Flow Chart")
    body(
        doc,
        "Figure 3.4 is the extractor circuit breaker. The important control-flow facts are: no "
        "same-model retry, skip of preview and known-dead ids, in-memory cache of a working model, "
        "and guaranteed local heuristic when the budget expires.",
    )
    add_picture(doc, figs["flowchart"], 130)
    caption_figure(doc, "3.4", "Flow chart of hybrid Gemini extraction with local fallback")

    subsection(doc, "3.3.4 Class Diagram")
    body(
        doc,
        "Figure 3.5 summarises the principal types. FastAPI App owns three routers. ChatRouter "
        "depends on GeminiExtractor (which may call HeuristicComposer) and Sufficiency, then on "
        "Dispatcher. UserStore is used only by AuthRouter. The React workspace is a separate "
        "process that holds Session, GmailAccess, and AuditEntry in Web Storage.",
    )
    add_picture(doc, figs["class"], 155)
    caption_figure(doc, "3.5", "Class diagram of backend services and the React workspace")

    subsection(doc, "3.3.5 ER Diagram")
    body(
        doc,
        "Figure 3.6 is the logical ER model. USER is identified by email. SESSION and GMAIL_TOKEN "
        "are 1:1 with the signed-in email in the browser. AUDIT_ENTRY is 1:N. DISPATCH_CLAIM is "
        "process-local and is not durable across Render restarts. CHAT_TURN is the in-memory "
        "thread on the client; only concatenated user text is posted to /chat.",
    )
    add_picture(doc, figs["er"], 155)
    caption_figure(doc, "3.6", "Entity-relationship diagram of the logical data model")

    subsection(doc, "3.3.6 Sequence Diagram")
    body(
        doc,
        "Figure 3.7 traces a SEND that uses the X-Gmail-Token header. The browser never sends the "
        "Google ID token on /chat; that token is used only on /auth/google. A missing user token "
        "in production returns HTTP 403 with the Connect Gmail copy. An expired Gmail token "
        "returns HTTP 401 Reconnect Gmail.",
    )
    add_picture(doc, figs["sequence"], 155)
    caption_figure(doc, "3.7", "Sequence diagram of POST /chat leading to Gmail users.messages.send")

    section_heading(doc, "3.4 Database Design")
    body(
        doc,
        "Inspection of app/ found no SQLAlchemy models and no PostgreSQL driver. Persistence is "
        "intentionally small for a Project-1 demo: a JSON file of password hashes, Web Storage on "
        "the client, and an in-memory duplicate map. The logical design below is still a "
        "third-normal-form relational schema of those records, so a later PostgreSQL migration "
        "(Chapter 7) has a documented target. Claiming that PostgreSQL is already wired would be "
        "false; the physical design therefore names the real files and keys.",
    )

    subsection(doc, "3.4.1 Logical Database Design")
    caption_table(doc, "3.2", "Relation USER (local email/password accounts)")
    make_table(
        doc,
        ["Attribute", "Type", "Constraints", "Description"],
        [
            ["email", "VARCHAR(254)", "PK, unique, lowercased", "Login identifier"],
            ["name", "VARCHAR(80)", "NOT NULL", "Display name"],
            ["password_hash", "CHAR(encoded)", "NOT NULL", "pbkdf2_sha256$200000$salt$digest"],
            ["picture", "TEXT", "default ''", "Empty for local accounts"],
        ],
    )
    caption_table(doc, "3.3", "Relations SESSION, GMAIL_TOKEN, AUDIT_ENTRY, DISPATCH_CLAIM")
    make_table(
        doc,
        ["Relation", "Key", "Attributes", "Notes"],
        [
            ["SESSION", "email PK/FK", "name, picture", "Mirrors GIS or local profile"],
            ["GMAIL_TOKEN", "email PK/FK", "access_token, expires_at", "gmail.send only; never logged"],
            ["AUDIT_ENTRY", "id PK", "email FK, ts, recipient, subject, body_preview, status, clarification_turns", "status ∈ {SENT, PREVIEW}"],
            ["DISPATCH_CLAIM", "message_key PK", "claimed_at, window_s", "message_key = SHA-256(to, subject, body)"],
        ],
    )
    body(
        doc,
        "Normalisation: USER is in 3NF (every non-key attribute depends on email). SESSION and "
        "GMAIL_TOKEN are 1:1 extensions rather than extra attributes of USER because they live in "
        "a different trust domain (the browser) and expire independently. AUDIT_ENTRY stores a "
        "body preview, not the full body, to keep the browser quota small (50 rows). No relation "
        "stores a Gemini API key or a refresh token in the client.",
    )

    subsection(doc, "3.4.2 Physical Database Design")
    caption_table(doc, "3.4", "Physical mapping of logical relations")
    make_table(
        doc,
        ["Relation", "Physical store", "Key / path", "Durability"],
        [
            ["USER", "JSON object file", "APP_USERS_PATH default data/users.json", "Disk on API host; atomic tmp replace"],
            ["SESSION", "localStorage", "uncertain-email-session", "Until sign-out or origin clear"],
            ["GMAIL_TOKEN", "sessionStorage", "uncertain-email-gmail:<email>", "Tab-scoped; dropped at expiry"],
            ["AUDIT_ENTRY", "localStorage array", "uncertain-email-audit, cap 50", "Until Clear History"],
            ["DISPATCH_CLAIM", "process dict", "DuplicateGuard._claimed", "Lost on Render restart"],
            ["CHAT_TURN", "React state + thread helper", "frontend/src/thread.ts", "Cleared on sign-out"],
        ],
    )
    body(
        doc,
        "Physical security choices: passwords never leave the API as plaintext; verify_password "
        "uses hmac.compare_digest; a dummy hash is verified when the email is unknown so timing "
        "does not leak membership. Gmail access tokens are not written to disk on the server when "
        "the user-token path is used. CORS is an explicit origin list. These are file- and "
        "header-level controls, not SQL GRANT statements, because there is no database server in "
        "the current deployment.",
    )
