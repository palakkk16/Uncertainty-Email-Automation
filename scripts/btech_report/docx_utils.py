"""Times New Roman, A4, Medicaps margin and heading helpers."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn, nsmap
from docx.shared import Mm, Pt, Cm, Emu, RGBColor, Inches
from docx.table import Table
from docx.text.paragraph import Paragraph

NAVY = RGBColor(0x1B, 0x36, 0x5D)
MAROON = RGBColor(0x8B, 0x1E, 0x3F)
BLACK = RGBColor(0x00, 0x00, 0x00)
TNR = "Times New Roman"
LOGO = Path(__file__).resolve().parents[2] / "docs" / "report_assets" / "medicaps_logo.jpeg"


def new_document() -> Document:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = TNR
    style.font.size = Pt(12)
    style.font.color.rgb = BLACK
    style.element.rPr.rFonts.set(qn("w:eastAsia"), TNR)
    pf = style.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    _style_heading(doc, "Heading 1", 18, True, WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    _style_heading(doc, "Heading 2", 16, True, WD_ALIGN_PARAGRAPH.LEFT, space_before=14, space_after=8)
    _style_heading(doc, "Heading 3", 14, True, WD_ALIGN_PARAGRAPH.LEFT, space_before=10, space_after=6)
    return doc


def _style_heading(doc, name, size, bold, align, space_before=0, space_after=8):
    style = doc.styles[name]
    style.font.name = TNR
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = BLACK
    style.element.rPr.rFonts.set(qn("w:eastAsia"), TNR)
    style.paragraph_format.alignment = align
    style.paragraph_format.space_before = Pt(space_before)
    style.paragraph_format.space_after = Pt(space_after)
    style.paragraph_format.line_spacing = 1.5
    style.paragraph_format.page_break_before = False


def apply_page(section, *, top=30, bottom=22, left=30, right=20):
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(top)
    section.bottom_margin = Mm(bottom)
    section.left_margin = Mm(left)
    section.right_margin = Mm(right)
    section.header_distance = Mm(12)
    section.footer_distance = Mm(10)


def set_number_format(section, fmt: str, start: int | None = None) -> None:
    sect_pr = section._sectPr
    node = sect_pr.find(qn("w:pgNumType"))
    if node is None:
        node = OxmlElement("w:pgNumType")
        sect_pr.append(node)
    node.set(qn("w:fmt"), fmt)
    if start is not None:
        node.set(qn("w:start"), str(start))


def add_centered_page_number(section, *, roman: bool = False, skip_first: bool = False) -> None:
    footer = section.footer
    footer.is_linked_to_previous = False
    para = footer.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_run_font(para.add_run(""), 12)
    _add_page_field(para, "ROMAN" if roman else "ARABIC")
    if skip_first:
        section.different_first_page_header_footer = True
        first = section.first_page_footer
        first.is_linked_to_previous = False
        first.paragraphs[0].text = ""


def _add_page_field(paragraph: Paragraph, kind: str) -> None:
    run = paragraph.add_run()
    _set_run_font(run, 12)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" PAGE \\* {kind} "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text_run = OxmlElement("w:t")
    text_run.text = "1"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(separate)
    run._r.append(text_run)
    run._r.append(end)


def _set_run_font(run, size, *, bold=False, italic=False, color=BLACK):
    run.font.name = TNR
    run._element.rPr.rFonts.set(qn("w:eastAsia"), TNR)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = color


def run(paragraph, text, size=12, *, bold=False, italic=False, color=BLACK):
    r = paragraph.add_run(text)
    _set_run_font(r, size, bold=bold, italic=italic, color=color)
    return r


def body(doc, text, *, indent=True, space_after=8, align=WD_ALIGN_PARAGRAPH.JUSTIFY) -> Paragraph:
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    if indent:
        p.paragraph_format.first_line_indent = Mm(12)
    p.paragraph_format.widow_control = True
    run(p, text, 12)
    return p


def centered(doc, text, size=12, *, bold=False, italic=False, space_after=0, space_before=0, color=BLACK):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.first_line_indent = Mm(0)
    run(p, text, size, bold=bold, italic=italic, color=color)
    return p


def left(doc, text, size=12, *, bold=False, italic=False, space_after=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.first_line_indent = Mm(0)
    run(p, text, size, bold=bold, italic=italic)
    return p


def chapter(doc, number: int, title: str, *, new_page: bool = True) -> Paragraph:
    if new_page:
        page_break(doc)
    p = doc.add_paragraph()
    p.style = doc.styles["Heading 1"]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.page_break_before = False
    p.clear()
    run(p, f"Chapter {number}", 18, bold=True)
    p2 = doc.add_paragraph()
    p2.style = doc.styles["Heading 1"]
    p2.paragraph_format.page_break_before = False
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.clear()
    run(p2, title, 18, bold=True)
    return p2


def section_heading(doc, text: str) -> Paragraph:
    p = doc.add_paragraph(text, style="Heading 2")
    p.paragraph_format.first_line_indent = Mm(0)
    for r in p.runs:
        _set_run_font(r, 16, bold=True)
    return p


def subsection(doc, text: str) -> Paragraph:
    p = doc.add_paragraph(text, style="Heading 3")
    p.paragraph_format.first_line_indent = Mm(0)
    for r in p.runs:
        _set_run_font(r, 14, bold=True)
    return p


def bullet(doc, text: str) -> Paragraph:
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.left_indent = Mm(12)
    p.clear()
    run(p, text, 12)
    return p


def numbered(doc, text: str) -> Paragraph:
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_after = Pt(4)
    p.clear()
    run(p, text, 12)
    return p


def caption_table(doc, number: str, title: str) -> Paragraph:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.first_line_indent = Mm(0)
    run(p, f"Table {number}: {title}", 12, bold=True)
    return p


def caption_figure(doc, number: str, title: str) -> Paragraph:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(12)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.first_line_indent = Mm(0)
    run(p, f"Figure {number}: {title}", 12, italic=True)
    return p


def add_picture(doc, path: Path, width_mm: float = 150) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Mm(0)
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(str(path), width=Mm(width_mm))


def add_logo(doc, width_mm: float = 42) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = Mm(0)
    r = p.add_run()
    r.add_picture(str(LOGO), width=Mm(width_mm))


def page_break(doc) -> None:
    doc.add_page_break()


def set_borders(table: Table) -> None:
    tbl = table._tbl
    tblPr = tbl.tblPr if tbl.tblPr is not None else OxmlElement("w:tblPr")
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "8")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "1B365D")
        borders.append(el)
    tblPr.append(borders)


def shade_header(cell, color="1B365D") -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def make_table(doc, headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None) -> Table:
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    set_borders(table)
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run(p, h, 11, bold=True, color=RGBColor(255, 255, 255))
        shade_header(cell)
    for r_i, row in enumerate(rows, start=1):
        for c_i, value in enumerate(row):
            cell = table.rows[r_i].cells[c_i]
            cell.text = ""
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.line_spacing = 1.15
            run(p, value, 10)
            if r_i % 2 == 0:
                shade_header(cell, "EEF3F8")
    return table


def signature_line(doc, label: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.first_line_indent = Mm(0)
    run(p, "_______________________________", 12)
    left(doc, label, 12, bold=True, space_after=0)
