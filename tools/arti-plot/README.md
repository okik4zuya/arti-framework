# arti-plot (interim pattern, no shared renderer yet)

Plot lane for ARTi-figure. First real use: Paper SLR Nanobubble in Reaction,
`figures/scripts/build_fig3_corpus-trend.py` (2026-09-16) — a data-driven
bar-chart trend figure built from a project's `arti-lit.db`.

Unlike the diagram and table lanes, plots don't fit a shared JSON-spec +
renderer split well: a diagram's content is geometry (nodes/edges an author
positions by hand), and a table's content is already tabular — but a plot's
content is *derived* from project data (a SQL query, a CSV, a classification
pass) via chart-specific logic (binning, aggregation, color-by-series) that
differs per figure. Forcing that into one generic spec format would just
relocate the same code into a JSON blob. So there is no `render.py` here yet
— the interim pattern is a **per-figure, per-project script**, not a shared
tool:

- One script per plot, at `figures/scripts/build_<Fig_N>_<slug>.py` in the
  paper project (sibling to the project's other figure outputs).
- Run via the vendored interpreter from the project root (relative paths in
  the script assume this):
  `"~/.arti/python/python.exe" "figures/scripts/build_<Fig_N>_<slug>.py"`
  (Mac/Linux: `~/.arti/python/bin/python3`).
- The script owns its own data pull (query `arti-lit.db` directly, or read a
  `data/*.csv`/`.json` the project already has), any classification/binning
  logic, and the `matplotlib` rendering — save the PNG straight to
  `figures/Fig_N_<slug>.png` at `dpi=300`. No intermediate `.drawio` or `.md`
  step, since a plot's final form (unlike a table) is the rendered image.
- Emit the aggregated data the plot is built from as a sibling file under
  `data/` (e.g. `data/domain-trend-by-year.csv`) — not just the image — so
  the chart's numbers are checkable and the script is re-runnable, not a
  one-off.
- Keep the script itself as a real, committed file (not a scratch/temp file)
  once the figure is finalized — it is the plot's reproducibility record,
  the way a JSON spec is for the diagram/table lanes.

Same verification loop as the other two lanes: read the rendered PNG back
and eyeball it before calling the figure done, and register it in
`figures/figure-register.md` on first render (update in place on re-render).

`matplotlib` is required and available in the vendored interpreter; it is
listed in `requirements.txt`. If a second project needs a plot with a
genuinely reusable shape (e.g. another year-binned two-series trend chart),
that is the signal to extract a real shared `render.py` here instead of
copy-pasting the script — not before, per the original "lowest priority,
build when real plot data exists" scoping.
