# ARTi Framework

This is the ARTi Framework's own home — the meta-project, not a paper project. `memory/` in this
project is the single source of truth for everything Claude needs to remember about building and
maintaining ARTi itself. Do not read from or write to the default
`~/.claude/projects/.../memory/` location for this project — everything durable goes in the files
below instead, so it stays inside the repo, versionable, and visible to anyone browsing `~/.arti`
directly.

## What lives here

- `skills/` — the four live skills (`ARTi-idea`, `ARTi-writing`, `ARTi-setup`, `ARTi-figure`),
  junction-linked into `~/.claude/skills/` by the installer. A paper project's root
  `CLAUDE.md` is generated from `skills/ARTi-setup/references/project-claude-template.md` —
  the one canonical copy, rendered by both ARTi-setup and the dashboard scaffolder
- `tools/` — standalone export/render tools (`arti-render`, `arti-plot`, `arti-table`,
  `arti-docx`, `arti-pdf`, `arti-db`, `arti-lit`, `scopus-ris-batch-export`, …)
- `dashboard/` — the local launcher (`dashboard/server/server.py` + `arti-dashboard.html`), a general
  project launcher with ARTi-specific detail for paper projects — see `dashboard/README.md`
- `python/` — vendored interpreter, fetched by `install.ps1`/`install.sh`, not tracked
- `bin/` — vendored poppler/tesseract, populated exclusively by `installer/arti-installer.nsi`
  (the NSIS installer's build step); **not** fetched by `install.ps1`/`install.sh` — see
  `tools/_shared/README.md`
- `installer/` — the NSIS installer source (`arti-installer.nsi`, `build_installer.bat`); its
  `payload/` and `dist/` build output are git-ignored, never tracked
- `voice-profiles/`, `workflow-sessions/`, `journal-library/`, `inbox/` — researcher-content
  folders, not memory-system files in the T0/T1 sense below
- `memory/` — everything else: this project's own tracker plus every cross-project singleton the
  skills read by hardcoded path (researcher profile, idea bank, project index, working
  preferences, figure style). **The whole folder is git-ignored** — nothing in it enters git
  history except the blank scaffold stubs the installer seeds on a fresh install.

## Memory system

- `memory/MEMORY.md` is the index — pointers only, one line each, never content itself. Read it
  first.
- `memory/todo-list.md` is the checklist only — contiguous `- [ ]`/`- [x]` items, no narrative.
- `memory/status.md` carries the living narrative: one overwritten "Current state" block at the
  top + an archive section below for superseded write-ups. Read both `todo-list.md` (what's
  outstanding) and `status.md` (what just happened) before advising on scope or priority, and keep
  both current as items complete, new ones surface, or a session changes state.
- Everything else — one file per topic — lives in `memory/memories/` (T1, read on demand, no
  budget). The three files above plus this `CLAUDE.md` are T0 (auto-loaded every session, ~20 KB
  budget total); a T0 file that exceeds it gets compacted at the next wrap-up, not left to grow.
- Update the existing file on a topic rather than creating a near-duplicate. Link related files
  with `[[slug]]` references instead of restating their content.
- Read the relevant memory file before advising on that topic; details live there, not here.
- A pointer to `memory/working-preferences.md` — read it at the start of every ARTi session; it is
  short, imperative, and states what Claude must do, not what was observed.
- **Timestamps:** get the real current time before writing any timestamp — never guess it. Set
  `created` in frontmatter on creation and `updated` on every write, and add a line to that file's
  `## Change log`.

## `inbox/` — raw-idea inbox for the framework itself

The one folder in this project meant for the researcher to create and edit files in directly;
everything else here is Claude-managed. `inbox/index.md` is the file Claude reads first each
session. Untriaged files (no status prefix) are uncapped and never archived — surface any of them
near session start rather than waiting to be asked. Triaging renames a file to
`YYMMDD_STATUS_<slug>.md` — **OK** (ingested somewhere), **SKIP** (reviewed, not used), or
**PARKED** (good idea, not actionable yet) — and updates its `index.md` row to match. Triaged
files are capped at 10 outside `inbox/archive/`; nothing archived is deleted, only the index row
is — grep `inbox/archive/*.md` directly if asked about something not in the live table. Every
triage event also upserts a row into `~/.arti/inbox/idea-index.md`, the cross-project idea-list
aggregator, so a project's own `inbox/` triage and this framework's own `inbox/` triage both land in
the same place.

## Session-end wrap-up ritual

Any phrasing meaning "we're done for now" — not only the exact words "update memory" — fires this
checklist:
- Update the relevant `memory/` file(s), including `memory/memories/` topic files touched this
  session
- Overwrite `status.md`'s "Current state" block (don't stack it alongside the previous one — the
  change log carries the fact that an old one existed)
- Check off/add `todo-list.md` items the session resolved or surfaced
- Append to `~/.arti/workflow-sessions/`
- Check whether anything said this session should be promoted to
  `memory/working-preferences.md` (a correction on *how* to do something, not a one-off fact)

This project has no `project-index.md` row of its own to upsert — that file tracks paper
projects, not the framework itself.

## Session-start standing asks

Surface any open question a memory file recorded, and any untriaged `inbox/index.md` rows, near
the start of the session rather than waiting to be asked.
