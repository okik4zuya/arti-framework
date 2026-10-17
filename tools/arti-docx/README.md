# arti-docx

Markdown -> styled `.docx` for journal manuscripts. Markdown source stays the
editable source of truth; the `.docx` is a snapshot rebuilt fresh from it on
every run - never a merge into an existing `.docx`'s content, the same
philosophy `arti-convert/README.md` states for `arti-convert pdf`'s HTML/PDF output.

Usage:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-docx/render.py" \
  --md path/to/manuscript.md \
  --out path/to/manuscript.docx \
  --template path/to/style-template.docx   # optional, defaults to assets/default-academic-template.docx
```

## Zotero citations (`--cite zotero`)

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-docx/render.py" \
  --md manuscript.md --out manuscript.docx --cite zotero --project path/to/paper-project
```

Each `[LIT: key]` (or `[LIT: k1, k2]`) in the Markdown becomes a Zotero `ADDIN ZOTERO_ITEM
CSL_CITATION` field, and the `## References` section becomes one `ADDIN ZOTERO_BIBL` field
(a hand-written list there is replaced; with no `## References` heading, one is appended).
Metadata is read from `<project>/literature/arti-lit.db`'s `csl_json` column — fill it first with
`arti-lit library enrich`. Any cited key that is unknown or has no `csl_json` aborts the render
with the full list of problem keys; nothing is emitted silently empty.

There is no CSL engine: the text cached inside each field is an author-year placeholder
(`(Kaw et al., 2016)`) that is only right until the researcher opens the file in Word with Zotero
and clicks **Refresh**, which re-formats everything in the style stored in the file
(`--cite-style`, default `http://www.zotero.org/styles/apa`; change it in Zotero's Document
Preferences for a journal style). Items carry local placeholder Zotero URIs, so Zotero may note
they are not in the user's library. `--template` defaults to
`assets/default-academic-template-zotero.docx` in this mode; a custom template without a
`docProps/custom.xml` part loses the stored style preference (Zotero asks on first use).
Field structure: `memory/memories/zotero-docx-field-format.md`. Default `--cite none` is
unchanged.

The template supplies styles, section properties (A4, margins, continuous
line numbering), and the page-number footer - it is never a content source.
A project can keep its own house-style copy (e.g. `writing/manuscript-template.docx`)
and pass it via `--template`; `assets/default-academic-template.docx` is the
ARTi-wide fallback for a paper with no template of its own yet.

**Annotations never reach the .docx.** Before rendering, `render.py` runs `arti-annotate`'s `strip` on the Markdown
(comments keep their current span, suggestions keep the old text) and prints how many annotations it left out and
how many are still open. The source `.md` keeps them, so resolving and re-rendering can go on.

**House style (every project, any template).** Both default templates use Arial throughout. Tables get the
three-line look (rule on top and bottom, one rule under the header row, no vertical or inner lines) unless the
template defines its own table style (anything other than "Table Grid"/"Normal Table"). Cell text is single
spaced and left aligned, 10 pt shrinking to 8 pt (7 pt as a last resort); column widths follow the content, and
the header row repeats across pages. A table that does not fit portrait at 8 pt goes into its own landscape
section together with its caption (the caption line directly before the table), and the next content returns to
portrait. Page numbering and the footer continue across the section breaks.

**Layout check (developer aid).** `python preview.py manuscript.docx` renders the file to PDF and PNG pages in a
`preview/` folder next to it, through LibreOffice and the vendored poppler, so a layout change can be looked at.
LibreOffice is not shipped with ARTi; without it the script says so and exits 0. It is a rough stand-in for
Word, never evidence about Zotero fields, and it does not modify the `.docx` (never save a manuscript from
LibreOffice: it rewrites the Zotero fields).

See the module docstring in `render.py` for the supported Markdown subset and
v1 non-goals (nested/numbered lists, footnotes, section-by-section merging).
Extend the converter for these if a document needs them, rather than reaching
for pandoc - the point is staying zero-manual-install, matching every other
`~/.arti` tool.
