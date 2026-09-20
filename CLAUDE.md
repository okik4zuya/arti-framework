# ARTi Framework

This is the ARTi Framework's own home — the meta-project, not a paper project. `memory/` in this
project is the single source of truth for everything Claude needs to remember about building and
maintaining ARTi itself. Do not read from or write to the default
`~/.claude/projects/.../memory/` location for this project — everything durable goes in the files
below instead, so it stays inside the repo, versionable, and visible to anyone browsing `~/.arti`
directly.

## What lives here

- `skills/` — the live skills (`ARTi-crosscite`, `ARTi-figure`, `ARTi-idea`, `ARTi-jfinder`,
  `ARTi-ref`, `ARTi-scratchbook`, `ARTi-setup`, `ARTi-writing`), junction-linked into
  `~/.claude/skills/` by the installer. A paper project's root
  `CLAUDE.md` is generated from `skills/ARTi-setup/references/project-claude-template.md` —
  the one canonical copy, rendered by both ARTi-setup and the dashboard scaffolder
- `tools/` — standalone export/render tools (`arti-render`, `arti-plot`, `arti-table`,
  `arti-docx`, `arti-pdf`, `arti-db`, `arti-lit`, `scopus-ris-batch-export`, …)
- `dashboard/` — the local launcher (`dashboard/server/server.py` + `arti-dashboard.html`), a general
  project launcher with ARTi-specific detail for paper projects — see `dashboard/README.md`
- `python/` — vendored interpreter, fetched by `install.ps1`/`install.sh`, not tracked. **Never
  invoke a bare `python`/`python3`/`py` — nothing on this machine puts it on `PATH` (deliberate, to
  avoid clashing with any system Python), so that command has nothing to resolve to on a clean
  client machine.** Always call it by full path: `"~/.arti/python/python.exe" <script>.py ...`
  (Windows) or `~/.arti/python/bin/python3 <script>.py ...` (Mac/Linux); a top-level
  `~/.arti/python.cmd` / `~/.arti/python3` wrapper (created by the installer alongside `python/`)
  also forwards to the same binary if the subpath is forgotten. This applies everywhere, not just
  inside a scaffolded paper project — a paper project's generated `CLAUDE.md` repeats this
  convention for its own tool calls, but this repo has no such generated file, so this line is the
  only place it's stated for work done directly in `~/.arti`
- `bin/` — vendored poppler/tesseract, populated exclusively by `installer/arti-installer.nsi`
  (the NSIS installer's build step); **not** fetched by `install.ps1`/`install.sh` — see
  `tools/_shared/README.md`
- `installer/` — the NSIS installer source (`arti-installer.nsi`, `build_installer.bat`); its
  `payload/` and `dist/` build output are git-ignored, never tracked
- `voice-profiles/`, `journal-library/`, `inbox/` — researcher-content folders, not memory-system
  files in the T0/T1 sense below
- `workflow-sessions/` — retired 2026-09-20 (personalization now goes straight into
  `memory/working-preferences.md`, captured the same turn it's given). The existing logs and
  `memory/memories/arti-workflow-profile.md` stay as a frozen historical record; nothing new is
  appended
- `memory/` — everything else: this project's own tracker plus every cross-project singleton the
  skills read by hardcoded path (researcher profile, idea bank, project index, working
  preferences, figure style). **The whole folder is git-ignored** — nothing in it enters git
  history except the blank scaffold stubs the installer seeds on a fresh install.

## Memory system

- `memory/MEMORY.md` is the index — pointers only, one line each, never content itself. Read it
  first.
- `memory/todo-list.md` is the checklist only — contiguous `- [ ]`/`- [x]` items, one line each, no
  narrative continuation. Link `[[slug]]` for context instead of inlining it. No `## Change log`
  section — git history covers edits to this file. A phase's checked items get deleted once it's
  closed and captured in a topic file; this file tracks outstanding work, not history.
- `memory/status.md` carries the living narrative, but only as a pointer: one overwritten "Current
  state" block at the top, 2-4 sentences naming what changed and a `[[topic-file]]` link for every
  detail — the topic file carries the report, not this block. No Archive section and no
  `## Change log` section here either; the linked topic file's own change log and git history
  already cover it. Read both `todo-list.md` (what's outstanding) and `status.md` (what just
  happened) before advising on scope or priority, and keep both current as items complete, new
  ones surface, or a session changes state.
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
  `## Change log` — except `todo-list.md`/`status.md`, which carry no change log of their own (see
  above).

## `inbox/` — raw-idea inbox for the framework itself

The one folder in this project meant for the researcher to create and edit files in directly;
everything else here is Claude-managed. Pure drop-and-forget capture — no index, no rename, no
archiving. Presence in the folder is the "still open" signal: glob `inbox/*.md` at session start
and surface whatever is there. Reviewing a file ends one of three ways, decided in conversation, no
ceremony: worth keeping — fold it into a `memories/` topic file or `idea-bank add` entry and delete
the raw file; not worth keeping — delete it; still undecided — leave it in place. Verbatim
researcher prose that *is* the content (not a note *about* something) is never summarized or
deleted once used — record where it's been used with one `<!-- used-in: ... -->` comment at the
file's own top. A capture worth cross-project tracking can be added to `inbox/idea-index.md` via
`idea-index upsert` — an available action, not a step every file goes through.

## Session-end wrap-up ritual

Any phrasing meaning "we're done for now" — not only the exact words "update memory" — fires this
checklist:
- Update the relevant `memory/` file(s), including `memory/memories/` topic files touched this
  session
- **Only if the session moved outstanding work or produced a state change worth recording:**
  overwrite `status.md`'s "Current state" pointer and/or check off/add `todo-list.md` items. A
  session that was pure discussion, research, or Q&A with no checklist or state change skips both
  files entirely — there is nothing to overwrite.
- Write any correction on *how* to work straight into `memory/working-preferences.md`, the same
  turn it's given — never deferred to session end

This project has no `project-index.md` row of its own to upsert — that file tracks paper
projects, not the framework itself.

## Session-start standing asks

Surface any open question a memory file recorded, and any file sitting untriaged in `inbox/`, near
the start of the session rather than waiting to be asked.
