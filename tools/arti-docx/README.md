# arti-docx

Markdown -> styled `.docx` for journal manuscripts. Markdown source stays the
editable source of truth; the `.docx` is a snapshot rebuilt fresh from it on
every run - never a merge into an existing `.docx`'s content, the same
philosophy `arti-pdf/README.md` states for `arti-pdf`'s HTML/PDF output.

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

See the module docstring in `render.py` for the supported Markdown subset and
v1 non-goals (nested/numbered lists, footnotes, section-by-section merging).
Extend the converter for these if a document needs them, rather than reaching
for pandoc - the point is staying zero-manual-install, matching every other
`~/.arti` tool.
