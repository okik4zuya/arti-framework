<!-- arti-claude-template: v1 -->
# {{PROJECT_NAME}} — Project Instructions

ARTi research-paper project. This project's `memory/` is the single source of truth — never read
or write the default `~/.claude/projects/.../memory/` for it.

Read every session: `memory/MEMORY.md`, `memory/todo-list.md`, `memory/status.md`,
`~/.arti/memory/working-preferences.md`, `inbox/index.md`.

## Folders

| Folder | Holds |
|---|---|
| `idea/` | ARTi-idea outputs: `gap-map.md`, `idea-canvas.md`, `journal-target-sheet.md`, `handoff.md`, `research-design.md`/`.pdf` (frozen A4 print snapshot). One paper = no topic slugs. |
| `writing/` | ARTi-writing outputs: `journal-profile_[journal-abbreviation].md`, `manuscript-blueprint.md`, `scratchbook.md`, `manuscript_draft[N]_[date].md`, `iteration-log.md`, `references.md` (generated), `completion-plan.md`/`.pdf` (hand-maintained, frozen scope to submission). |
| `literature/` | One key per source (`author-year[a\|b]`, e.g. `kaw-2016`) across: `exports/` (raw, never renamed), `fulltext/` (PDF + `.md`, named by key), `search-log.md` (one row per search round, hand-seeded), `library.md` (generated export backed by `arti-lit.db` — canonical bibliography, superset incl. screened-out; readable directly, but mutations go through `arti-lit`). |
| `data/` | Raw + processed data. `data/instruments/` = instruments, pretest/posttest packets, scoring keys — placement follows what a file *is*, not that Methods cites it. |
| `figures/` | Plots, images, diagrams + `figures/figure-register.md` (seeded on first `ARTi-figure` use, not at scaffold). |
| `submission/` | Cover letter, rebuttal, growth log, journal-formatted export, supplementary files. |
| `inbox/` | Researcher-owned raw-idea inbox — see below. |

Voice Profile is cross-project: `~/.arti/voice-profiles/`, not `writing/`.

## `inbox/` — the one folder the researcher edits directly

Everything else is Claude-managed. `inbox/index.md` columns:
`File · Tipe · Status · One-line hook · Dipakai di · Date added`.

- **Tipe = Ide** (default) — a note *about* something to do/decide. Triage renames it
  `YYMMDD_STATUS_<slug>.md` (date = triaged, not written), status one of **OK** (ingested
  somewhere) / **SKIP** (reviewed, unused) / **PARKED** (good, not this paper → `idea-bank add`
  entry if a research idea, `~/.arti/inbox/` if about the ARTi framework itself).
- **Tipe = Narasi** — verbatim researcher prose that *is* the content. Never summarize, rewrite,
  or condense it; triage fills only `One-line hook` and `Dipakai di` (e.g. `ebook Bab 1`). Never
  archived, exempt from the cap; its `OK` means "used in a deliverable," and the file stays put.
- **Every triage event** also runs `idea-index upsert` (see `arti-db` invocation below).
- **Caps:** untriaged files (no prefix) uncapped, never archived. Triaged files capped at 10
  outside `inbox/archive/`; past that, move the oldest in, then run `idea-index archive` with the
  affected row ids and a one-line summary — it marks those rows archived and appends the summary
  to the aggregator's Change log in one call.
- **Findability:** if asked about `inbox/` content absent from the live table, grep
  `inbox/archive/*.md` — only index rows are deleted, never files.

## Memory rules

- `memory/` holds exactly three files flat (`MEMORY.md`, `todo-list.md`, `status.md`). Every topic
  file goes in `memory/memories/`, read on demand.
- `MEMORY.md` = index, pointers only, one line each — never content.
- `todo-list.md` = contiguous `- [ ]`/`- [x]` items only, no narrative.
- `status.md` = narrative: one "Current state" block overwritten in place each session (never
  stacked), archive below.
- One file per topic — update it rather than creating a near-duplicate; read it before advising on
  that topic. Link with `[[slug]]`, don't restate across files.
