<!-- arti-claude-template: v1 -->
# {{PROJECT_NAME}} — Project Instructions

{{Brief description}}

This project's `memory/` is the single source of truth — never read
or write the default `~/.claude/projects/.../memory/` for it.

Read every session: `memory/MEMORY.md`, `memory/todo-list.md`, `memory/status.md`,
`~/.arti/memory/working-preferences.md`. If an `inbox/` folder exists, glob `inbox/*.md` at
session start and surface whatever is sitting there — presence in the folder is the "still open"
signal, no index file to keep in sync.

**Never invoke a bare `python`/`python3`/`py`** — nothing on this machine puts it on `PATH`. Always
call the vendored interpreter by full path: `"~/.arti/python/python.exe" <script>.py ...`
(Windows) or `~/.arti/python/bin/python3 <script>.py ...` (Mac/Linux); a top-level
`~/.arti/python.cmd` / `~/.arti/python3` wrapper also forwards to the same binary if the subpath
is forgotten.

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

## Session end

Fired by *any* phrasing meaning "we're done" — "update memory", "update status", "end session",
and the like:

1. Update the relevant memory file(s).
2. **Only if the session moved outstanding work or produced a state change worth recording:**
   overwrite `status.md`'s "Current state" pointer and/or check off / add `todo-list.md` items. A
   session that was pure discussion, research, or Q&A with no checklist or state change skips both
   files entirely — there is nothing to overwrite.
3. Write any correction on *how* to work straight into `~/.arti/memory/working-preferences.md`, the
   same turn it's given — never deferred to session end.

<!-- arti: local additions below — preserved on regeneration -->
