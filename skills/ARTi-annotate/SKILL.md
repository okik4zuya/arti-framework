---
name: ARTi-annotate
description: >
  Resolve the researcher's inline comments and suggested edits in any Markdown file (manuscript,
  scratchbook, notes, anything) — the annotations they made in the ARTi dashboard's file preview,
  stored in the file itself as CriticMarkup (`{==span==}{>>#a1 open | note<<}`). Use when the
  researcher says "resolve my comments", "address the annotations", "apply my comments to the
  manuscript", "go through the highlights", "what did I comment on", or points at a md file with
  `{==` / `{>>#a` markers in it. Also use to strip annotation markup before a file is treated as
  final text. Do NOT use for drafting new prose or reviewer-response work (ARTi-writing) or for
  Word/PDF comments — this is only the inline `{>>#aN ...<<}` format.
---

# ARTi-annotate Skill

The researcher highlights text in the dashboard's md preview and attaches a note ("change this
word", "make this paragraph more concise"). Your job in a later session is to act on every open
note, then leave the result visible for their review. Format and CLI: `~/.arti/tools/arti-annotate/README.md`.

All tool calls use the vendored interpreter by full path (never a bare `python`):
`"~/.arti/python/python.exe" ~/.arti/tools/arti-annotate/cli.py ...` (Windows) or
`~/.arti/python/bin/python3 ~/.arti/tools/arti-annotate/cli.py ...` (Mac/Linux).

## Resolve all comments

1. **List**: `cli.py list FILE --status open`. Each item has `id`, `kind` (`comment` or
   `suggestion`), the span (`text`, or `old`/`new`), and `note`. If the researcher named one file,
   use it; otherwise look for files containing `{>>#a` in the project and ask which.
2. **Comments** (`kind: comment`): read the note as an instruction about the highlighted span and
   rewrite *only that span*, in the surrounding voice (if the file is a manuscript and a voice
   profile exists, follow it; keep `[LIT: key]`/`[OWN]` tags, citations, numbers and units intact
   unless the note says otherwise). Apply it with
   `cli.py revise FILE ID --text "<new span>"` — never hand-edit the markup, so `was` (the original)
   and the note are preserved. If the note asks for something you cannot do from the file (needs
   new data, a source you don't have), leave it `open` and say why in your reply.
3. **Suggestions** (`kind: suggestion`): these are the researcher's own proposed replacements.
   Do not change them; they accept or reject them in the dashboard. Only touch one if its note
   explicitly asks you to (e.g. "polish my wording"), by editing the text between `~>` and `~~}`.
4. **Never** run `accept`, `revert` or `strip --write` on the researcher's behalf. Revised spans
   show yellow in the dashboard until they accept (or revert) each one; that review step is the
   point.
5. **Report**: one line per annotation — id, what changed (or why it stayed open). Note anything
   you changed outside a span because a rewrite forced it (e.g. a pronoun in the next sentence);
   prefer not to, and if unavoidable say so.

## Other requests

- "What did I comment on?" — `cli.py list FILE` and summarize; change nothing.
- "Make a clean copy / export / submit": run `cli.py strip FILE` (prints clean prose; comments keep
  their current span, suggestions keep the old text) and use that output, or `strip FILE --write`
  only when the researcher asks for the file itself to be cleaned.
- Reading a file for facts or quoting it: ignore the markup (`strip`), but treat open notes as the
  researcher's pending intent, not as content.

## Rules

- Annotations are the researcher's words about their text; never delete or rewrite a note.
- Keep one annotation per span; do not nest or overlap them, and do not add new annotations
  yourself unless asked (the dashboard creates them).
- If `cli.py` reports `annotation aN not found`, re-run `list`; the file changed (or the
  dashboard saved) since you read it.
