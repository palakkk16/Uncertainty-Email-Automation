"""Cover through notations, matching the Medicaps annexure order without the annexure notes."""

from __future__ import annotations

from docx.shared import Mm, Pt

from scripts.btech_report.docx_utils import (
    add_logo,
    body,
    bullet,
    caption_table,
    centered,
    left,
    make_table,
    page_break,
    run,
    signature_line,
)

TITLE = (
    "Uncertainty-Aware Email Automation System "
    "(Design and Implementation of an Uncertainty-Aware Multi-User Email Automation System)"
)
SHORT_TITLE = "Uncertainty-Aware Email Automation System"


def add_cover(doc) -> None:
    add_logo(doc, 46)
    centered(doc, TITLE, 16, bold=True, space_before=10, space_after=10)
    centered(doc, "A Project-1 Report", 14, bold=True, space_after=6)
    centered(doc, "Submitted in partial fulfillment of requirement of the", 12, space_after=0)
    centered(doc, "Degree of", 12, space_after=6)
    centered(doc, "BACHELOR OF TECHNOLOGY", 14, bold=True, space_after=0)
    centered(doc, "in", 12, space_after=0)
    centered(doc, "COMPUTER SCIENCE & ENGINEERING", 14, bold=True, space_after=12)
    centered(doc, "BY", 12, bold=True, space_after=6)
    centered(doc, "Palak Punjabi", 14, bold=True, space_after=0)
    centered(doc, "EN23CS301704", 12, space_after=12)
    centered(doc, "Under the Guidance of", 12, italic=True, space_after=4)
    centered(doc, "Prof. Shankar Raj Soni", 13, bold=True, space_after=0)
    centered(doc, "Assistant Professor", 12, space_after=0)
    centered(doc, "Department of Computer Science & Engineering", 12, space_after=14)
    centered(doc, "Department of Computer Science & Engineering", 12, bold=True, space_after=0)
    centered(doc, "Faculty of Engineering", 12, space_after=0)
    centered(doc, "MEDICAPS UNIVERSITY, INDORE - 453331", 13, bold=True, space_after=10)
    centered(doc, "December-2026", 13, bold=True)


def add_title_page(doc) -> None:
    page_break(doc)
    add_logo(doc, 42)
    centered(doc, TITLE, 16, bold=True, space_before=8, space_after=10)
    centered(doc, "A Project-1 Report", 14, bold=True, space_after=6)
    centered(doc, "Submitted in partial fulfillment of requirement of the", 12)
    centered(doc, "Degree of", 12, space_after=6)
    centered(doc, "BACHELOR OF TECHNOLOGY", 14, bold=True)
    centered(doc, "in COMPUTER SCIENCE & ENGINEERING", 13, bold=True, space_after=12)
    centered(doc, "BY", 12, bold=True, space_after=6)
    centered(doc, "Palak Punjabi", 14, bold=True)
    centered(doc, "University Roll No.: EN23CS301704", 12, space_after=10)
    centered(doc, "Under the Guidance of", 12, italic=True, space_after=4)
    centered(doc, "Prof. Shankar Raj Soni", 13, bold=True)
    centered(doc, "Assistant Professor, Department of Computer Science & Engineering", 12, space_after=12)
    centered(doc, "Department of Computer Science & Engineering", 12, bold=True)
    centered(doc, "Faculty of Engineering", 12)
    centered(doc, "MEDICAPS UNIVERSITY, INDORE - 453331", 13, bold=True, space_after=8)
    centered(doc, "December 2026", 13, bold=True)


def add_approval(doc) -> None:
    centered(doc, "Report Approval", 18, bold=True, space_after=16)
    body(
        doc,
        f'The project-1 “{SHORT_TITLE}” is hereby approved as a creditable study of an '
        "engineering subject carried out and presented in a manner satisfactory to warrant its "
        "acceptance as a prerequisite to the degree for which it has been submitted. It is to be "
        "understood that by this approval the undersigned do not endorse or approve any statement "
        "made, opinion expressed, or conclusion drawn therein; but approve the project-1 report "
        "only for the purpose for which it is submitted.",
        indent=True,
    )
    left(doc, "Internal Examiner", 14, bold=True, space_after=6)
    left(doc, "Name: ________________________________", 12, space_after=0)
    left(doc, "Designation: _________________________", 12, space_after=0)
    left(doc, "Affiliation: __________________________", 12, space_after=14)
    left(doc, "External Examiner", 14, bold=True, space_after=6)
    left(doc, "Name: ________________________________", 12, space_after=0)
    left(doc, "Designation: _________________________", 12, space_after=0)
    left(doc, "Affiliation: __________________________", 12, space_after=18)
    left(doc, "Date: ____________________", 12, space_after=0)
    left(doc, "Place: Medicaps University, Indore", 12, space_after=0)


