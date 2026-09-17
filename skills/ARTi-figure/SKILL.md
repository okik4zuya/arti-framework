---
name: ARTi-figure
description: >
  Generate manuscript figures and tables via the vendored ~/.arti Python interpreter: diagrams and
  tables from a JSON spec, plots from a per-project matplotlib script (interim pattern, no shared
  renderer yet — see arti-plot/README.md). Use this skill when a researcher wants a study-design
  diagram, flowchart, or other box-and-arrow figure, a manuscript table, a data-driven chart
  (bar/line/trend/bibliometric plot), or asks to regenerate/edit one from its spec. Triggers
  include: "make a figure for this", "draw a diagram of the study design", "regenerate Fig_N",
  "edit the flowchart spec", "turn this into a .drawio file", "make a table of this", "convert this
  table image to Markdown", "plot X per year", "chart the trend of X vs Y", "classify these papers
  and show the trend". Diagrams produce an editable `.drawio` file, not a final image — draw.io
  itself is where wrapping, sizing, and export to PNG/PDF get fixed by hand. Tables produce
  editable Markdown table syntax, ready to paste into the manuscript source. Plots produce a final
  PNG directly plus the aggregated data file it was built from.
---

# ARTi-figure Skill

v1 scope: **three lanes — diagram, table, and plot.**

**Diagram lane.** A figure is authored as a JSON spec (nodes, edges, styles) and rendered to an
editable `.drawio` file by `arti-render`. There is no auto-layout, no auto-fix loop, and no direct
PNG output pipeline on purpose — draw.io's own editor is where a box that overflows or an edge
that routes badly gets fixed by hand, once, visually. This skill produces the `.drawio`; the
researcher (or Claude, if asked, using the draw.io desktop app when present) does the rest.

**Table lane.** A table is authored as a JSON spec (columns, alignment, rows) and rendered to a
Markdown table by `arti-table`. Unlike the diagram lane, the output is the final artifact, not an
intermediate to hand-edit visually — a manuscript whose source is Markdown wants a real editable
table in the prose, not a rasterized image. Route a request here (not to the diagram lane) whenever
the ask is comparison/summary data with rows and columns, including "convert this table image/PNG
into something I can edit" — back-derive the spec from the image's visible structure, render it,
then diff the rendered table against the source image by eye (column order, cell content, header
row) before treating it as done.

**Plot lane.** For a data-driven chart (bar/line/trend/bibliometric figure, anything whose content
comes from aggregating project data rather than hand-placed geometry or a simple rows-and-columns
table), there is no shared JSON-spec renderer the way diagrams and tables have — see
`~/.arti/tools/arti-plot/README.md` for why (each plot's data pull and aggregation logic is too
project-specific to fit one generic spec) and the interim pattern instead: write a standalone,
per-figure Python script at `figures/scripts/build_<Fig_N>_<slug>.py` in the paper project that
pulls its own data (query the project's `arti-lit.db`, or read a `data/*.csv`/`.json` already in
the project), does whatever classification/binning the chart needs, and renders straight to
`figures/Fig_N_<slug>.png` at `dpi=300` with `matplotlib` (available in the vendored interpreter;
listed in `~/.arti/tools/requirements.txt`). Emit the aggregated numbers behind the chart to a
sibling file under `data/` as well, not just the image — the point is a re-runnable, checkable
script, not a one-off render. Keep the script as a committed file once the figure is finalized;
it is this lane's reproducibility record, the way a JSON spec is for diagram/table. Register the
resulting figure in `figures/figure-register.md` exactly as for the other two lanes, and run the
same read-back verification loop (below) before calling it done. If a second project ever needs a
plot with a genuinely reusable shape, that's the signal to extract a real shared `render.py` into
`arti-plot` — not before.

## Tooling location

