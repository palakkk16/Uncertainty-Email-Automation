"""High-resolution UML-style figures for Chapter 3 and Chapter 5 placeholders."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, Rectangle

NAVY = "#1B365D"
MAROON = "#8B1E3F"
TEAL = "#2A6F7F"
GOLD = "#C4A35A"
SLATE = "#4A5568"
PAPER = "#F7F5F1"
BOX = "#FFFFFF"
ASK = "#B45309"
SEND = "#1F7A4D"
OUT = Path(__file__).resolve().parents[2] / "docs" / "report_assets"
DPI = 220


def generate_all() -> dict[str, Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {
        "dfd0": _dfd_level0(),
        "dfd1": _dfd_level1(),
        "activity": _activity(),
        "flowchart": _flowchart(),
        "class": _class_diagram(),
        "er": _er_diagram(),
        "sequence": _sequence(),
        "architecture": _architecture(),
        "ui1": _placeholder("5.1", "Login Page", "Google Identity Services and email/password sign-in"),
        "ui2": _placeholder("5.2", "Compose Agent", "Chat thread, Check control, and clarification turns"),
        "ui3": _placeholder("5.3", "ASK Clarification", "Agent asking for a missing slot such as subject"),
        "ui4": _placeholder("5.4", "SEND Confirmation", "Draft card after a SEND decision and Gmail dispatch"),
        "ui5": _placeholder("5.5", "Sent & Audit Log", "Timestamp, recipient, subject, status, clarification turns"),
    }
    return paths


def _fig(w: float, h: float):
    fig, ax = plt.subplots(figsize=(w, h), dpi=DPI)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    return fig, ax


def _save(fig, name: str) -> Path:
    path = OUT / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor="white", pad_inches=0.25)
    plt.close(fig)
    return path


def _box(ax, x, y, w, h, text, *, fill=BOX, ec=NAVY, fs=8.5, weight="medium", radius=0.6):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.25,rounding_size={radius}",
        linewidth=1.3,
        edgecolor=ec,
        facecolor=fill,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        color=NAVY,
        fontweight=weight,
        wrap=True,
    )


def _actor(ax, x, y, label):
    ax.add_patch(Circle((x, y + 8), 2.2, fill=False, lw=1.4, edgecolor=MAROON))
    ax.plot([x, x], [y + 5.8, y + 1.5], color=MAROON, lw=1.4)
    ax.plot([x - 2.4, x + 2.4], [y + 4.2, y + 4.2], color=MAROON, lw=1.4)
    ax.plot([x, x - 2.0], [y + 1.5, y - 1.5], color=MAROON, lw=1.4)
    ax.plot([x, x + 2.0], [y + 1.5, y - 1.5], color=MAROON, lw=1.4)
    ax.text(x, y - 4.2, label, ha="center", va="top", fontsize=8, color=MAROON, fontweight="bold")


def _arrow(ax, x1, y1, x2, y2, label="", *, color=NAVY):
    ax.annotate(
        "",
        xy=(x2, y2),
        xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.15),
    )
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 1.6, label, ha="center", fontsize=7, color=SLATE)


def _store(ax, x, y, w, h, text):
    ax.add_patch(Rectangle((x, y), w, h, fill=True, facecolor="#EEF3F8", edgecolor=TEAL, lw=1.3))
    ax.plot([x + 1.2, x + 1.2], [y, y + h], color=TEAL, lw=1.3)
    ax.plot([x + w - 1.2, x + w - 1.2], [y, y + h], color=TEAL, lw=1.3)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8, color=NAVY, fontweight="medium")


def _dfd_level0() -> Path:
    fig, ax = _fig(11.2, 7.4)
    ax.text(50, 96, "Context Diagram (DFD Level 0)", ha="center", fontsize=12, color=NAVY, fontweight="bold")
    _actor(ax, 12, 55, "End User")
    _box(ax, 32, 38, 36, 28, "Uncertainty-Aware\nEmail Automation System\n(FastAPI + React)", fill="#E8EEF6", fs=10, weight="bold")
    _box(ax, 78, 72, 18, 12, "Google Gemini\nAPI", fs=8)
    _box(ax, 78, 44, 18, 12, "Gmail API\ngmail.send", fs=8)
    _box(ax, 78, 16, 18, 12, "Google Identity\nServices", fs=8)
    _store(ax, 8, 14, 22, 10, "D1 User Store\n(JSON / PBKDF2)")
    _store(ax, 34, 14, 24, 10, "D2 Browser Storage\n(session + audit)")
    _arrow(ax, 16, 52, 32, 52, "natural-language\ninstruction")
    _arrow(ax, 32, 46, 16, 46, "ASK / SEND reply")
    _arrow(ax, 68, 60, 78, 76, "JSON slots")
    _arrow(ax, 78, 74, 68, 58, "extraction or 4xx/5xx")
    _arrow(ax, 68, 50, 78, 50, "RFC 5322 raw")
    _arrow(ax, 78, 48, 68, 48, "message_id")
    _arrow(ax, 68, 42, 78, 24, "ID token")
    _arrow(ax, 20, 38, 20, 24, "credentials")
    _arrow(ax, 46, 38, 46, 24, "session / audit")
    return _save(fig, "fig_3_1_dfd_level0.png")


def _dfd_level1() -> Path:
    fig, ax = _fig(12.2, 8.2)
    ax.text(50, 97, "Data Flow Diagram (Level 1)", ha="center", fontsize=12, color=NAVY, fontweight="bold")
    _actor(ax, 8, 78, "User")
    _box(ax, 22, 78, 16, 10, "1.0\nAuthenticate", fs=8)
    _box(ax, 44, 78, 16, 10, "2.0 Capture\nInstruction", fs=8)
    _box(ax, 22, 50, 20, 12, "3.0 Extract Slots\nGemini + Heuristic\n6 s / 2 models", fs=8)
    _box(ax, 50, 50, 20, 12, "4.0 Decide\nSlot sufficiency\nASK or SEND", fs=8)
    _box(ax, 78, 50, 18, 12, "5.0 Dispatch\nAllowlist +\nDuplicateGuard", fs=8)
    _box(ax, 50, 22, 20, 10, "6.0 Record Audit", fs=8)
    _store(ax, 2, 22, 18, 10, "D1 users.json")
    _store(ax, 24, 22, 18, 10, "D2 local/session\nStorage")
    _box(ax, 78, 78, 18, 10, "Gemini API", fs=8)
    _box(ax, 78, 22, 18, 10, "Gmail API", fs=8)
    _arrow(ax, 12, 82, 22, 83, "credential")
    _arrow(ax, 38, 83, 44, 83, "session")
    _arrow(ax, 52, 78, 42, 62, "message")
    _arrow(ax, 42, 62, 78, 80, "generateContent")
    _arrow(ax, 42, 56, 50, 56, "EmailExtraction")
    _arrow(ax, 70, 56, 78, 56, "Draft")
    _arrow(ax, 87, 50, 87, 32, "raw send")
    _arrow(ax, 60, 50, 60, 32, "SEND card")
    _arrow(ax, 50, 22, 42, 22)
    _arrow(ax, 22, 78, 12, 32, "hash check")
    return _save(fig, "fig_3_2_dfd_level1.png")


def _activity() -> Path:
    fig, ax = _fig(11.0, 13.2)
    ax.text(50, 98, "Activity Diagram — Compose to Dispatch", ha="center", fontsize=12, color=NAVY, fontweight="bold")
    steps = [
        (40, 90, 20, 5, "Start", GOLD),
        (32, 81, 36, 6, "Sign in (Google or email/password)", BOX),
        (32, 72, 36, 6, "Optional: Connect Gmail (gmail.send)", BOX),
        (32, 63, 36, 6, "Enter natural-language instruction", BOX),
        (32, 54, 36, 6, "POST /chat  (threadpool extract)", BOX),
        (32, 44, 36, 7, "Hybrid extract (Gemini ≤ 6 s,\nelse local heuristic)", "#E8EEF6"),
        (32, 34, 36, 6, "decide() slot-sufficiency threshold", BOX),
    ]
    for x, y, w, h, t, fill in steps:
        _box(ax, x, y, w, h, t, fill=fill, fs=8)
        if y < 90:
            _arrow(ax, 50, y + h + 1.2, 50, y + h - 0.2 if False else y + 6.2)
    # diamonds
    def diamond(cx, cy, label, fill):
        xs = [cx, cx + 14, cx, cx - 14, cx]
        ys = [cy + 5, cy, cy - 5, cy, cy + 5]
        ax.fill(xs, ys, facecolor=fill, edgecolor=NAVY, lw=1.3)
        ax.text(cx, cy, label, ha="center", va="center", fontsize=7.5, color=NAVY, fontweight="bold")

    diamond(50, 25, "All three\nslots resolved?", "#FFF6E5")
    _box(ax, 4, 16, 28, 8, "ASK: one clarification question\n(recipient → subject → body)", fill="#F8E7D6", fs=7.5)
    _box(ax, 68, 16, 28, 8, "SEND: Dispatcher + GmailSender\nDuplicateGuard 600 s window", fill="#E3F2EA", fs=7.5)
    _box(ax, 36, 4, 28, 6, "Write audit entry  /  End", fill=GOLD, fs=8)
    ax.annotate("", xy=(18, 24), xytext=(36, 25), arrowprops=dict(arrowstyle="-|>", color=ASK, lw=1.2))
    ax.annotate("", xy=(82, 24), xytext=(64, 25), arrowprops=dict(arrowstyle="-|>", color=SEND, lw=1.2))
    ax.text(28, 28.5, "No — ASK", color=ASK, fontsize=7.5, fontweight="bold")
    ax.text(66, 28.5, "Yes — SEND", color=SEND, fontsize=7.5, fontweight="bold")
    ax.annotate("", xy=(50, 10), xytext=(18, 16), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.1))
    ax.annotate("", xy=(50, 10), xytext=(82, 16), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.1))
    ax.annotate("", xy=(50, 63), xytext=(18, 20), arrowprops=dict(arrowstyle="-|>", color=SLATE, lw=1.0, linestyle="--"))
    ax.text(10, 40, "user answers;\nstitch turns", fontsize=7, color=SLATE, rotation=90)
    return _save(fig, "fig_3_3_activity.png")


def _flowchart() -> Path:
    fig, ax = _fig(11.4, 13.4)
    ax.text(50, 98, "Flow Chart — Hybrid Extraction Circuit Breaker", ha="center", fontsize=12, color=NAVY, fontweight="bold")
    _box(ax, 30, 90, 40, 6, "Instruction arrives at POST /chat", fs=8.5)
    _box(ax, 30, 80, 40, 6, "GEMINI_API_KEY present?", fs=8.5, fill="#FFF6E5")
    _box(ax, 4, 68, 28, 7, "503 ExtractionUnavailable\n(no local guess of address)", fill="#F8E7D6", fs=7.5)
    _box(ax, 42, 68, 50, 7, "deadline = now + 6.0 s; try at most 2 Flash models\ngemini-flash-latest then gemini-2.0-flash", fill="#E8EEF6", fs=7.5)
    _box(ax, 42, 56, 50, 7, "Per-call HTTP timeout 4000 ms, retries = 1\nSkip preview / 2.5-flash-lite / cached 404s", fs=7.5)
    _box(ax, 42, 44, 50, 6, "Model returns valid JSON slots?", fill="#FFF6E5", fs=8)
    _box(ax, 4, 32, 36, 8, "On 404 / 429 / 503 / timeout / parse error:\ntry next model if budget remains", fill="#F8E7D6", fs=7.5)
    _box(ax, 48, 20, 44, 8, "local_regex_extract + apply_followup_slots\n+ compose_missing_body (dates preserved)", fill="#E3F2EA", fs=7.5)
    _box(ax, 48, 8, 44, 7, "EmailExtraction → decide() → ASK or SEND\nHTTP 200 (never 502 on Gemini failure)", fill=GOLD, fs=7.5)
    _arrow(ax, 50, 90, 50, 86)
    ax.annotate("", xy=(18, 75), xytext=(30, 82), arrowprops=dict(arrowstyle="-|>", color=ASK, lw=1.15))
    ax.annotate("", xy=(50, 75), xytext=(50, 80), arrowprops=dict(arrowstyle="-|>", color=SEND, lw=1.15))
    ax.text(24, 84, "No", color=ASK, fontsize=8, fontweight="bold")
    ax.text(54, 77, "Yes", color=SEND, fontsize=8, fontweight="bold")
    _arrow(ax, 67, 68, 67, 63)
    _arrow(ax, 67, 56, 67, 50)
    ax.annotate("", xy=(22, 40), xytext=(42, 46), arrowprops=dict(arrowstyle="-|>", color=ASK, lw=1.15))
    ax.annotate("", xy=(70, 28), xytext=(70, 44), arrowprops=dict(arrowstyle="-|>", color=SEND, lw=1.15))
    ax.text(30, 48, "No", color=ASK, fontsize=8, fontweight="bold")
    ax.text(78, 36, "Yes / polish", color=SEND, fontsize=8, fontweight="bold")
    ax.annotate("", xy=(70, 28), xytext=(40, 34), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.1))
    _arrow(ax, 70, 20, 70, 15)
    return _save(fig, "fig_3_4_flowchart.png")


def _class_diagram() -> Path:
    fig, ax = _fig(12.4, 8.6)
    ax.text(50, 97, "Class Diagram — Principal Backend and UI Types", ha="center", fontsize=12, color=NAVY, fontweight="bold")

    def clazz(x, y, w, h, title, body):
        ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=NAVY, lw=1.2))
        ax.add_patch(Rectangle((x, y + h - 5.2), w, 5.2, facecolor="#E8EEF6", edgecolor=NAVY, lw=1.2))
        ax.text(x + w / 2, y + h - 2.6, title, ha="center", va="center", fontsize=7.4, fontweight="bold", color=NAVY)
        ax.text(x + 1.0, y + h - 6.2, body, ha="left", va="top", fontsize=6.3, color=SLATE, family="monospace")

    clazz(2, 70, 22, 22, "FastAPI App", "create_app()\nCORSMiddleware\nrouters: chat, auth,\nhealth")
    clazz(28, 70, 22, 22, "ChatRouter", "POST /chat\nrun_in_threadpool\nextract → decide\n→ dispatch")
    clazz(54, 70, 22, 22, "AuthRouter", "POST /auth/login\nPOST /auth/register\nPOST /auth/google")
    clazz(80, 70, 18, 22, "HealthRouter", "GET|HEAD /health\nGET /health/config")
    clazz(2, 38, 24, 26, "GeminiExtractor", "extract_email_fields()\nbudget 6 s, max 2 models\ncache working id\nfallback heuristic")
    clazz(30, 38, 24, 26, "HeuristicComposer", "local_regex_extract()\napply_followup_slots()\ncompose_missing_body()\npreserve dates/times")
    clazz(58, 38, 20, 26, "Sufficiency", "decide()\nASK | SEND\nresolved_fraction\nno duplicate question")
    clazz(82, 38, 16, 26, "Dispatcher", "allowlist\nDuplicateGuard\nGmailSender")
    clazz(8, 6, 22, 24, "UserStore", "users.json\nhash_password PBKDF2\nauthenticate()\nregister_user()")
    clazz(36, 6, 22, 24, "GmailSender", "user access token\nor token.json\nbuild_raw_message()\ngmail.users.messages.send")
    clazz(64, 6, 30, 24, "React Workspace", "LoginPage, ComposeView\nAuditLogView, GmailConnect\nsessionStorage Gmail token\nlocalStorage session+audit")
    _arrow(ax, 13, 70, 13, 64)
    _arrow(ax, 39, 70, 39, 64)
    _arrow(ax, 65, 70, 65, 64)
    _arrow(ax, 90, 70, 90, 64)
    _arrow(ax, 40, 38, 40, 30)
    _arrow(ax, 68, 38, 47, 30)
    _arrow(ax, 90, 38, 47, 18)
    return _save(fig, "fig_3_5_class.png")


def _er_diagram() -> Path:
    fig, ax = _fig(12.0, 8.0)
    ax.text(50, 97, "Entity-Relationship Diagram — Logical Data Model", ha="center", fontsize=12, color=NAVY, fontweight="bold")

    def ent(x, y, w, h, title, attrs):
        ax.add_patch(Rectangle((x, y), w, h, facecolor="white", edgecolor=NAVY, lw=1.25))
        ax.add_patch(Rectangle((x, y + h - 5), w, 5, facecolor="#E8EEF6", edgecolor=NAVY, lw=1.25))
        ax.text(x + w / 2, y + h - 2.5, title, ha="center", va="center", fontsize=8, fontweight="bold", color=NAVY)
        ax.text(x + 1.2, y + h - 6.2, attrs, ha="left", va="top", fontsize=6.6, color=SLATE, family="monospace")

    ent(4, 58, 26, 32, "USER", "email  PK\nname\npassword_hash\npicture_url\ncreated_at")
    ent(38, 62, 26, 28, "SESSION", "email  PK/FK\nname\npicture\nstored_in localStorage")
    ent(72, 62, 24, 28, "GMAIL_TOKEN", "email  PK/FK\naccess_token\nexpires_at\nstored_in sessionStorage")
    ent(4, 12, 28, 34, "AUDIT_ENTRY", "id  PK\nemail  FK\ntimestamp\nrecipient\nsubject\nbody_preview\nstatus SENT|PREVIEW\nclarification_turns")
    ent(40, 16, 26, 30, "DISPATCH_CLAIM", "message_key  PK\nsha256(to,subject,body)\nclaimed_at\nwindow_s = 600")
    ent(72, 12, 24, 34, "CHAT_TURN", "thread_id\nrole user|assistant\ntext\nstitched user turns\nposted as message")
    ax.annotate("", xy=(38, 76), xytext=(30, 76), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.2))
    ax.text(34, 78.5, "1", fontsize=7)
    ax.text(36, 72, "1", fontsize=7)
    ax.annotate("", xy=(72, 76), xytext=(64, 76), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.2))
    ax.annotate("", xy=(18, 46), xytext=(18, 58), arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.2))
    ax.text(19.5, 52, "1..*", fontsize=7)
    ax.text(86, 48, "per browser tab", fontsize=7, color=SLATE)
    return _save(fig, "fig_3_6_er.png")


def _sequence() -> Path:
    fig, ax = _fig(12.4, 9.0)
    ax.text(50, 97, "Sequence Diagram — Successful SEND with User Gmail Token", ha="center", fontsize=12, color=NAVY, fontweight="bold")
    lanes = [
        (10, "Browser\nReact UI"),
        (32, "FastAPI\n/chat"),
        (54, "Extractor\nGemini/local"),
        (74, "decide()"),
        (92, "Gmail API"),
    ]
    for x, label in lanes:
        ax.text(x, 90, label, ha="center", va="top", fontsize=7.5, color=NAVY, fontweight="bold")
        ax.plot([x, x], [8, 82], color="#CBD5E1", lw=1.0, linestyle="--")

    def msg(x1, x2, y, text, dashed=False):
        style = "dashed" if dashed else "solid"
        ax.annotate(
            "",
            xy=(x2, y),
            xytext=(x1, y),
            arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.05, linestyle=style),
        )
        ax.text((x1 + x2) / 2, y + 1.5, text, ha="center", fontsize=6.4, color=SLATE)

    msg(10, 32, 78, "POST /chat {message}  + X-Gmail-Token")
    msg(32, 54, 70, "extract_email_fields(instruction)")
    msg(54, 32, 62, "EmailExtraction  (or local fallback)", dashed=True)
    msg(32, 74, 54, "decide(instruction, fields)")
    msg(74, 32, 46, "Decision SEND + Draft", dashed=True)
    msg(32, 92, 38, "users.messages.send raw")
    msg(92, 32, 30, "id / message_id", dashed=True)
    msg(32, 10, 22, "ChatResponse decision=SEND dispatch.sent")
    ax.text(50, 12, "ASK path returns clarification and does not call Gmail.", ha="center", fontsize=8, color=MAROON, style="italic")
    return _save(fig, "fig_3_7_sequence.png")


def _architecture() -> Path:
    fig, ax = _fig(11.6, 7.6)
    ax.text(50, 96, "Layered Deployment Architecture", ha="center", fontsize=12, color=NAVY, fontweight="bold")
    _box(ax, 8, 72, 84, 16, "Presentation  —  React 19 + Vite 8 on Vercel\nhttps://uncertainty-email-automation.vercel.app\nCompose Agent  ·  Sent & Audit Log  ·  GIS login  ·  GmailConnect", fill="#E8EEF6", fs=8.5)
    _box(ax, 8, 48, 84, 16, "Application  —  FastAPI 0.141 + Uvicorn on Render\nhttps://uncertainty-email-automation.onrender.com\nstarlette.concurrency.run_in_threadpool  ·  Pydantic v2 schemas  ·  CORS allow-list", fill="#F4E9EE", fs=8.5)
    _box(ax, 8, 24, 40, 16, "Decision & Extraction\nGemini google-genai 2.25\nLocal heuristic compose\nSlot-sufficiency threshold", fill="#E3F2EA", fs=8)
    _box(ax, 52, 24, 40, 16, "Security & Dispatch\nPBKDF2-SHA256 users.json\nOAuth 2.0 gmail.send\nDuplicateGuard 600 s", fill="#FFF6E5", fs=8)
    _box(ax, 8, 6, 84, 12, "Persistence  —  JSON user store on the API host; browser localStorage (session, audit); sessionStorage (per-user Gmail access token); in-memory dispatch claims", fill=PAPER, fs=8)
    return _save(fig, "fig_3_0_architecture.png")


def _placeholder(number: str, title: str, hint: str) -> Path:
    fig, ax = _fig(10.2, 6.4)
    ax.add_patch(
        FancyBboxPatch(
            (6, 12),
            88,
            76,
            boxstyle="round,pad=0.4,rounding_size=1.2",
            linewidth=1.6,
            linestyle=(0, (6, 4)),
            edgecolor=NAVY,
            facecolor="#F8FAFC",
        )
    )
    ax.text(50, 68, f"Figure {number}  —  {title}", ha="center", fontsize=13, color=NAVY, fontweight="bold")
    ax.text(50, 54, "Screenshot placeholder", ha="center", fontsize=11, color=SLATE)
    ax.text(50, 42, hint, ha="center", fontsize=9, color=SLATE)
    ax.text(
        50,
        28,
        "Paste the corresponding UI capture from\nhttps://uncertainty-email-automation.vercel.app\ninside this bordered frame before hard-binding.",
        ha="center",
        fontsize=8,
        color=MAROON,
    )
    return _save(fig, f"fig_{number.replace('.', '_')}_placeholder.png")