- **Timestamps:** run a date command, never guess. Set `created` on creation, `updated` on every
  write, add one `## Change log` line. That is the whole ritual — no history file, no change log
  of the index.

Frontmatter for every memory file:

```
---
name: kebab-case-slug
description: one-line summary, specific enough to judge relevance later
metadata:
  type: project | user | feedback | reference
  created: yyyy-mm-dd HH:mm
  updated: yyyy-mm-dd HH:mm
---
```

...content, then `## Change log` at the bottom.

## Session start

Surface, unasked: any open question a memory file recorded ("ask whether X"), and any untriaged
`inbox/index.md` rows.

## Session end

Fired by *any* phrasing meaning "we're done" — "update memory", "update status", "end session",
and the like:

1. Update the relevant memory file(s).
2. Overwrite `status.md`'s "Current state" block.
3. Check off / add `todo-list.md` items.
4. If a phase boundary was crossed (idea complete / writing started / submitted / published),
   run `project upsert` for this project's row.
5. Append the session log to `~/.arti/workflow-sessions/` — **preserve turn order; never reorder
   or flatten by topic.** The sequence in which topics arose is itself the feedback signal for how
   ARTi's own stages should be sequenced. Synthesized findings live in
   `~/.arti/memory/memories/arti-workflow-profile.md`.
6. Promote any correction on *how* to work to `~/.arti/memory/working-preferences.md`.

## Cross-project discovery

"Do I have research about X" / "have I looked into X" / "did I already study X" is never a
local-memory-only question. Run `idea-bank search <keywords>` and `project list` first — plus
`idea-index list` if it's about framework/skill ideas rather than research topics. `project
list`'s `summary` field is free text covering each project's actual memory sub-topics — read it to
shortlist the one or two projects that plausibly hold the topic, *then* open only those projects'
own `MEMORY.md` and follow the pointer to the right `memories/*.md` file, instead of opening every
candidate project's `MEMORY.md` by hand. A direct read of `project-index.md` — including its
`Summary` column — is an acceptable substitute for running `project list` when the file is already
open or being scanned for other reasons; the CLI is only required for anything that *writes*.

## `arti-db` invocation

Every `project`/`idea-bank`/`idea-index` command above runs as:
`"~/.arti/python/python.exe" "~/.arti/tools/arti-db/cli.py" <subcommand> ...` (Mac/Linux:
`~/.arti/python/bin/python3`). Each call prints one JSON object (`{"ok": true, ...}` or
`{"ok": false, "error": ...}`); see `~/.arti/tools/arti-db/README.md` for the full subcommand
surface. Never hand-edit `project-index.md`, `research-idea-bank.md`, or `idea-index.md`
directly — all three are generated exports, overwritten on every write.

## `arti-lit` invocation

Every `library`/`refs generate` command for this project's `literature/` layer runs as:
`"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" <subcommand> ... --project PATH`
(Mac/Linux: `~/.arti/python/bin/python3`). Each call prints one JSON object (`{"ok": true, ...}` or
`{"ok": false, "error": ...}`); see `~/.arti/tools/arti-lit/README.md` for the full subcommand
surface. Unlike `arti-db`, this is per-project, not a cross-project singleton. Never hand-edit
`library.md` or `writing/references.md` directly — both are generated exports, overwritten on
every write.

## `arti-pdf-ingest` invocation

Batch-converts PDFs to `literature\fulltext\` Markdown and registers each conversion in `arti-lit`
(status `fulltext`) in one pass, instead of ingesting one PDF at a time:
`"~/.arti/python/python.exe" "~/.arti/tools/arti-pdf-ingest/cli.py" ingest --project PATH
--manifest PATH` (Mac/Linux: `~/.arti/python/bin/python3`). Requires each manifest row's `key` to
already exist in `library.md` — it never creates new library rows. See
`~/.arti/tools/arti-pdf-ingest/README.md` for the manifest format.

<!-- arti: local additions below — preserved on regeneration -->