def add_declaration(doc) -> None:
    page_break(doc)
    centered(doc, "Declaration", 18, bold=True, space_after=16)
    body(
        doc,
        f'I hereby declare that the project entitled “{SHORT_TITLE}” submitted in partial '
        "fulfillment for the award of the degree of Bachelor of Technology in Computer Science & "
        "Engineering of Medicaps University, Indore, is a record of my own work carried out under "
        "the guidance of Prof. Shankar Raj Soni, Assistant Professor, Department of Computer "
        "Science & Engineering. The matter embodied in this project has not been submitted to any "
        "other university or institute for the award of any degree or diploma.",
        indent=True,
    )
    body(
        doc,
        "Further, I declare that the content of this project work, in full or in parts, has neither "
        "been taken from any other source without due acknowledgement nor been submitted to any "
        "other university or institute for the award of any degree.",
        indent=True,
    )
    left(doc, "Date: ____________________", 12, space_after=18)
    left(doc, "Signature of the student", 12, bold=True, space_after=0)
    left(doc, "Palak Punjabi", 12, bold=True, space_after=0)
    left(doc, "EN23CS301704", 12, space_after=0)
    left(doc, "B.Tech. IV Year, Computer Science & Engineering", 12, space_after=0)
    left(doc, "Medicaps University, Indore", 12, space_after=0)


def add_certificate(doc) -> None:
    page_break(doc)
    add_logo(doc, 36)
    centered(doc, "Certificate", 18, bold=True, space_after=14)
    body(
        doc,
        "I, Prof. Shankar Raj Soni, certify that the project entitled "
        f"“{SHORT_TITLE}” submitted in partial fulfillment for the award of the degree of "
        "Bachelor of Technology in Computer Science & Engineering by Palak Punjabi "
        "(EN23CS301704) is a bona fide record of work carried out under my supervision. The "
        "work has been completed to my satisfaction and is worthy of consideration for the award "
        "of the said degree.",
        indent=True,
    )
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(28)
    p.paragraph_format.first_line_indent = Mm(0)
    run(p, "_______________________________", 12)
    left(doc, "Prof. Shankar Raj Soni", 12, bold=True, space_after=0)
    left(doc, "Internal Guide", 12, space_after=0)
    left(doc, "Assistant Professor", 12, space_after=0)
    left(doc, "Department of Computer Science & Engineering", 12, space_after=0)
    left(doc, "Medicaps University, Indore", 12, space_after=18)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.first_line_indent = Mm(0)
    run(p, "_______________________________", 12)
    left(doc, "Dr. Kailash Chandra Bandhu", 12, bold=True, space_after=0)
    left(doc, "Head of the Department", 12, space_after=0)
    left(doc, "Computer Science & Engineering", 12, space_after=0)
    left(doc, "Medicaps University, Indore", 12, space_after=0)


