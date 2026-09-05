---
name: ARTi-figure
description: >
  Generate manuscript figures (diagrams for now — table and plot lanes are stubs, not yet built)
  from a JSON spec, via the vendored ~/.arti Python interpreter. Use this skill when a researcher
  wants a study-design diagram, flowchart, or other box-and-arrow figure for a manuscript, or asks
  to regenerate/edit one from its spec. Triggers include: "make a figure for this", "draw a
  diagram of the study design", "regenerate Fig_N", "edit the flowchart spec", "turn this into a
  .drawio file". Produces an editable `.drawio` file, not a final image — draw.io itself is where
  wrapping, sizing, and export to PNG/PDF get fixed by hand.
---

# ARTi-figure Skill

v1 scope: **diagram lane only**. A figure is authored as a JSON spec (nodes, edges, styles) and
rendered to an editable `.drawio` file by `arti-render`. There is no auto-layout, no auto-fix
loop, and no direct PNG output pipeline on purpose — draw.io's own editor is where a box that
overflows or an edge that routes badly gets fixed by hand, once, visually. This skill produces the
`.drawio`; the researcher (or Claude, if asked, using the draw.io desktop app when present) does
the rest.

Table lane (`arti-table`) and plot lane (`arti-plot`) are stubs — not implemented, no scope here.
Don't attempt to build them under this skill without the researcher explicitly asking to extend
scope; they're deferred on purpose (no plot data exists yet in any active project).

## Tooling location

Everything this skill needs lives under `~/.arti` (`C:\Users\<user>\.arti\` on Windows, `~/.arti`
on Mac/Linux) — the cross-project ARTi tooling home, installed separately via `install.ps1` /
`install.sh` from the `arti` repo (see `ARTi-setup` for the researcher-content side of `~/.arti`;
this skill only touches the tooling side).

- **Renderer:** `~/.arti/tools/arti-render/render.py`
- **Interpreter:** `~/.arti/python/python.exe` (Windows) or `~/.arti/python/bin/python3`
  (Mac/Linux) — the vendored python-build-standalone interpreter, **not** whatever `python` or
  `python3` resolves to on the researcher's `PATH`. Always invoke the renderer through the
  vendored interpreter's full path so figure rendering doesn't depend on (or fight with) whatever
  else is installed system-wide.

If `~/.arti/python/` doesn't exist yet, tell the researcher to run the installer
(`~/.arti/install.ps1` or `~/.arti/install.sh`) first — this skill does not install Python itself.

## Figure spec format

A figure spec is a single JSON file, conventionally `figures/<Fig_N>.json` inside the paper
project (sibling to the project's other figure outputs, e.g. `figures/Fig_1.drawio`,
`figures/Fig_1.png`). Shape:

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

## Rendering

Run the vendored interpreter directly against `render.py`:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-render/render.py" --spec "figures/Fig_1.json" --out-dir "figures"
```

(swap in the Mac/Linux interpreter path when running there). This writes `figures/Fig_1.drawio`.
If the draw.io desktop app is installed, `render.py` also attempts a PNG export at 4x scale via
its CLI (`figures/Fig_1.png`); if draw.io isn't found, it says so and skips the PNG — open the
`.drawio` file by hand and export instead.

**After rendering, always open (or ask the researcher to open) the resulting `.drawio` and check
it visually** — this is not an auto-fix loop. Text overflow, awkward wrapping, or an edge that
routes through a box are expected occasionally and get fixed in draw.io's editor, not by tweaking
the spec blindly until it looks right in your head.

## Editing an existing figure

To change a figure, edit its JSON spec (add/move/resize nodes, change text, add edges) and
re-render — don't hand-edit the `.drawio` XML directly unless the researcher has already made
manual layout fixes in draw.io that aren't worth re-encoding into the spec. If the researcher has
made manual draw.io edits and asks for a further *content* change, ask whether they want the spec
updated to match (losing nothing) or whether it's faster to edit the `.drawio` by hand this once.
