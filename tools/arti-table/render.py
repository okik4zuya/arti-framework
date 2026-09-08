#!/usr/bin/env python3
"""
arti-table - table spec (JSON) -> editable Markdown table

Pure stdlib, same pattern as arti-render (arti-figure's diagram lane): a JSON
spec in, an editable text output out, no rasterization. The manuscript source
for this project family is Markdown, so a table belongs in the prose as real
Markdown table syntax - not a rendered image - so it can be edited, diffed,
and pasted directly into a draft.

Usage:
    python render.py --spec ../../figures/table-1.json --out-dir ../../figures
"""
import argparse
import json
import os


def esc_cell(s):
    s = str(s)
    return s.replace("|", "\\|").replace("\n", " ")


def col_width(cells):
    return max((len(esc_cell(c)) for c in cells), default=3)


def align_marker(a, width):
    a = (a or "left").lower()
    if a == "center":
        return ":" + "-" * max(width - 2, 1) + ":"
    if a == "right":
        return "-" * max(width - 1, 1) + ":"
    return "-" * width


def render(spec_path, out_dir):
    spec_path = os.path.abspath(spec_path)
    with open(spec_path, "r", encoding="utf-8") as f:
        s = json.load(f)

    name = s["table"]
    columns = s["columns"]
    rows = s.get("rows", [])
    align = s.get("align", ["left"] * len(columns))
    caption = s.get("caption")

    os.makedirs(out_dir, exist_ok=True)
    out_dir = os.path.abspath(out_dir)

    print(f"arti-table: {name}  ({len(columns)} cols x {len(rows)} rows)")

    widths = [
        col_width([columns[i]] + [r[i] for r in rows])
        for i in range(len(columns))
    ]

    def fmt_row(cells):
        padded = [esc_cell(c).ljust(widths[i]) for i, c in enumerate(cells)]
        return "| " + " | ".join(padded) + " |"

    lines = []
    if caption:
        lines.append(f"**{name}.** {caption}")
        lines.append("")
    lines.append(fmt_row(columns))
    lines.append(
        "| "
        + " | ".join(align_marker(align[i], widths[i]) for i in range(len(columns)))
        + " |"
    )
    for r in rows:
        lines.append(fmt_row(r))

    md_path = os.path.join(out_dir, f"{name}.md")
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  [ok] {md_path}")
    return md_path


def main():
    parser = argparse.ArgumentParser(description="Render a table spec (JSON) to a Markdown table")
    parser.add_argument("--spec", required=True, help="path to the table spec JSON")
    parser.add_argument("--out-dir", default=".", help="directory for the generated .md")
    args = parser.parse_args()
    render(args.spec, args.out_dir)


if __name__ == "__main__":
    main()
