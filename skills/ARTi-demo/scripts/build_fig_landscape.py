"""Figure 2: the OpenAlex landscape as a three-panel composite (a: works per year, b: open-access status, c: top venues).

    python.exe scripts/build_fig_landscape.py --project P

Reads data/landscape-year.csv, landscape-oa.csv, landscape-source.csv (aggregate.py; panels whose file is missing are
skipped). Writes the panel PNGs to figures/panels/, scaffolds figures/src/Fig_2.html from the multi-panel template with
`arti-compose --new` (so the page size, base CSS and checks are the template's), points it at the panels and renders
figures/Fig_2.pdf and figures/Fig_2.png. The compose WARN/FAIL lines are printed as they are; read them, then look at the PNG.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import PY, TOOLS, read_csv  # noqa: E402
from _plot import PALETTE, apply_style, shorten  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
a = ap.parse_args()
project = Path(a.project)
data = project / "data"
panels = project / "figures" / "panels"
panels.mkdir(parents=True, exist_ok=True)
plt = apply_style(7.5)
made = {}

# (a) works per year, whole width
p = data / "landscape-year.csv"
if p.exists():
    rows = read_csv(p)
    yrs = [r["year"] for r in rows]
    vals = [int(r["works"]) for r in rows]
    fig, ax = plt.subplots(figsize=(7.2, 1.95))
    ax.bar(yrs, vals, color=PALETTE[0], width=0.72, linewidth=0)
    for x, v in zip(yrs, vals):
        ax.text(x, v + max(vals) * 0.015, "{:,}".format(v), ha="center", va="bottom", fontsize=6.5)
    ax.set_ylabel("Works in OpenAlex")
    ax.set_xlabel("Publication year")
    ax.set_ylim(0, max(vals) * 1.15)
    if len(yrs) > 14:
        ax.set_xticks(yrs[:: max(1, len(yrs) // 12)])
    fig.tight_layout(pad=0.5)
    fig.savefig(panels / "Fig_2a.png")
    plt.close(fig)
    made["a"] = "Fig_2a.png"

# (b) open-access status
p = data / "landscape-oa.csv"
if p.exists():
    rows = read_csv(p)
    names = [r["oa_status"] for r in rows]
    vals = [int(r["works"]) for r in rows]
    tot = sum(vals) or 1
    fig, ax = plt.subplots(figsize=(3.5, 1.95))
    ax.barh(names[::-1], [100.0 * v / tot for v in vals][::-1], color=PALETTE[2], height=0.65, linewidth=0)
    for i, v in enumerate(vals[::-1]):
        ax.text(100.0 * v / tot + 1, i, "%.0f%%" % (100.0 * v / tot), va="center", fontsize=6.5)
    ax.set_xlabel("Share of works (%)")
    ax.set_xlim(0, 100)
    fig.tight_layout(pad=0.5)
    fig.savefig(panels / "Fig_2b.png")
    plt.close(fig)
    made["b"] = "Fig_2b.png"

# (c) top venues
p = data / "landscape-source.csv"
if p.exists():
    rows = read_csv(p)[:8]
    names = [shorten(r["source"], 26) for r in rows][::-1]
    vals = [int(r["works"]) for r in rows][::-1]
    fig, ax = plt.subplots(figsize=(3.5, 1.95))
    ax.barh(names, vals, color=PALETTE[1], height=0.65, linewidth=0)
    for i, v in enumerate(vals):
        ax.text(v + max(vals) * 0.02, i, "{:,}".format(v), va="center", fontsize=6.5)
    ax.set_xlabel("Works")
    ax.set_xlim(0, max(vals) * 1.2)
    ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    fig.tight_layout(pad=0.5)
    fig.savefig(panels / "Fig_2c.png")
    plt.close(fig)
    made["c"] = "Fig_2c.png"

if not made:
    print("FAIL: no landscape CSV found in data/ (run aggregate.py after the arti-search count calls)")
    sys.exit(1)

src = project / "figures" / "src" / "Fig_2.html"
src.parent.mkdir(parents=True, exist_ok=True)
compose = str(TOOLS / "arti-compose" / "compose.py")
if src.exists():
    src.unlink()
r = subprocess.run([PY, compose, "--new", "multi-panel", "--src", str(src)], capture_output=True, text=True)
if r.returncode != 0 or not src.exists():
    print("FAIL: compose --new failed: " + (r.stdout + r.stderr)[-400:])
    sys.exit(1)
html = src.read_text(encoding="utf-8")
for tag, ph, ext in (("a", "PANEL_A.svg", "Fig_2a.png"), ("b", "PANEL_B.png", "Fig_2b.png"), ("c", "PANEL_C.png", "Fig_2c.png")):
    if tag in made:
        html = html.replace(ph, "../panels/" + ext)
    else:  # drop the whole figure element of a missing panel
        start = html.rfind("<figure", 0, html.find(ph))
        end = html.find("</figure>", html.find(ph)) + len("</figure>")
        html = html[:start] + html[end:]
# the template draws a scale bar example on panel (c); a bar chart needs none
html = html.replace('<div class="scalebar"><i style="width:10mm"></i>200 nm</div>', "")
src.write_text(html, encoding="utf-8")

r = subprocess.run([PY, compose, "--src", str(src), "--out-dir", str(project / "figures")], capture_output=True, text=True)
print((r.stdout + r.stderr).strip())
sys.exit(0 if r.returncode == 0 else 1)
