# Deprecated: `_ARTi` location is no longer a per-researcher decision

This file used to hold the resolved path to the researcher's `_ARTi` data folder, which lived
inside their Drive-synced research folder and had to be confirmed with the researcher every time
(see the "hard rule" that used to be in `SKILL.md`).

That's superseded: the cross-project ARTi home is now the fixed path `~/.arti`
(`C:\Users\<user>\.arti\` on Windows, `~/.arti` on Mac/Linux) — same on every machine, never asked
about or confirmed, mirroring how Claude Code keeps `~/.claude`. See `SKILL.md`'s Workflow A.

This file is kept only so anything that still links to it finds an explanation instead of a dead
reference. It carries no live pointer and Workflow A no longer reads it.

**Migrated from:** `G:\My Drive\RESEARCH\_ARTi\` (2026-09-05) — that folder is left in place with
its own `MOVED.md` pointer rather than deleted.
