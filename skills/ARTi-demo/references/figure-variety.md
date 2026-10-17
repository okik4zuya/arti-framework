# Figure variety (phase 7)

Four reference images in `templates/` show the range to aim for. They are look-and-feel references from a real paper,
not templates to copy: never reuse their data, labels or artwork. Open each one with Read before building figures, then
choose a different *form* for each demo figure so the set does not read as one chart type repeated.

| Reference | What it shows | Take from it |
|---|---|---|
| `Fig_1_materials.png` | Three panels of three different chart types: horizontal grouped bars with value labels, a log-scale line chart with end labels instead of a legend and a dashed partial-year tail, and a band-edge style bar chart with reference lines | Mixed panel types in one figure; the item of interest in one accent colour, all others grey; direct labels; dashed tail for an incomplete year; horizontal reference lines with labels on the right |
| `Fig_3_trend.png` | Two stacked panels sharing a year axis; stacked bars by category, total printed above each bar | Same x-axis, two different groupings of the same records; totals on top; colour-blind-safe categorical palette with a grey "other" |
| `Fig_4_band_edges.png` | Panel (a) is a drawn mechanism scheme (numbered steps, arrows, energy levels); panel (b) is a data chart with gradient bars, rotated labels inside the bars, per-item marker shapes and a marker legend | A drawn scheme above a data chart; numbered circles for steps; marker shape as a second encoding; labels inside bars |
| `graphical-abstract.png` | A circular cycle: three curved arrows connect three illustrated nodes, with an overlapping three-circle diagram in the centre | A graphical abstract can be a cycle or a central overlap, not only left-to-right zones |

## Rules for the demo

1. **Every figure uses a different form.** No two figures in the run may share the same chart type or layout. Pick from:
   grouped or stacked bars, horizontal bars with value labels, log-scale lines with end labels, heatmap (approach by
   field), slope or dumbbell chart, bubble chart, lollipop, waffle or proportion strip, stacked area, small multiples,
   Venn or overlap diagram, cycle or hub-and-spoke scheme, timeline.
2. **At least one multi-panel figure mixes two chart types** (for example bars plus lines, as in `Fig_1_materials.png`), and
   at least one figure is a drawn scheme or diagram (PRISMA flow counts).
3. **The graphical abstract is not the default three-zone strip.** Choose a layout from: cycle, hub-and-spoke, central overlap
   (Venn), funnel with branching outcomes, timeline arc. Keep the ARTi-figure rule: title, 1-2 word labels, numbers and
   units, no sentences. Draw simple icons in inline SVG (shapes, arrows, stacked sheets, magnifier); no stock or copied
   artwork.
4. **One accent colour per figure for the thing the story is about**, everything else grey or a muted tint (as in the
   reference figures); categorical palettes only where categories are the point. Take colours from `figure-style.md`.
5. **Label directly** (end-of-line labels, value labels on bars, labels inside bars) rather than a detached legend whenever it fits.
6. **Vary what is plotted from the data the run already wrote** (`data/*.csv`, `data/prisma-counts.json`): year trend,
   approach by field, evidence access (full text vs abstract), source database, label co-occurrence. Never invent a series.
7. The existing scripts (`build_fig_landscape.py`, `build_fig_classification.py`) give the default forms; when a form would
   repeat another figure, change the chart type in the script call or write a short per-project matplotlib script
   (`ARTi-figure/references/plot-lane.md`) instead.
8. Still bound by the caps: 4 numbered figures plus the graphical abstract, 2 render iterations per figure.
