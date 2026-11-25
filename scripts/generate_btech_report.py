#!/usr/bin/env python3
"""Generate the Medicaps University B.Tech Project-1 report as a .docx file.

Run from the repository root:

    PYTHONPATH=docs/report_vendor:. python scripts/generate_btech_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "docs" / "report_vendor"
if VENDOR.exists():
    sys.path.insert(0, str(VENDOR))
sys.path.insert(0, str(ROOT))

from docx.enum.section import WD_SECTION

from scripts.btech_report.chapters_a import add_chapter_1, add_chapter_2, add_chapter_3
from scripts.btech_report.chapters_b import (
    add_appendix,
    add_bibliography,
    add_chapter_4,
    add_chapter_5,
    add_chapter_6,
    add_chapter_7,
)
from scripts.btech_report.docx_utils import (
    add_centered_page_number,
    apply_page,
    new_document,
    set_number_format,
)
from scripts.btech_report.figures import generate_all
from scripts.btech_report.front import (
    add_abbreviations,
    add_abstract,
    add_acknowledgements,
    add_approval,
    add_certificate,
    add_cover,
    add_declaration,
    add_list_of_figures,
    add_list_of_tables,
    add_notations,
    add_title_page,
    add_toc,
)

OUT = ROOT / "docs" / "BTech_Project_1_Report_Palak_Punjabi.docx"


def _blank_footer(section) -> None:
    section.footer.is_linked_to_previous = False
    section.footer.paragraphs[0].text = ""
    section.header.is_linked_to_previous = False
    section.header.paragraphs[0].text = ""


def main() -> None:
    figs = generate_all()
    doc = new_document()

    cover = doc.sections[0]
    apply_page(cover, top=25, bottom=20)
    set_number_format(cover, "decimal", 1)
    _blank_footer(cover)
    add_cover(doc)
    add_title_page(doc)

    prelim = doc.add_section(WD_SECTION.NEW_PAGE)
    apply_page(prelim)
    set_number_format(prelim, "lowerRoman", 2)
    add_centered_page_number(prelim, roman=True)
    add_approval(doc)
    add_declaration(doc)
    add_certificate(doc)
    add_acknowledgements(doc)
    add_abstract(doc)
    add_toc(doc)
    add_list_of_figures(doc)
    add_list_of_tables(doc)
    add_abbreviations(doc)
    add_notations(doc)

    body = doc.add_section(WD_SECTION.NEW_PAGE)
    apply_page(body)
    set_number_format(body, "decimal", 1)
    add_centered_page_number(body, roman=False, skip_first=True)
    add_chapter_1(doc)
    add_chapter_2(doc)
    add_chapter_3(doc, figs)
    add_chapter_4(doc)
    add_chapter_5(doc, figs)
    add_chapter_6(doc)
    add_chapter_7(doc)
    add_appendix(doc)
    add_bibliography(doc)

    core = doc.core_properties
    core.author = "Palak Punjabi"
    core.title = (
        "Uncertainty-Aware Email Automation System — B.Tech Project-1 Report"
    )
    core.subject = "Computer Science & Engineering, Medicaps University"
    core.category = "Project-1 Report"
    core.comments = "EN23CS301704, December 2026, Guide: Prof. Shankar Raj Soni"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