def add_acknowledgements(doc) -> None:
    page_break(doc)
    centered(doc, "Acknowledgements", 18, bold=True, space_after=14)
    body(
        doc,
        "I would like to express my deepest gratitude to the Honourable Chancellor, Shri R. C. "
        "Mittal, who has provided every facility required to carry out this work at Medicaps "
        "University. I am equally grateful to the Honourable Vice Chancellor, Prof. (Dr.) D. K. "
        "Patnaik, for academic leadership that makes undergraduate research of this kind possible.",
    )
    body(
        doc,
        "I sincerely thank the Associate Dean (Computing & Allied Branches), Prof. (Dr.) Ratnesh "
        "Litoriya, and the Head of the Department of Computer Science & Engineering, Prof. (Dr.) "
        "Kailash Chandra Bandhu, for their guidance, laboratory support, and continuous "
        "encouragement during Project-1.",
    )
    body(
        doc,
        "I would also like to express my gratitude to my internal guide, Prof. Shankar Raj Soni, "
        "Assistant Professor, Department of Computer Science & Engineering. His reviews of the "
        "uncertainty policy, the ASK versus SEND threshold, and the live Gmail dispatch path "
        "shaped the engineering of this system. It is because of his help and support that I was "
        "able to complete the design, implementation, testing, and deployment described in this "
        "report.",
    )
    body(
        doc,
        "Finally, I thank my family and classmates for their patience during the long sequence of "
        "integration tests that a live email agent demands, and the open-source communities behind "
        "FastAPI, React, pytest, and the Google APIs that this project stands on.",
    )
    left(doc, "Palak Punjabi", 12, bold=True, space_after=0)
    left(doc, "B.Tech. IV Year", 12, space_after=0)
    left(doc, "Department of Computer Science & Engineering", 12, space_after=0)
    left(doc, "Faculty of Engineering", 12, space_after=0)
    left(doc, "Medicaps University, Indore", 12, space_after=0)


def add_abstract(doc) -> None:
    page_break(doc)
    centered(doc, "Abstract", 18, bold=True, space_after=14)
    body(
        doc,
        "Large language models can draft fluent email, yet fluency is not a licence to send. "
        "When a user types a short instruction such as “mail Rahul about tomorrow,” an over-eager "
        "agent may invent an address, assume a subject, and dispatch a message the user never "
        "approved. This Project-1 report presents the design and implementation of an "
        "uncertainty-aware, multi-user email automation system that refuses that shortcut. The "
        "system copies recipient addresses only from user text, drafts a professional subject and "
        "body from the stated intent, and then applies a deterministic Python slot-sufficiency "
        "threshold: SEND if and only if recipient, subject, and body are resolved; otherwise ASK "
        "exactly one clarification question, in a fixed order of recipient, then subject, then "
        "body. The completeness ratio resolved_fraction is reported as resolved slots divided by "
        "three. It is not a calibrated probability, not semantic entropy, and not a model "
        "confidence score.",
    )
    body(
        doc,
        "The architecture is hybrid and fault-tolerant. A React 19 workspace hosted on Vercel "
        "(https://uncertainty-email-automation.vercel.app) offers Google Identity Services sign-in, "
        "email/password accounts, a Compose Agent, a Sent & Audit Log, and a per-user Gmail OAuth "
        "connection persisted in sessionStorage. A FastAPI service hosted on Render "
        "(https://uncertainty-email-automation.onrender.com) extracts slots with the google-genai "
        "SDK under a six-second wall-clock circuit breaker and a two-model cap "
        "(gemini-flash-latest, then gemini-2.0-flash, 4000 ms per call). On HTTP 404, 429, 503, "
        "timeout, or parse failure the extractor falls back to a local heuristic that still "
        "returns HTTP 200, strips meta-instructions from subjects, preserves dates and times in "
        "both subject and body, and never repeats the same clarification twice. Dispatch uses the "
        "Gmail API gmail.send scope, a SHA-256 duplicate lock of 600 seconds, and an optional "
        "allow-list. Passwords are stored as PBKDF2-SHA256 hashes in data/users.json; the browser "
        "holds session and audit records. There is no SQLAlchemy engine in the submitted "
        "codebase: the logical relational schema in Chapter 3 is the 3NF model of those stores.",
    )
    body(
        doc,
        "Chapter 1 reviews related work on selective prediction, slot filling, and human-in-the-loop "
        "agents. Chapter 2 specifies users, functions, performance, and constraints. Chapter 3 "
        "gives algorithms, modular design, DFDs, UML diagrams, and the logical and physical data "
        "model. Chapter 4 documents the stack and 147 automated pytest tests. Chapter 5 discusses "
        "modules, UI snapshots, and backend stores. Chapter 6 concludes; Chapter 7 outlines a "
        "PostgreSQL migration, calibrated uncertainty, and production hardening. An offline "
        "eighteen-case evaluation shows task success 18/18, zero incorrect SEND on gold-ASK cases, "
        "and 12/12 prevented misfires against a gap-filling baseline that always records a send.",
    )
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Mm(0)
    p.paragraph_format.space_before = Pt(10)
    run(p, "Keywords: ", 12, bold=True)
    run(
        p,
        "uncertainty-aware agents; slot-sufficiency threshold; ASK versus SEND; Gemini Flash; "
        "heuristic fallback; circuit breaker; Gmail API; OAuth 2.0; FastAPI; React; human-in-the-loop.",
        12,
        italic=True,
    )


