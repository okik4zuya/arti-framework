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

Pure drop-and-forget capture, no structure required to add a file. No index, no rename, no
archiving — presence in the folder *is* the "still open" signal. Everything else here is
Claude-managed.

- **Session start:** glob `inbox/*.md` and surface whatever is there — that's the whole discovery
  mechanism.
- **Reviewing a file** ends one of three ways, decided in conversation, no ceremony: (a) worth
  keeping — fold it into the right place (a `memories/` topic file, `idea-bank add` if it's a
  research idea, or `~/.arti/inbox/` if it's about the ARTi framework itself) and delete the raw
  file; (b) not worth keeping — delete it; (c) still undecided — leave it in place.
- **Verbatim researcher prose that *is* the content** (not a note *about* something — ebook
  narrative, landing-page copy) is never summarized, rewritten, or condensed, and isn't deleted
  once used. Record where it's been used with one `<!-- used-in: ... -->` comment at the top of the
  file itself instead of a separate index row.
- A capture worth cross-project tracking can be added to `~/.arti/inbox/idea-index.md` via
  `idea-index upsert` (see `arti-db` invocation below) — an available action, not a step every file
  goes through.

## Memory rules

- `memory/` holds exactly three files flat (`MEMORY.md`, `todo-list.md`, `status.md`). Every topic
  file goes in `memory/memories/`, read on demand.
- `MEMORY.md` = index, pointers only, one line each — never content.
- `todo-list.md` = contiguous `- [ ]`/`- [x]` items only, one line each, no narrative continuation
  — link `[[slug]]` for context instead of inlining it. No `## Change log` section. A phase's
  checked items get deleted once it's closed and captured in a topic file — this file tracks
  outstanding work, not history.
- `status.md` = narrative, but only as a pointer: one "Current state" block overwritten in place
  each session (never stacked), 2-4 sentences naming what changed and a `[[topic-file]]` link for
  every detail — the topic file carries the report, not this block. No Archive section and no
  `## Change log` section here either; the linked topic file's own change log and git history
  already cover it.
- One file per topic — update it rather than creating a near-duplicate; read it before advising on
  that topic. Link with `[[slug]]`, don't restate across files.
- **Timestamps:** run a date command, never guess. Set `created` on creation, `updated` on every
  write. Every memory file except `status.md`/`todo-list.md` adds one `## Change log` line on
  write — no history file, no change log of the index.

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

Surface, unasked: any open question a memory file recorded ("ask whether X"), and any file sitting
untriaged in `inbox/`.

## Session end

Fired by *any* phrasing meaning "we're done" — "update memory", "update status", "end session",
and the like:

1. Update the relevant memory file(s).
2. **Only if the session moved outstanding work or produced a state change worth recording:**
   overwrite `status.md`'s "Current state" pointer and/or check off / add `todo-list.md` items. A
   session that was pure discussion, research, or Q&A with no checklist or state change skips both
   files entirely — there is nothing to overwrite.
3. If a phase boundary was crossed (idea complete / writing started / submitted / published),
   run `project upsert` for this project's row.
4. Write any correction on *how* to work straight into `~/.arti/memory/working-preferences.md`, the
   same turn it's given — never deferred to session end.

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

## `arti-jfinder` invocation

Every `journal`/`scope` command run as: `"~/.arti/python/python.exe"
"~/.arti/tools/arti-jfinder/cli.py" <subcommand> ...` (Mac/Linux: `~/.arti/python/bin/python3`).
No `--project` flag — it is a cross-project singleton like `arti-db`. Each call prints one JSON
object (`{"ok": true, ...}` or `{"ok": false, "error": ...}`); see
`~/.arti/tools/arti-jfinder/README.md` for the full subcommand surface. Backed by a
researcher-downloaded Scimago snapshot — if `journal search`/`get` returns `{"ok": false}` because
the database is empty or missing, tell the researcher to download the current-year export from
Scimago and run `ingest --file PATH --year YYYY`, then fall back to general knowledge rather than
blocking.

<!-- arti: local additions below — preserved on regeneration -->
