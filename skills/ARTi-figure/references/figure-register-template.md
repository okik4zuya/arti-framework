# Figure Register

One row per figure or table produced by `ARTi-figure` for this project. Update it whenever a
spec is rendered for the first time, a figure is promoted from draft to final, or a citation
location changes — not on every re-render of an unchanged spec.

| Figure | Lane | Spec path | Status | Cited in (section/line) | Last rendered |
|---|---|---|---|---|---|
| Fig_1 | diagram | `figures/Fig_1.json` | draft | Methods | 2026-09-05 |
| Fig_2 | composite | `figures/src/Fig_2.html` | draft | Results | 2026-10-14 |

- **Lane** is `diagram`, `table`, `plot` or `composite`; the spec path is the JSON spec, the plot
  script, or the `.html` source respectively.
- **Status** is `draft` or `final` — `final` means the researcher has visually approved the
  rendered output and no further layout changes are expected.
- **Cited in** names the manuscript section (and line, if the draft uses one-line paragraphs) the
  figure is referenced from — update it when a draft moves the citation, not just when the figure
  changes.
- **Last rendered** is the date `arti-render`/`arti-table` last produced output from this spec,
  not the date the row was last edited.
- A figure with no spec file (hand-drawn, imported, or manually edited `.drawio` with no JSON
  source) still gets a row — leave **Spec path** as `(none — manual)` rather than omitting it.
