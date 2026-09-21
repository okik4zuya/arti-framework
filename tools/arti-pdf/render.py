#!/usr/bin/env python3
"""
arti-pdf - Markdown -> print-styled HTML -> A4 PDF

Pure stdlib Markdown->HTML step (headings, paragraphs, pipe tables with
alignment rows, bold/italic/inline-code) followed by a headless Edge/Chrome
print-to-pdf pass. No pandoc, no wkhtmltopdf, no third-party packages.
See ~/.arti/tools/arti-pdf/README.md for the recipe this formalizes.

This is intentionally not a full CommonMark implementation - just enough
structure (headings/paragraphs/tables/checklists) for frozen reference
documents like a Research Design or a Submission Completion Plan. Extend the
converter if a document needs more (nested lists, images, footnotes) rather
than reaching for pandoc - the point is staying zero-install.

Usage:
    python render.py --md ../../../Paper/writing/completion-plan.md --out-dir ../../../Paper/writing
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import sys


def convert_inline(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def is_table_separator(line):
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c) for c in cells)


def parse_table(lines, i):
    header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
    align_cells = [c.strip() for c in lines[i + 1].strip().strip("|").split("|")]
    aligns = []
    for c in align_cells:
        if c.startswith(":") and c.endswith(":"):
            aligns.append("center")
        elif c.endswith(":"):
            aligns.append("right")
        elif c.startswith(":"):
            aligns.append("left")
        else:
            aligns.append("")

    rows = []
    j = i + 2
    while j < len(lines) and "|" in lines[j] and lines[j].strip():
        rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
        j += 1

    out = ['<table>', "  <thead>", "    <tr>"]
    for k, h in enumerate(header):
        style = f' style="text-align:{aligns[k]}"' if k < len(aligns) and aligns[k] else ""
        out.append(f"      <th{style}>{convert_inline(h)}</th>")
    out.append("    </tr>")
    out.append("  </thead>")
    out.append("  <tbody>")
    for row in rows:
        out.append("    <tr>")
        for k, cell in enumerate(row):
            style = f' style="text-align:{aligns[k]}"' if k < len(aligns) and aligns[k] else ""
            out.append(f"      <td{style}>{convert_inline(cell)}</td>")
        out.append("    </tr>")
    out.append("  </tbody>")
    out.append("</table>")
    return "\n".join(out), j


def md_to_html_body(md_text):
    lines = md_text.replace("\r\n", "\n").split("\n")
    out = []
    i = 0
    n = len(lines)
    para = []

    def flush_para():
        if para:
            out.append(f"<p>{convert_inline(' '.join(para))}</p>")
            para.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_para()
            i += 1
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            level = len(m.group(1))
            out.append(f"<h{level}>{convert_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < n and is_table_separator(lines[i + 1]):
            flush_para()
            table_html, next_i = parse_table(lines, i)
            out.append(table_html)
            i = next_i
            continue

        if stripped.startswith(">"):
            flush_para()
            out.append(f"<blockquote>{convert_inline(stripped.lstrip('> ').strip())}</blockquote>")
            i += 1
            continue

        if re.match(r"^[-*]\s+", stripped):
            flush_para()
            items = []
            while i < n and re.match(r"^[-*]\s+", lines[i].strip()):
                items.append(convert_inline(re.sub(r"^[-*]\s+", "", lines[i].strip())))
                i += 1
            out.append("<ul>" + "".join(f"<li>{it}</li>" for it in items) + "</ul>")
            continue

        para.append(stripped)
        i += 1

    flush_para()
    return "\n".join(out)


PAGE_CSS = """
@page { size: A4; margin: 16mm 14mm; }
* { print-color-adjust: exact; -webkit-print-color-adjust: exact; box-sizing: border-box; }
body { font-family: Arial, Helvetica, sans-serif; font-size: 10.5pt; line-height: 1.35; color: #111; margin: 0; }
h1 { font-size: 16pt; margin: 0 0 4mm 0; }
h2 { font-size: 12.5pt; margin: 6mm 0 2mm 0; break-after: avoid; }
h3 { font-size: 11pt; margin: 4mm 0 1.5mm 0; break-after: avoid; }
p { margin: 0 0 2.5mm 0; }
em { color: #444; }
table { width: 100%; border-collapse: collapse; margin: 0 0 4mm 0; break-inside: avoid; }
th, td { border: 0.4pt solid #999; padding: 1.2mm 2mm; text-align: left; vertical-align: top; font-size: 9.5pt; }
th { background: #e8e8e8; font-weight: bold; }
tr { break-inside: avoid; }
ul { margin: 0 0 2.5mm 4mm; padding: 0 0 0 4mm; }
li { margin-bottom: 1mm; }
blockquote { margin: 0 0 3mm 0; padding-left: 3mm; border-left: 2pt solid #999; color: #333; }
td, th { font-variant-numeric: normal; }
"""

def wrap_html(title, body_html):
    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
{body_html}
</body>
</html>
"""


def find_browser():
    if sys.platform == "win32":
        candidates = [
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    else:
        candidates = [shutil.which("microsoft-edge"), shutil.which("google-chrome"), shutil.which("chromium")]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def html_to_pdf(html_path, pdf_path):
    """Prints html_path to pdf_path via headless Edge/Chrome. Returns True if
    the PDF was actually produced, False if no browser was found or printing
    failed."""
    browser = find_browser()
    if not browser:
        return False

    result = subprocess.run(
        [
            browser,
            "--headless",
            "--disable-gpu",
            f"--print-to-pdf={pdf_path}",
            "--print-to-pdf-no-header",
            "--no-pdf-header-footer",
            html_path,
        ],
        capture_output=True,
        text=True,
    )
    if not os.path.exists(pdf_path):
        print(f"  PDF print failed (exit {result.returncode}). stderr:\n{result.stderr}")
        return False
    return True


def render(md_path, out_dir):
    md_path = os.path.abspath(md_path)
    name = os.path.splitext(os.path.basename(md_path))[0]
    os.makedirs(out_dir, exist_ok=True)
    out_dir = os.path.abspath(out_dir)

    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    m = re.search(r"^#\s+(.*)$", md_text, re.MULTILINE)
    title = m.group(1).strip() if m else name

    body_html = md_to_html_body(md_text)
    full_html = wrap_html(title, body_html)

    html_path = os.path.join(out_dir, f"{name}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"arti-pdf: {name}")
    print(f"  [ok] {html_path}")

    browser = find_browser()
    if not browser:
        print("  no headless Edge/Chrome found - HTML written, open it and print to PDF by hand.")
        return html_path

    pdf_path = os.path.join(out_dir, f"{name}.pdf")
    if html_to_pdf(html_path, pdf_path):
        print(f"  [ok] {pdf_path}")
    return pdf_path


def main():
    parser = argparse.ArgumentParser(description="Render a Markdown reference doc to a print-styled A4 PDF")
    parser.add_argument("--md", required=True, help="path to the source Markdown file")
    parser.add_argument("--out-dir", default=".", help="output directory for the .html and .pdf")
    args = parser.parse_args()
    render(args.md, args.out_dir)


if __name__ == "__main__":
    main()
