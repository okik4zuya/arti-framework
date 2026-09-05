#!/usr/bin/env python3
"""
arti-render - figure spec (JSON) -> .drawio

Pure stdlib port of render.ps1. Zero-install: no third-party packages, no
browser, no external binary required to produce the .drawio file. Emits only
the editable .drawio - open it in draw.io to view, export, or fix by hand.
There is no auto-fix loop here on purpose: draw.io's own editor is where
that happens.

Usage:
    python render.py --spec ../../figures/src/Fig_1.json --out-dir ../../figures/out

Args:
    --spec     path to the figure spec JSON (required)
    --out-dir  directory for the generated .drawio (created if missing, default: .)
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def esc_xml(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def fmt_num(n):
    if isinstance(n, float) and n.is_integer():
        return str(int(n))
    return str(n)


def render(spec_path, out_dir):
    spec_path = os.path.abspath(spec_path)
    with open(spec_path, "r", encoding="utf-8") as f:
        s = json.load(f)

    name = s["figure"]
    os.makedirs(out_dir, exist_ok=True)
    out_dir = os.path.abspath(out_dir)

    print(f"arti-render: {name}  ({s['canvas']['width']} x {s['canvas']['height']})")

    lines = []
    lines.append('<mxfile host="arti-render" version="28.0.6">')
    lines.append(f'  <diagram name="{esc_xml(name)}" id="arti-{name}">')
    lines.append(
        '    <mxGraphModel dx="2182" dy="1158" grid="1" gridSize="10" guides="1" '
        'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        f'pageWidth="{s["canvas"]["width"]}" pageHeight="{s["canvas"]["height"]}" '
        'math="0" shadow="0">'
    )
    lines.append("      <root>")
    lines.append('        <mxCell id="0" />')
    lines.append('        <mxCell id="1" parent="0" />')

    d = s["defaults"]
    by_id = {n["id"]: n for n in s["nodes"]}

    # edges first, so they sit behind the boxes
    i = 0
    for e in s.get("edges", []):
        i += 1
        style = (
            "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
            "html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;"
            f"entryDy=0;strokeWidth={d['strokeWidth']};fontSize={d['fontSize']};"
        )
        lines.append(
            f'        <mxCell id="e{i}" style="{style}" edge="1" parent="1" '
            f'source="{e["from"]}" target="{e["to"]}">'
        )
        if e.get("route") == "vhv":
            a = by_id[e["from"]]
            b = by_id[e["to"]]
            ax = a["x"] + a["w"] / 2
            bx = b["x"] + b["w"] / 2
            lines.append('          <mxGeometry relative="1" as="geometry">')
            lines.append('            <Array as="points">')
            lines.append(f'              <mxPoint x="{fmt_num(ax)}" y="{e["midY"]}" />')
            lines.append(f'              <mxPoint x="{fmt_num(bx)}" y="{e["midY"]}" />')
            lines.append("            </Array>")
            lines.append("          </mxGeometry>")
        else:
            lines.append('          <mxGeometry relative="1" as="geometry" />')
        lines.append("        </mxCell>")

    for n in s["nodes"]:
        st = s["styles"][n["style"]]
        parts = []
        for ln in n["lines"]:
            t = esc_xml(ln["t"])
            if ln.get("b"):
                parts.append(f"&lt;b&gt;{t}&lt;/b&gt;")
            else:
                parts.append(t)
        value = "&lt;br&gt;".join(parts)
        cell_style = (
            "text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;"
            f"strokeColor={st['stroke']};strokeWidth={d['strokeWidth']};"
            f"fontSize={d['fontSize']};spacingLeft={d['padX']};spacingRight={d['padX']};"
            f"fillColor={st['fill']};fontColor={st['text']};"
        )
        lines.append(
            f'        <mxCell id="{n["id"]}" value="{value}" style="{cell_style}" '
            'vertex="1" parent="1">'
        )
        lines.append(
            f'          <mxGeometry x="{n["x"]}" y="{n["y"]}" width="{n["w"]}" '
            f'height="{n["h"]}" as="geometry" />'
        )
        lines.append("        </mxCell>")

    lines.append("      </root>")
    lines.append("    </mxGraphModel>")
    lines.append("  </diagram>")
    lines.append("</mxfile>")

    drawio_path = os.path.join(out_dir, f"{name}.drawio")
    with open(drawio_path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(lines) + "\r\n")
    print(f"  [ok] {drawio_path}")

    # --- optional PNG, only if the draw.io desktop app happens to be installed --
    # This is a convenience, not a dependency: if the drawio binary is missing we
    # just skip it and say so - no browser fallback, no chasing another renderer.
    drawio_exe = find_drawio_exe()
    if drawio_exe:
        png_path = os.path.join(out_dir, f"{name}.png")
        err_log = os.path.join(tempfile.gettempdir(), "arti-drawio-cli.log")
        with open(err_log, "w", encoding="utf-8") as errf:
            subprocess.run(
                [drawio_exe, "-x", "-f", "png", "-s", "4", "-o", png_path, drawio_path],
                stderr=errf,
            )
        if os.path.exists(png_path):
            print(f"  [ok] {png_path}  (scale 4x, via draw.io CLI)")
        else:
            print(f"  draw.io CLI export failed - open {drawio_path} by hand and export instead.")
    else:
        print(f"  draw.io desktop not found - skipping PNG. Open {drawio_path} in draw.io to export yourself.")

    return drawio_path


def find_drawio_exe():
    if sys.platform == "win32":
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", ""), "draw.io", "draw.io.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "draw.io", "draw.io.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "draw.io", "draw.io.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = ["/Applications/draw.io.app/Contents/MacOS/draw.io"]
    else:
        candidates = []
        which = shutil.which("drawio")
        if which:
            candidates.append(which)
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def main():
    parser = argparse.ArgumentParser(description="Render a figure spec (JSON) to .drawio")
    parser.add_argument("--spec", required=True, help="path to the figure spec JSON")
    parser.add_argument("--out-dir", default=".", help="directory for the generated .drawio")
    args = parser.parse_args()
    render(args.spec, args.out_dir)


if __name__ == "__main__":
    main()
