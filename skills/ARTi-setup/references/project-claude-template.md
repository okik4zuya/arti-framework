<!-- arti-claude-template: v1 -->
# {{PROJECT_NAME}} — Project Instructions

ARTi research-paper project. This project's `memory/` is the single source of truth — never read
or write the default `~/.claude/projects/.../memory/` for it.

Read every session: `memory/MEMORY.md`, `memory/todo-list.md`, `memory/status.md`,
`~/.arti/memory/working-preferences.md`, `wdyt/index.md`.

## Folders

| Folder | Holds |
|---|---|
| `idea/` | ARTi-idea outputs: `gap-map.md`, `idea-canvas.md`, `journal-target-sheet.md`, `handoff.md`, `research-design.md`/`.pdf` (frozen A4 print snapshot). One paper = no topic slugs. |
| `writing/` | ARTi-writing outputs: `journal-profile_[journal-abbreviation].md`, `manuscript-blueprint.md`, `scratchbook.md`, `manuscript_draft[N]_[date].md`, `iteration-log.md`, `references.md` (generated), `completion-plan.md`/`.pdf` (hand-maintained, frozen scope to submission). |
| `literature/` | One key per source (`author-year[a\|b]`, e.g. `kaw-2016`) across: `exports/` (raw, never renamed), `fulltext/` (PDF + `.md`, named by key), `search-log.md` (one row per search round), `library.md` (canonical bibliography, superset incl. screened-out). |
| `data/` | Raw + processed data. `data/instruments/` = instruments, pretest/posttest packets, scoring keys — placement follows what a file *is*, not that Methods cites it. |
| `figures/` | Plots, images, diagrams + `figures/figure-register.md` (seeded on first `ARTi-figure` use, not at scaffold). |
| `submission/` | Cover letter, rebuttal, growth log, journal-formatted export, supplementary files. |
| `wdyt/` | Researcher-owned raw-idea inbox — see below. |

Voice Profile is cross-project: `~/.arti/voice-profiles/`, not `writing/`.

## `wdyt/` — the one folder the researcher edits directly

Everything else is Claude-managed. `wdyt/index.md` columns:
`File · Tipe · Status · One-line hook · Dipakai di · Date added`.

- **Tipe = Ide** (default) — a note *about* something to do/decide. Triage renames it
  `YYMMDD_STATUS_<slug>.md` (date = triaged, not written), status one of **OK** (ingested
  somewhere) / **SKIP** (reviewed, unused) / **PARKED** (good, not this paper → move to
  `~/.arti/memory/research-idea-bank.md` if a research idea, `~/.arti/wdyt/` if about the ARTi
  framework itself).
- **Tipe = Narasi** — verbatim researcher prose that *is* the content. Never summarize, rewrite,
  or condense it; triage fills only `One-line hook` and `Dipakai di` (e.g. `ebook Bab 1`). Never
  archived, exempt from the cap; its `OK` means "used in a deliverable," and the file stays put.
- **Every triage event** also upserts a row into `~/.arti/wdyt/idea-index.md`.
- **Caps:** untriaged files (no prefix) uncapped, never archived. Triaged files capped at 10
  outside `wdyt/archive/`; past that, move the oldest in, **delete its row** (don't relabel the
  path in place), and fold it into one collapsed line under `## Archived` at the bottom of
  `index.md`, overwritten on each later batch.
- **Findability:** if asked about `wdyt/` content absent from the live table, grep
  `wdyt/archive/*.md` — only index rows are deleted, never files.

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
`wdyt/index.md` rows.

## Session end

Fired by *any* phrasing meaning "we're done" — "update memory", "update status", "end session",
and the like:

1. Update the relevant memory file(s).
2. Overwrite `status.md`'s "Current state" block.
3. Check off / add `todo-list.md` items.
4. If a phase boundary was crossed (idea complete / writing started / submitted / published),
   upsert this project's row in `~/.arti/memory/progress-index.md`.
5. Append the session log to `~/.arti/workflow-sessions/` — **preserve turn order; never reorder
   or flatten by topic.** The sequence in which topics arose is itself the feedback signal for how
   ARTi's own stages should be sequenced. Synthesized findings live in
   `~/.arti/memory/memories/arti-workflow-profile.md`.
6. Promote any correction on *how* to work to `~/.arti/memory/working-preferences.md`.

## Cross-project discovery

"Do I have research about X" / "have I looked into X" / "did I already study X" is never a
local-memory-only question. Check `~/.arti/memory/research-idea-bank.md` and
`~/.arti/memory/progress-index.md` first — plus `~/.arti/wdyt/idea-index.md` if it's about
framework/skill ideas rather than research topics.

<!-- arti: local additions below — preserved on regeneration -->