Everything this skill needs lives under `~/.arti` (`C:\Users\<user>\.arti\` on Windows, `~/.arti`
on Mac/Linux) — the cross-project ARTi tooling home, installed separately via `install.ps1` /
`install.sh` from the `arti` repo (see `ARTi-setup` for the researcher-content side of `~/.arti`;
this skill only touches the tooling side).

- **Diagram renderer:** `~/.arti/tools/arti-render/render.py`
- **Table renderer:** `~/.arti/tools/arti-table/render.py`
- **Interpreter:** `~/.arti/python/python.exe` (Windows) or `~/.arti/python/bin/python3`
  (Mac/Linux) — the vendored python-build-standalone interpreter, **not** whatever `python` or
  `python3` resolves to on the researcher's `PATH`. Always invoke the renderer through the
  vendored interpreter's full path so figure rendering doesn't depend on (or fight with) whatever
  else is installed system-wide.

If `~/.arti/python/` doesn't exist yet, tell the researcher to run the installer
(`~/.arti/install.ps1` or `~/.arti/install.sh`) first — this skill does not install Python itself.

## Figure spec format (diagram lane)

A figure spec is a single JSON file, conventionally `figures/<Fig_N>.json` inside the paper
project (sibling to the project's other figure outputs, e.g. `figures/Fig_1.drawio`,
`figures/Fig_1.png`). Colors, fonts, and line weights in a new spec's `defaults`/`styles` blocks
should start from `~/.arti/memory/figure-style.md` (the cross-project visual baseline shared with every
other figure) rather than being invented per figure — see that file for the palette and floors,
and the project's own `writing/journal-profile_*.md` Block A/B for any journal-specific dpi/
column-width override to apply at render or export time. Shape:

```json
{
  "figure": "Fig_1",
  "canvas": { "width": 850, "height": 1100 },
  "defaults": { "fontFamily": "...", "fontSize": 20, "strokeWidth": 2, "padX": 20 },
  "styles": {
    "dark":  { "fill": "#4D4D4D", "stroke": "#000000", "text": "#FFFFFF" }
  },
  "nodes": [
    { "id": "n1", "x": 217, "y": 10, "w": 410, "h": 120, "style": "dark",
      "lines": [ { "t": "line of text", "b": true } ] }
  ],
  "edges": [
    { "from": "n1", "to": "n2", "route": "v" },
    { "from": "n1", "to": "n3", "route": "vhv", "midY": 360 }
  ]
}
```

- `nodes[].lines[].b` (bold) is optional; omit for regular weight.
- `edges[].route` is `"v"` (straight, no waypoints) or `"vhv"` (vertical-horizontal-vertical,
  requires `midY` — the horizontal-run y-coordinate).
- draw.io does its own text wrapping inside a node — the spec only needs geometry (`x`, `y`, `w`,
  `h`), not wrapped line lengths.

Before writing a new spec from scratch, check whether an existing figure in the project's
`figures/` folder has a similar structure (e.g. a flowchart) and adapt it rather than
reinventing node/edge conventions per figure.

## Table spec format (table lane)

A table spec is a single JSON file, conventionally `figures/<Table_N>.json`. Shape:

```json
{
  "table": "Table_1",
  "caption": "Comparison of ...",
  "columns": ["Property", "Column A", "Column B"],
  "align": ["left", "left", "left"],
  "rows": [
    ["Row label", "cell", "cell"],
    ["Row label", "cell", "cell"]
  ]
}
```

- `align[]` is one entry per column: `"left"`, `"center"`, or `"right"` — controls the Markdown
  table's separator-row marker, not text alignment inside a rendering engine.
- `caption` is optional; when present it's emitted as a bolded `**Table_N.** caption` line above
  the table, matching how this project's manuscript captions its figures.
- Deriving a spec from an existing table image: read the image, transcribe its header row and
  every cell into `columns`/`rows` preserving the source's own column order — don't reorder or
  reword cells for tidiness.

## Rendering

Diagram lane:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-render/render.py" --spec "figures/Fig_1.json" --out-dir "figures"
```

Table lane:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-table/render.py" --spec "figures/Table_1.json" --out-dir "figures"
```

(swap in the Mac/Linux interpreter path when running there). The diagram renderer writes
`figures/Fig_1.drawio`; if the draw.io desktop app is installed, it also attempts a PNG export at
4x scale via its CLI (`figures/Fig_1.png`), skipping and saying so if draw.io isn't found. The
table renderer writes `figures/Table_1.md` directly — no export step, since Markdown is the final
form.

**Verification loop — run both steps every time a figure or table renders, not just the first
time:**
1. **Read the rendered output back, don't just prompt the researcher to look.** For a diagram,
   open the exported PNG (or export one if the draw.io CLI is available) and view it directly; for
   a table, read the generated `.md` and compare it cell-by-cell against the source spec or
   original image. Catching an overflowing box, a misrouted edge, or a transposed column is
   Claude's job before the researcher ever opens the file.
2. **Check legibility/overflow against the target journal's print constraints, not just default
   canvas size.** Pull print width/column count and figure dpi/resolution requirements from this
   project's `writing/journal-profile_*.md` (Block A/B) when they're recorded there; if that block
   says "not confirmed," say so explicitly rather than silently assuming a default, and flag it as
   an open item rather than guessing a number.
Only after both checks pass (or their gaps are explicitly flagged) is a render considered done —
"I rendered it" and "I verified it" are different claims; don't conflate them in the response to
the researcher.

## Maintaining the figure register

After a figure or table's **first** successful render in a project, add it to
`figures/figure-register.md` (seed it from `ARTi-figure/references/figure-register-template.md`
if the file doesn't exist yet) — one row per figure/table: spec path, status (`draft`/`final`),
where it's cited in the manuscript, and the date last rendered. Update the row (not append a new
one) on every subsequent re-render or status change; add a new row only for a genuinely new
figure/table.

## Editing an existing figure or table

To change a figure or table, edit its JSON spec (add/move/resize nodes, change text/cells, add
edges/rows) and re-render — don't hand-edit the `.drawio` XML or the generated `.md` table
directly unless the researcher has already made manual fixes there that aren't worth re-encoding
into the spec. If the researcher has made manual edits and asks for a further *content* change,
ask whether they want the spec updated to match (losing nothing) or whether it's faster to edit
the rendered output by hand this once.