def add_toc(doc) -> None:
    page_break(doc)
    centered(doc, "Table of Contents", 18, bold=True, space_after=12)
    rows = [
        ("Report Approval", "ii"),
        ("Declaration", "iii"),
        ("Certificate", "iv"),
        ("Acknowledgements", "v"),
        ("Abstract", "vi"),
        ("Table of Contents", "vii"),
        ("List of Figures", "viii"),
        ("List of Tables", "ix"),
        ("Abbreviations", "x"),
        ("Notations & Symbols", "xi"),
        ("Chapter 1  Introduction", "1"),
        ("    1.1 Introduction", "1"),
        ("    1.2 Literature Review", "3"),
        ("    1.3 Objectives", "6"),
        ("    1.4 Significance", "7"),
        ("    1.5 Research Design", "8"),
        ("    1.6 Source of Data", "9"),
        ("    1.7 Chapter Scheme", "10"),
        ("Chapter 2  Requirement Specification", "11"),
        ("    2.1 User Characteristics", "11"),
        ("    2.2 Functional Requirements", "12"),
        ("    2.3 Dependencies", "13"),
        ("    2.4 Performance Requirements", "14"),
        ("    2.5 Hardware Requirements", "15"),
        ("    2.6 Constraints & Assumptions", "15"),
        ("Chapter 3  Design", "17"),
        ("    3.1 Algorithm", "17"),
        ("    3.2 Function-Oriented / Modular Design", "19"),
        ("    3.3 System Design", "21"),
        ("        3.3.1 Data Flow Diagrams (Level 0 & Level 1)", "21"),
        ("        3.3.2 Activity Diagram", "23"),
        ("        3.3.3 Flow Chart", "24"),
        ("        3.3.4 Class Diagram", "25"),
        ("        3.3.5 ER Diagram", "26"),
        ("        3.3.6 Sequence Diagram", "27"),
        ("    3.4 Database Design", "28"),
        ("        3.4.1 Logical Database Design", "28"),
        ("        3.4.2 Physical Database Design", "30"),
        ("Chapter 4  Implementation, Testing, and Maintenance", "32"),
        ("    4.1 Languages, IDEs, Tools and Technologies", "32"),
        ("    4.2 Testing Techniques and Test Plans", "34"),
        ("    4.3 Installation Instructions", "38"),
        ("    4.4 End User Instructions", "39"),
        ("Chapter 5  Results and Discussions", "41"),
        ("    5.1 User Interface Representation", "41"),
        ("    5.2 Brief Description of Various Modules", "42"),
        ("    5.3 Snapshots of the System", "44"),
        ("    5.4 Back-End Representation", "46"),
        ("    5.5 Snapshots of Data Stores", "47"),
        ("Chapter 6  Summary and Conclusions", "49"),
        ("Chapter 7  Future Scope", "51"),
        ("Appendix  REST API Endpoints and Sample Payloads", "53"),
        ("Bibliography", "56"),
    ]
    for title, page in rows:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.first_line_indent = Mm(0)
        dots = max(3, 72 - len(title) - len(page))
        run(p, f"{title} {'.' * dots} {page}", 12)


def add_list_of_figures(doc) -> None:
    page_break(doc)
    centered(doc, "List of Figures", 18, bold=True, space_after=10)
    caption_table(doc, "F.1", "Figures appearing in this report")
    make_table(
        doc,
        ["S.No.", "Figure No.", "Figure Name"],
        [
            ["1", "3.0", "Layered deployment architecture (Vercel, Render, stores)"],
            ["2", "3.1", "Context diagram (DFD Level 0)"],
            ["3", "3.2", "Data flow diagram (Level 1)"],
            ["4", "3.3", "Activity diagram of compose-to-dispatch"],
            ["5", "3.4", "Flow chart of the hybrid extraction circuit breaker"],
            ["6", "3.5", "Class diagram of principal types"],
            ["7", "3.6", "Entity-relationship diagram of the logical data model"],
            ["8", "3.7", "Sequence diagram of a successful SEND"],
            ["9", "5.1", "Login page (screenshot placeholder)"],
            ["10", "5.2", "Compose Agent (screenshot placeholder)"],
            ["11", "5.3", "ASK clarification turn (screenshot placeholder)"],
            ["12", "5.4", "SEND confirmation (screenshot placeholder)"],
            ["13", "5.5", "Sent & Audit Log (screenshot placeholder)"],
        ],
    )


