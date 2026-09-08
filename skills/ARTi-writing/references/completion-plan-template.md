# Submission Completion Plan — template

Output: `writing\completion-plan.md` (source of truth, hand-maintained) rendered to
`writing\completion-plan.pdf` via the shared Markdown→A4-PDF pipeline documented in
`~/.arti/tools/arti-pdf/README.md`. Do not hand-roll a self-contained HTML file for this — the pipeline
already handles the print CSS (A4 page size, `break-inside: avoid` per phase, `print-color-adjust:
exact`, sized checkbox glyphs); this template only needs to specify the Markdown structure.

**Hand-maintained, not generated.** Compile it once from `idea\research-design.md`, the
Manuscript Blueprint, Journal Profile Blocks A/B, and the open `- [ ]` items in
`memory\todo-list.md` — then the researcher (or Claude, on request) edits it by hand as scope
firms up. It does not regenerate from `todo-list.md` on a schedule; the two artifacts have a
deliberate division of labour:

| Artifact | Scope | Update cadence |
|---|---|---|
| `completion-plan.md`/`.pdf` | frozen full scope to submission-ready | only when scope genuinely changes — re-render the PDF after each hand edit |
| `memory\todo-list.md` + `memory\status.md` | living session-to-session working state (checklist + narrative) | every session |

**Density target:** fits compactly — no hard page-count limit, let content decide. Use real
`☐`/`☑` glyphs directly in the Markdown cells (not `- [ ]` task-list syntax or HTML checkbox
inputs — see `~/.arti/tools/arti-pdf/README.md` for why).

## Precondition — Blueprint completeness gate

Before compiling this document, read the Manuscript Blueprint end-to-end. Every top-level section
(Introduction, Materials & Methods, Results & Discussion, Conclusion) must carry an explicit
figure/table decision — a specific display item, or an explicit "no display items needed" call,
never silence. If any section's decision is missing, **stop** and ask the researcher to decide it
in the Blueprint's Revision Notes first; do not compile the Figures & Tables Inventory around a
silent gap.

## Structure

```markdown
# [Paper Title] — Completion Plan

*Frozen [YYYY-MM-DD]. Update only when scope genuinely changes — see memory/status.md for
session-to-session state.*

## 1. Data Collection

| # | Item | Status |
|---|---|:---:|
| 1.1 | [one row per data-collection task, with target date/instrument if known] | ☐ |

## 2. Analysis Plan (per hypothesis)

| # | Item | Status |
|---|---|:---:|
| 2.1 | [test/analysis to run, tool, expected output — one row per hypothesis] | ☐ |

## 3. Figures & Tables Inventory

| # | Description | Status |
|---|---|:---:|
| 3.1 | [display item] | [create / redraw / verify] |

## 4. Remaining Manuscript Sections

| # | Item | Status |
|---|---|:---:|
| 4.1 | [section/subsection still to draft] | ☐ |

## 5. Pre-Submission Checks

| # | Item | Status |
|---|---|:---:|
| 5.1 | Journal allowances (word/figure/table limits) | ☐ |
| 5.2 | Reference verification | ☐ |
| 5.3 | IRB/ethics | ☐ |

## 6. Submission Package

| # | Item | Status |
|---|---|:---:|
| 6.1 | Cover letter | ☐ |
| 6.2 | Manuscript file (render with arti-docx — see below) | ☐ |
| 6.3 | Figures as separate files | ☐ |
| 6.4 | Supplementary | ☐ |
| 6.5 | Author forms | ☐ |
```

Render with:
```
python ~/.arti/tools/arti-pdf/render.py --md writing\completion-plan.md --out-dir writing
```

**Item 6.2, Manuscript file:** render `writing\manuscript_draft[N]_[date].md` to `.docx` with
`arti-docx` (`~/.arti/tools/arti-docx/`), the same "Markdown is truth, docx is a rebuilt snapshot"
philosophy as this plan's own PDF pipeline:
```
"~/.arti/python/python.exe" "~/.arti/tools/arti-docx/render.py" --md writing\manuscript_draft[N]_[date].md --template writing\manuscript-template.docx --out writing\manuscript_draft[N]_[date].docx
```
`--template` defaults to ARTi's shared academic template if the project has not saved its own
`writing\manuscript-template.docx` house-style copy yet.

## Change log
Keep this template's own history to a one-line-per-date list if it is ever revised; do not
document individual project plans here — those live in each project's own
`writing\completion-plan.md`.
