# arti-pdf

Markdown → A4 PDF pipeline for frozen reference documents (e.g. Research Design, Submission
Completion Plan) — zero-install, no pandoc/wkhtmltopdf dependency, uses whichever of Edge/Chrome is
already on the machine. Same convention as `arti-render`/`arti-table`: a pure-stdlib Python
converter, vendored under `~/.arti/tools/`.

## What this is for

A **frozen, print-ready A4 reference** — a document the researcher keeps at hand during execution
(at the bench, during a meeting, printed on paper), not a living file they'll keep editing on
screen. The Markdown source stays the editable source of truth; the PDF is a snapshot rendered
from it. Re-render only when the source genuinely changes — this is not a live-sync/watch pipeline.

## Pipeline

1. **Author** a plain Markdown file — headings, paragraphs, tables, checklist rows using real
   glyphs `☐` (open) / `☑` (done) written directly in the Markdown cell, not HTML `<input
   type="checkbox">` or a task-list `- [ ]` syntax (task-list checkboxes render as native form
   controls in some intermediate renderers and print poorly).
2. **Convert** to a print-styled intermediate HTML file (kept alongside the PDF as an inspectable
   artifact, not deleted):
   - `@page { size: A4; margin: ... }`
   - `table, tr, .no-break { break-inside: avoid; }` so a table row never splits across a page
     boundary
   - `* { print-color-adjust: exact; -webkit-print-color-adjust: exact; }` so header shading/colors
     actually print instead of being stripped to white
   - Checkbox glyphs sized up slightly (`font-size: 1.1em` or similar) since `☐`/`☑` render small
     at body text size
   - No dependency on a specific font being installed — stick to a generic stack
     (`Arial, Helvetica, sans-serif`)
3. **Render** to PDF via a headless browser already on the machine — no pandoc, no wkhtmltopdf, no
   extra install:
   ```
   <edge-or-chrome> --headless --disable-gpu --print-to-pdf="<out>.pdf" --print-to-pdf-no-header "<intermediate>.html"
   ```
   Prefer Edge (`msedge.exe`) if present, fall back to Chrome (`chrome.exe`) — both accept the same
   flags. Check known Windows install paths for each; this needs no network access and no browser
   profile.
4. **Density target**: "fits compactly," not "must fit one page." There is no hard page-count
   limit — let the content decide how many pages it needs. Don't compress line-height or font-size
   to chase a page count.

## Usage

`render.py` mirrors `arti-render`/`arti-table`'s existing convention: zero-install, pure-stdlib
Markdown→HTML step (handles headings, paragraphs, pipe tables with alignment rows, bold/italic/
inline-code — this is intentionally not a full CommonMark implementation, just enough for the plain
structure these documents use), then shells out to whichever of Edge/Chrome it finds for the actual
PDF print step.

```
python render.py --md <path/to/source.md> --out-dir <dir>
```

Produces `<name>.pdf` next to `<name>.html` (the inspectable intermediate) in `--out-dir`. If a
document's Markdown ever needs something the converter doesn't handle (nested lists, images,
footnotes), extend the converter — don't reach for pandoc as a workaround; the whole point is
staying zero-install.

## Consumers

- ARTi-idea's Research Design (`idea/research-design.md` → `.pdf`)
- ARTi-writing's Submission Completion Plan (`writing/completion-plan.md` → `.pdf`)

Both reference this file rather than duplicating the recipe in their own template docs.

## Change log
- 2026-09-06 — Moved here from `~/.arti/memory/print-to-pdf.md`: this is tool documentation with no
  researcher-specific content, so it belongs with the tool (tracked in git, shipped to every
  install) rather than in the private, git-ignored `memory/` folder.