def add_list_of_tables(doc) -> None:
    page_break(doc)
    centered(doc, "List of Tables", 18, bold=True, space_after=10)
    caption_table(doc, "T.1", "Tables appearing in this report")
    make_table(
        doc,
        ["S.No.", "Table No.", "Table Name"],
        [
            ["1", "2.1", "Functional requirements"],
            ["2", "2.2", "Hardware and software requirements"],
            ["3", "3.1", "Software modules and responsibilities"],
            ["4", "3.2", "Logical schema of USER"],
            ["5", "3.3", "Logical schema of GMAIL_TOKEN, SESSION, AUDIT_ENTRY"],
            ["6", "3.4", "Physical mapping of logical entities to stores"],
            ["7", "4.1", "Languages, frameworks, and pinned versions"],
            ["8", "4.2", "Pytest files and collected test counts (147 total)"],
            ["9", "4.3", "Representative test cases (black-box)"],
            ["10", "4.4", "Offline evaluation metrics (18 labelled cases)"],
            ["11", "5.1", "REST routes implemented in app/routers"],
            ["12", "5.2", "users.json physical record"],
            ["13", "A.1", "POST /chat request and SEND response"],
            ["14", "A.2", "POST /chat ASK response"],
        ],
    )


def add_abbreviations(doc) -> None:
    page_break(doc)
    centered(doc, "Abbreviations", 18, bold=True, space_after=10)
    make_table(
        doc,
        ["S.No.", "Acronym", "Abbreviation"],
        [
            ["1", "API", "Application Programming Interface"],
            ["2", "ASK", "Clarification decision of the slot-sufficiency threshold"],
            ["3", "CORS", "Cross-Origin Resource Sharing"],
            ["4", "CSE", "Computer Science & Engineering"],
            ["5", "DFD", "Data Flow Diagram"],
            ["6", "ER", "Entity-Relationship"],
            ["7", "GIS", "Google Identity Services"],
            ["8", "HTTP", "Hypertext Transfer Protocol"],
            ["9", "JSON", "JavaScript Object Notation"],
            ["10", "JWT", "JSON Web Token (Google ID token)"],
            ["11", "LLM", "Large Language Model"],
            ["12", "OAuth", "Open Authorization"],
            ["13", "PBKDF2", "Password-Based Key Derivation Function 2"],
            ["14", "REST", "Representational State Transfer"],
            ["15", "SEND", "Dispatch-eligible decision of the threshold"],
            ["16", "SDK", "Software Development Kit"],
            ["17", "UML", "Unified Modeling Language"],
            ["18", "UI", "User Interface"],
        ],
    )


def add_notations(doc) -> None:
    page_break(doc)
    centered(doc, "Notations & Symbols", 18, bold=True, space_after=10)
    make_table(
        doc,
        ["S.No.", "Symbol", "Description"],
        [
            ["1", "ρ", "resolved_fraction = (resolved slots) / 3"],
            ["2", "S", "Subject slot status ∈ {resolved, missing}"],
            ["3", "B", "Body slot status ∈ {resolved, missing}"],
            ["4", "R", "Recipient status ∈ {resolved, missing, bare_name, ambiguous}"],
            ["5", "τ", "Per-call Gemini HTTP timeout = 4000 ms"],
            ["6", "T", "Wall-clock extraction budget = 6.0 s"],
            ["7", "M", "Maximum Flash models attempted = 2"],
            ["8", "W", "DuplicateGuard window = 600 s"],
            ["9", "H", "PBKDF2-SHA256 with 200 000 iterations"],
            ["10", "k", "SHA-256 message key of (recipient, subject, body)"],
        ],
    )
