"""Figure 3 (approach families by year, tasks) and Figure 4 (task x approach evidence map) from the aggregated CSVs.

    python.exe scripts/build_fig_classification.py --project P

Reads data/method-by-year.csv, data/task-counts.csv, data/task-method.csv (written by aggregate.py).
Writes figures/Fig_3_classification.png and figures/Fig_4_evidence-map.png at 320 dpi. The CSVs are the record of the numbers.
"""
import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_csv  # noqa: E402
from _plot import PALETTE, apply_style, shorten  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
a = ap.parse_args()
data = Path(a.project) / "data"
figs = Path(a.project) / "figures"
figs.mkdir(parents=True, exist_ok=True)
plt = apply_style()

# ---- Figure 3: (a) approach families by year, (b) tasks ------------------------------------------------------
mby = read_csv(data / "method-by-year.csv")
years = sorted({r["year"] for r in mby})
methods = []
for r in mby:
    if r["method"] not in methods:
        methods.append(r["method"])
totals = defaultdict(int)
for r in mby:
    totals[r["method"]] += int(r["n"])
methods.sort(key=lambda m: -totals[m])
tasks = read_csv(data / "task-counts.csv")[:8]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.7), gridspec_kw={"width_ratios": [1.15, 1]})
bottom = [0] * len(years)
for i, m in enumerate(methods):
    vals = [next((int(r["n"]) for r in mby if r["year"] == y and r["method"] == m), 0) for y in years]
    ax1.bar(years, vals, bottom=bottom, label=shorten(m, 28), color=PALETTE[i % len(PALETTE)], width=0.75, linewidth=0)
    bottom = [b + v for b, v in zip(bottom, vals)]
ax1.set_xlabel("Publication year")
ax1.set_ylabel("Included sources")
ax1.set_title("(a) Approach family by year", loc="left", fontweight="bold")
ax1.set_ylim(0, max(bottom) * 1.55)  # head-room so the legend never sits on a bar
ax1.legend(frameon=False, loc="upper left", ncol=2, handlelength=1, borderaxespad=0.2, columnspacing=1.0)
if len(years) > 8:
    ax1.set_xticks(years[:: max(1, len(years) // 8)])
ax1.tick_params(axis="x", labelrotation=0)

names = [shorten(t["task"], 30) for t in tasks][::-1]
vals = [int(t["n"]) for t in tasks][::-1]
ax2.barh(names, vals, color=PALETTE[0], height=0.65, linewidth=0)
for y, v in enumerate(vals):
    ax2.text(v + max(vals) * 0.015, y, str(v), va="center", fontsize=7)
ax2.set_xlabel("Included sources")
ax2.set_title("(b) Task addressed", loc="left", fontweight="bold")
ax2.set_xlim(0, max(vals) * 1.15)
fig.tight_layout(pad=0.6, w_pad=1.2)
fig.savefig(figs / "Fig_3_classification.png")
plt.close(fig)

# ---- Figure 4: task x approach evidence map ------------------------------------------------------------------
tm = read_csv(data / "task-method.csv")
task_names = [t["task"] for t in read_csv(data / "task-counts.csv")][:8]
method_names = methods[:7]
grid = [[sum(int(r["n"]) for r in tm if r["task"] == t and r["method"] == m) for m in method_names] for t in task_names]
fig, ax = plt.subplots(figsize=(7.2, 0.45 * len(task_names) + 1.1))
vmax = max(max(row) for row in grid) or 1
im = ax.imshow(grid, cmap="Blues", vmin=0, vmax=vmax, aspect="auto")
ax.set_xticks(range(len(method_names)), [shorten(m, 26) for m in method_names], rotation=25, ha="right")
ax.set_yticks(range(len(task_names)), [shorten(t, 34) for t in task_names])
for i, row in enumerate(grid):
    for j, v in enumerate(row):
        ax.text(j, i, str(v) if v else "", ha="center", va="center", fontsize=7, color="white" if v > vmax * 0.6 else "#222222")
ax.spines[:].set_visible(False)
ax.set_title("Sources per task and approach family (cells with no source are blank)", loc="left", fontweight="bold")
fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02, label="Sources")
fig.tight_layout(pad=0.6)
fig.savefig(figs / "Fig_4_evidence-map.png")
plt.close(fig)
print("ok: %s, %s" % (figs / "Fig_3_classification.png", figs / "Fig_4_evidence-map.png"))
