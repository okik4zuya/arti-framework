#!/usr/bin/env python3
"""
arti-docx - Markdown -> styled .docx (journal manuscript layout)

Rebuilds the entire document body fresh from a Markdown source on each run,
using a *style template* purely for styles/section-properties/footer (A4,
margins, continuous line numbering, page-number footer, named paragraph/table
styles). Markdown is the source of truth; the .docx is a snapshot rendered
from it, the same way arti-pdf treats its HTML/PDF output - never a merge
into an existing .docx's content.

Requires python-docx (see ~/.arti/tools/requirements.txt).

This is intentionally not a full CommonMark implementation - just enough
structure for a manuscript draft: headings, single-line paragraphs with
bold/italic, blockquotes, pipe tables, images, bold Table/Fig captions, code
fences (rendered verbatim as a monospace fallback for an ASCII placeholder
not yet swapped for a real image), and a References section.

Explicit non-goals for v1: nested/numbered lists, footnotes, merging into an
existing docx section-by-section. Extend the converter for these if a
document needs them, rather than reaching for pandoc.

Usage:
    python render.py --md manuscript.md --out manuscript.docx [--template style-template.docx]
"""
import argparse
import os
import re

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt

DEFAULT_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "default-academic-template.docx")

INLINE_RE = re.compile(r"(\*\*.+?\*\*|\*.+?\*)")
TRAILING_ASIDE_RE = re.compile(r"\s*\*\[[^\]]*\]\*\s*$")
CAPTION_RE = re.compile(r"^\*\*(Table|Fig|Figure)\b")
IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$")


def parse_inline_runs(text):
    """Split text into (text, bold, italic) run tuples on non-nested **bold**/*italic*."""
    runs = []
    pos = 0
    for m in INLINE_RE.finditer(text):
        if m.start() > pos:
            runs.append((text[pos:m.start()], False, False))
        token = m.group(0)
        if token.startswith("**"):
            runs.append((token[2:-2], True, False))
        else:
            runs.append((token[1:-1], False, True))
        pos = m.end()
    if pos < len(text):
        runs.append((text[pos:], False, False))
    if not runs:
        runs.append((text, False, False))
    return runs


def add_runs(paragraph, text, force_italic=False, mono=False):
    for run_text, bold, italic in parse_inline_runs(text):
        if not run_text:
            continue
        run = paragraph.add_run(run_text)
        run.bold = bold
        run.italic = italic or force_italic
        if mono:
            run.font.name = "Consolas"
            run.font.size = Pt(9)


def style_names(document):
    return {s.name for s in document.styles}


def heading_style_for(level, names):
    if level <= 2:
        return "Heading 1"
    if level == 3 and "Heading 3" in names:
        return "Heading 3"
    return "Heading 2"


def table_style_name(document):
    from docx.enum.style import WD_STYLE_TYPE
    table_styles = [s.name for s in document.styles if s.type == WD_STYLE_TYPE.TABLE]
    if "Table Grid" in table_styles:
        return "Table Grid"
    for name in table_styles:
        if name != "Normal Table":
            return name
    return None


def text_width(document):
    section = document.sections[0]
    return section.page_width - section.left_margin - section.right_margin


