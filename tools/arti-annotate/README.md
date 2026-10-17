# arti-annotate

Inline comments and suggested edits written into any `.md` file itself, as CriticMarkup with a short
id. The dashboard's md preview creates them (select text -> Comment / Suggest edit); the
`ARTi-annotate` skill has Claude resolve them in a later session; the dashboard shows Claude's
revisions in yellow until the researcher accepts or reverts each one.

Pure stdlib Python, run by full path (`~/.arti/python/python.exe cli.py ...`). `annot.py` is the
parser/mutator; `dashboard/lib/arti-annotate.js` is its JS mirror, and `fixtures.json` is the
contract both must pass (`test_annot.py`; dev-only `test_annot_js.js`, needs Node, not required to
run anything).

## Format

```
{==span==}{>>#a3 open | note<<}                              comment, not yet handled
{==new span==}{>>#a3 revised | was "old span" | note<<}      Claude rewrote the span
{~~old~>new~~}{>>#a4 open | note<<}                          user's suggested replacement
```

- `#aN` is unique per file (next free number). Status is `open` or `revised`.
- `was` is a JSON string holding the span text from before Claude's first revision; `note` is
  optional free text. Newlines in notes become spaces; `<<}` inside a note or `was` is escaped.
- A span must not contain `==}` (comment) or `~>` / `~~}` (suggestion), and annotations never nest
  or overlap.
- Markup inside fenced code blocks and inline code is ignored, and a bare `{==x==}` without a
  `{>>#aN ...<<}` block is not an annotation.

## Lifecycle

| Action | open comment | revised comment | suggestion |
|---|---|---|---|
| `accept` | keep span, drop markup | keep (new) span, drop markup | apply `new` |
| `revert` | keep span, drop markup | restore `was` | keep `old` |
| `revise` (Claude) | rewrite span, mark `revised`, keep `was` | rewrite again, original `was` kept | n/a |

`strip` = clean prose: every comment keeps its current span, every suggestion keeps the old text.
Anything that treats the file as final text (PDF export, docx export, submission) should use it.

## CLI

```
cli.py list FILE [--status open|revised]     JSON of annotations, in file order
cli.py revise FILE ID --text "new span"       (or --text-file PATH)
cli.py accept FILE ID | revert FILE ID
cli.py strip FILE [--write]                   print clean prose, or rewrite the file
```

Mutating commands rewrite FILE in place (UTF-8, line endings preserved). Python API: `parse`,
`strip`, `accept`, `revert`, `revise`, `add_comment`, `add_suggestion`, `next_id`.

## Used by

`ARTi-annotate` (resolve procedure), the dashboard preview (create/accept/revert, side panel, PDF
export strips markup), `arti-docx` (`render.py` strips markup before building the .docx), and any skill that must read a file as final text.
