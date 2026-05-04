#!/usr/bin/env python3
"""Generate a PDF from the Task 1 Markdown submission document (simple formatting)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos
except ImportError:
    print("Install: pip install -r scripts/requirements-pdf.txt", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MD = ROOT / "files" / "CINEGRAPH_AI_TASK1_SUBMISSION_DOCUMENT.md"
DEFAULT_OUT = ROOT / "files" / "CINEGRAPH_AI_Task1_Submission.pdf"


class SubmissionPDF(FPDF):
    def __init__(self) -> None:
        super().__init__()
        self.set_auto_page_break(auto=True, margin=18)
        self._body = "Helvetica"
        self._body_b = "Helvetica"

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font(self._body, "", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)


def _strip_md_inline(s: str) -> str:
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"`(.+?)`", r"\1", s)
    return _ascii_safe(s)


def _ascii_safe(s: str) -> str:
    """Core PDF fonts are latin-1; normalize common Unicode punctuation."""
    return (
        s.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2192", "->")
        .replace("\u2022", "*")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)|(https?://[^\s]+)")


def _render_rich_line(pdf: SubmissionPDF, text: str, indent: int = 0, bullet_prefix: str = "") -> None:
    """Render a single markdown line with clickable links."""
    pdf.set_x(pdf.l_margin + indent)
    if bullet_prefix:
        pdf.write(6, bullet_prefix)
    line = _strip_md_inline(text)
    cursor = 0
    for m in LINK_RE.finditer(line):
        start, end = m.span()
        if start > cursor:
            pdf.write(6, line[cursor:start])
        if m.group(1) and m.group(2):
            label = _ascii_safe(m.group(1))
            url = m.group(2)
        else:
            label = _ascii_safe(m.group(3))
            url = m.group(3)
        pdf.set_text_color(20, 70, 170)
        pdf.set_font(pdf._body, "U", 11)
        pdf.write(6, label, link=url)
        pdf.set_font(pdf._body, "", 11)
        pdf.set_text_color(0, 0, 0)
        cursor = end
    if cursor < len(line):
        pdf.write(6, line[cursor:])
    pdf.ln(6)


def _section_block(pdf: SubmissionPDF, title: str) -> None:
    y = pdf.get_y()
    pdf.set_fill_color(237, 242, 250)
    pdf.set_draw_color(225, 232, 245)
    pdf.rect(pdf.l_margin, y, pdf.w - pdf.l_margin - pdf.r_margin, 9, style="DF")
    pdf.set_y(y + 1.2)
    pdf.set_font(pdf._body_b, "", 12.5)
    pdf.set_text_color(30, 50, 90)
    pdf.cell(0, 6, _strip_md_inline(title))
    pdf.ln(8)
    pdf.set_text_color(0, 0, 0)


def build_pdf(md_path: Path, out_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    pdf = SubmissionPDF()
    pdf.add_page()
    pdf.set_font(pdf._body, "", 11)

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            pdf.ln(4)
            continue
        if line.strip() == "---":
            pdf.ln(2)
            continue
        if line.startswith("# "):
            y = pdf.get_y()
            pdf.set_fill_color(28, 38, 58)
            pdf.rect(pdf.l_margin, y, pdf.w - pdf.l_margin - pdf.r_margin, 12, style="F")
            pdf.set_y(y + 2)
            pdf.set_font(pdf._body_b, "", 16)
            pdf.set_text_color(245, 247, 252)
            pdf.cell(0, 8, _strip_md_inline(line[2:].strip()))
            pdf.ln(2)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(pdf._body, "", 11)
            continue
        if line.startswith("## "):
            _section_block(pdf, line[3:].strip())
            pdf.ln(1)
            pdf.set_font(pdf._body, "", 11)
            continue
        if line.startswith("### "):
            pdf.set_font(pdf._body_b, "", 11)
            pdf.multi_cell(
                0, 7, _strip_md_inline(line[4:].strip()), new_x=XPos.LMARGIN, new_y=YPos.NEXT
            )
            pdf.ln(1)
            pdf.set_font(pdf._body, "", 11)
            continue
        if line.strip().startswith("|") and "|" in line.strip()[1:]:
            # Skip markdown tables (wide rows break single-line layout in core fonts)
            if re.match(r"^\|\s*[-:]+\s*\|", line.strip()):
                continue
            continue
        if line.lstrip().startswith("- "):
            _render_rich_line(pdf, line.lstrip()[2:], indent=4, bullet_prefix="* ")
            continue
        if re.match(r"^\d+\.\s", line.lstrip()):
            _render_rich_line(pdf, line.strip(), indent=4)
            continue
        if line.startswith("```"):
            continue
        _render_rich_line(pdf, line)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    print(f"Wrote {out_path}")


def main() -> None:
    md = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MD
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    if not md.exists():
        print(f"Missing: {md}", file=sys.stderr)
        sys.exit(1)
    build_pdf(md, out)


if __name__ == "__main__":
    main()