def is_table_separator(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def set_column_widths(table, header, rows, total_width):
    """Distribute total_width across columns proportional to each column's longest
    line (by character count), so wrapped cell text is not squeezed evenly across
    columns regardless of content - python-docx tables don't autofit on open."""
    ncols = len(header)
    weights = []
    for k in range(ncols):
        longest = len(header[k])
        for row in rows:
            if k < len(row):
                longest = max(longest, max((len(part) for part in row[k].split("\n")), default=0))
        weights.append(max(longest, 4))
    total_weight = sum(weights)
    table.autofit = False
    for k, weight in enumerate(weights):
        width = int(total_width * weight / total_weight)
        for row in table.rows:
            row.cells[k].width = width


def add_table(document, lines, i, style_name):
    header = split_row(lines[i])
    rows = []
    j = i + 2
    while j < len(lines) and lines[j].strip().startswith("|"):
        rows.append(split_row(lines[j]))
        j += 1

    table = document.add_table(rows=1 + len(rows), cols=len(header))
    if style_name:
        table.style = style_name
    for k, cell_text in enumerate(header):
        cell = table.rows[0].cells[k]
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
        add_runs(cell.paragraphs[0], cell_text)
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for r, row in enumerate(rows):
        for k, cell_text in enumerate(row):
            if k >= len(header):
                continue
            cell = table.rows[r + 1].cells[k]
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
            add_runs(cell.paragraphs[0], cell_text)
    set_column_widths(table, header, rows, text_width(document))
    return j


def add_image(document, alt_text, path, base_dir, width):
    img_path = path if os.path.isabs(path) else os.path.join(base_dir, path)
    if not os.path.exists(img_path):
        p = document.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_runs(p, "[missing image: %s]" % path, force_italic=True)
        return
    document.add_picture(img_path, width=width)
    document.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def render_body(document, md_text, base_dir):
    names = style_names(document)
    table_style = table_style_name(document)
    width = text_width(document)
    bib_style = "Bibliography" if "Bibliography" in names else "Normal"

    lines = md_text.replace("\r\n", "\n").split("\n")
    n = len(lines)
    i = 0
    title_used = False
    in_references = False

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped == "---":
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            level = len(m.group(1))
            heading_text = m.group(2).strip()
            if level == 1 and not title_used:
                p = document.add_paragraph(style="Title")
                add_runs(p, heading_text)
                title_used = True
            else:
                style = heading_style_for(level, names)
                p = document.add_paragraph(style=style)
                add_runs(p, heading_text)
            in_references = heading_text.strip().lower() == "references"
            i += 1
            continue

        if stripped.startswith("```"):
            i += 1
            code_lines = []
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            p = document.add_paragraph(style="Normal")
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            for k, code_line in enumerate(code_lines):
                if k > 0:
                    p.add_run().add_break()
                run = p.add_run(code_line if code_line else " ")
                run.font.name = "Consolas"
                run.font.size = Pt(8)
            continue

        if stripped.startswith(">"):
            p = document.add_paragraph(style="Normal")
            add_runs(p, stripped.lstrip(">").strip(), force_italic=True)
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < n and is_table_separator(lines[i + 1]):
            i = add_table(document, lines, i, table_style)
            continue

        m = IMAGE_RE.match(stripped)
        if m:
            add_image(document, m.group(1), m.group(2), base_dir, width)
            i += 1
            continue

        if CAPTION_RE.match(stripped):
            caption_text = TRAILING_ASIDE_RE.sub("", stripped)
            p = document.add_paragraph(style="Normal")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            add_runs(p, caption_text)
            i += 1
            continue

        if in_references:
            p = document.add_paragraph(style=bib_style)
            add_runs(p, stripped)
            i += 1
            continue

        p = document.add_paragraph(style="Normal")
        add_runs(p, stripped)
        i += 1


def clear_body(document):
    body = document.element.body
    sect_pr = body.find(qn("w:sectPr"))
    for child in list(body):
        if child is not sect_pr:
            body.remove(child)


def render(md_path, out_path, template_path):
    document = docx.Document(template_path)
    clear_body(document)

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    base_dir = os.path.dirname(os.path.abspath(md_path))
    render_body(document, md_text, base_dir)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    document.save(out_path)
    print("arti-docx: %s" % out_path)


def main():
    parser = argparse.ArgumentParser(description="Render a Markdown manuscript to a styled .docx")
    parser.add_argument("--md", required=True, help="path to the source Markdown file")
    parser.add_argument("--out", required=True, help="path to write the .docx to")
    parser.add_argument("--template", default=DEFAULT_TEMPLATE, help="style template .docx (default: ARTi's academic template)")
    args = parser.parse_args()
    render(args.md, args.out, args.template)


if __name__ == "__main__":
    main()
