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
