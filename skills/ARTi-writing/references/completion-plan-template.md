# Submission Completion Plan — template

Output file: `writing\completion-plan.html`. This is the skill family's first non-Markdown output.
**Self-contained rule, stated here because it has nowhere else to live:** the file must not
reference any external asset (no CDN scripts, no external stylesheets, no external images) — copy
this template's CSS inline and it will still render correctly if the file is opened alone, offline,
years from now.

**Hand-maintained, not generated.** Compile it once from `idea\experiment-blueprint.md`, the
Manuscript Blueprint, Journal Profile Blocks A/B, and the open `- [ ]` items in
`memory\todo-list.md` — then the researcher (or Claude, on request) edits it by hand as scope
firms up. It does not regenerate from `todo-list.md` on a schedule; the two artifacts have a
deliberate division of labour:

| Artifact | Scope | Update cadence |
|---|---|---|
| `completion-plan.html` | frozen full scope to submission-ready | only when scope genuinely changes |
| `memory\todo-list.md` | living session-to-session working state | every session |

**Density target:** one side of one printed sheet (A4). If content doesn't fit, cut detail, not
sections — every phase below should survive in at least skeleton form.

**Required CSS properties** (bake these into the `<style>` block, don't rely on browser defaults):
- `@media print { @page { size: A4; margin: 12mm; } }`
- `break-inside: avoid` on each phase group, so a group doesn't split across a page edge
- `print-color-adjust: exact` (and `-webkit-print-color-adjust: exact`) so phase-group background
  tints actually print instead of being dropped to white
- Checkbox glyphs sized for a pen — a real `☐`/`☑` character or a bordered `<span>` box at least
  ~4mm square when printed, not a tiny native `<input type=checkbox>`

## Structure

```html
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Completion Plan — [Paper Title]</title>
<style>
  /* screen + print styles inline here — see required properties above */
</style>
</head>
<body>

<h1>[Paper Title] — Completion Plan</h1>
<p><em>Frozen [YYYY-MM-DD]. Update only when scope genuinely changes — see memory/todo-list.md for
session-to-session state.</em></p>

<section class="phase">
  <h2>1. Data Collection</h2>
  <!-- ☐ one line per data-collection task, with target date/instrument if known -->
</section>

<section class="phase">
  <h2>2. Analysis Plan (per hypothesis)</h2>
  <!-- ☐ one line per hypothesis: test/analysis to run, tool, expected output -->
</section>

<section class="phase">
  <h2>3. Figures &amp; Tables Inventory</h2>
  <!-- table: # | description | status (create / redraw / verify) -->
</section>

<section class="phase">
  <h2>4. Remaining Manuscript Sections</h2>
  <!-- ☐ one line per section/subsection still to draft -->
</section>

<section class="phase">
  <h2>5. Pre-Submission Checks</h2>
  <!-- ☐ journal allowances (word/figure/table limits) ☐ reference verification ☐ IRB/ethics -->
</section>

<section class="phase">
  <h2>6. Submission Package</h2>
  <!-- ☐ cover letter ☐ manuscript file ☐ figures as separate files ☐ supplementary ☐ author forms -->
</section>

</body>
</html>
```

## Change log
Keep this template's own history to a one-line-per-date list if it is ever revised; do not
document individual project plans here — those live in each project's own
`writing\completion-plan.html`.
