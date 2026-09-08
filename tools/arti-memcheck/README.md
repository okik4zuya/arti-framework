# arti-memcheck

Composition checker for an ARTi project's **T0** memory set — the four files
auto-loaded into context every session:

```
CLAUDE.md   memory/MEMORY.md   memory/todo-list.md   memory/status.md
```

## What it checks

**Composition is the defect; size is only a smell.**

| Check | Level | Catches |
|---|---|---|
| A — size | WARN only | T0 total over budget, any file over 8 KB |
| B — structure | ERROR/WARN | stacked `## Current state` blocks, `**Session N` pseudo-blocks in the live region, prose in the checklist-only `todo-list.md`, change logs that have eaten their own file, over-long `MEMORY.md` index lines |
| C — references | ERROR | `~/.arti/…` paths, multi-segment relative paths and `[[slug]]` links that don't resolve — reported as **MOVED → \<found path\>** when exactly one basename match exists, else **MISSING** |
| D — template | ERROR/INFO | `CLAUDE.md` drift above the ownership fence, missing canonical headings; local additions below the fence reported as INFO only |

Size never fails a run on its own. A large T0 made entirely of live state is a
pass — the checker must not create pressure to delete load-bearing content.

The **MOVED vs. MISSING** distinction in check C is the highest-value output: it
turns a nag into a patch list.

## Usage

```
"$HOME/.arti/python/python.exe" "$HOME/.arti/tools/arti-memcheck/check.py" \
    [--project DIR]   # default: cwd
    [--all]           # every path in progress-index.md, plus ~/.arti itself
    [--budget N]      # bytes, default 20480
    [--hook]          # summary mode: silent when clean, always exit 0
```

Exit `0` clean · `1` findings · `2` usage/IO error.

A directory that is not an ARTi project (no `memory/MEMORY.md`) exits silently
under `--hook`, and with a one-line error otherwise.

## Hook

Wired as a `SessionStart` hook (`startup|resume`) in
`C:\Users\user\.claude\settings.json`. Three load-bearing conditions:

1. **Silent when clean** — a hook that says "all good" every session becomes
   wallpaper, and the failure case gets skimmed along with it.
2. **Imperative, not statistical** — it prints what to do, not a percentage.
3. **`--hook` always exits 0** — a non-zero `SessionStart` hook blocks session
   start.

`Stop` and `PreCompact` were considered and rejected: `Stop` fires at every
*turn* end, not session end; `PreCompact` fires unpredictably and often never.

## Notes

Pure stdlib, same pattern as `arti-table` / `arti-render`. Every file read is
wrapped in `try/except OSError` — Google Drive holds real file locks on these
projects, and a traceback in a `SessionStart` hook is unacceptable.

Deliberately **not** built: `--fix`/auto-compaction (a script cannot satisfy the
lossless-compaction rule — report only), `--json` (nothing consumes it),
sentence-counting in `MEMORY.md` (`e.g.`, `et al.`, `§2.6.1` make it a
false-positive machine — length cap only), narrative keyword heuristics, and
frontmatter-presence checks.
