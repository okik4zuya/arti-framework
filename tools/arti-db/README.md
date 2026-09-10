# arti-db

SQLite-backed store for ARTi's three cross-project aggregators: `memory/project-index.md`,
`memory/research-idea-bank.md`, and `inbox/idea-index.md`. Replaces the old pattern where every
skill instruction told Claude to hand-open and hand-edit these markdown files directly (no lock,
no schema, easy to silently skip). Data lives in `~/.arti/memory/arti.db`. The dashboard
(`dashboard/server/db.py`) is a second reader/writer of this same file's `project_index` table —
it owns the launcher-only columns (category/tags/lifecycle/added_at/last_opened_at) added to that
table for its own project cards, alongside the paper-pipeline columns (stage/target_journal/
status/summary) the skills own.

Every `upsert`/`add`/`archive`/`log` auto-regenerates the matching `.md` file, so the plain-text
views stay current, git-diffable, and human-readable without a separate export step.

## Invocation

Same convention as every other `~/.arti/tools/*` tool — the vendored interpreter's absolute path:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-db/cli.py" <subcommand> ...
```

(Mac/Linux: `~/.arti/python/bin/python3`.)

Every subcommand prints one JSON object to stdout: `{"ok": true, "row"/"rows": ...}` or
`{"ok": false, "error": ...}`, exit 0/1.

## Subcommands

```
init                            # explicit init/migration trigger; also auto-runs lazily on first use

project upsert --project-path PATH --topic TEXT [--stage TEXT] [--target-journal TEXT] [--status TEXT] [--summary TEXT] [--updated YYYY-MM-DD]
    # --summary: free text listing the project's actual memory sub-topics (keywords), not just its
    # headline research question -- this is what makes cross-project topic lookup via `project list`
    # viable without a filesystem walk.
project list [--stage TEXT] [--status TEXT]
project get --project-path PATH
project export                # regenerates memory/project-index.md

idea-bank add --label TEXT --idea-text TEXT [--c N] [--m N] [--e N] [--novelty-label TEXT]
              [--date-parked YYYY-MM-DD] [--source-project TEXT] [--reason TEXT] [--notes TEXT]
idea-bank search KEYWORDS...   # LIKE-match over idea_text/label/source_project/notes
idea-bank list [--source-project TEXT]
idea-bank remove --id N
idea-bank export               # regenerates memory/research-idea-bank.md

idea-index upsert --project TEXT --file TEXT [--tipe Ide|Narasi] [--status TEXT] [--hook TEXT] [--used-in TEXT] [--date-added YYYY-MM-DD]
idea-index list [--project TEXT] [--status TEXT] [--include-archived]
idea-index archive --ids N,N,N --summary TEXT
idea-index log --note TEXT
idea-index export              # regenerates inbox/idea-index.md (table + Change log section)
```

Dates default to today, computed by the tool itself, if omitted.

## Migration

The first time `arti.db` doesn't exist yet, `init_db()` (run automatically by every subcommand)
one-time imports the three legacy markdown files: `project-index.md`'s table,
`research-idea-bank.md`'s `## Entry N:` blocks, and `idea-index.md`'s table + `## Change log`
bullets. A row that fails to parse is skipped with a `warning:` line on stderr rather than
aborting the whole migration. The source `.md` files are kept, not deleted — they become generated
exports from that point on, still readable with no tool, but no longer hand-edited.

## Dashboard integration

The dashboard reads and writes `project_index` directly (`dashboard/server/db.py`), aliasing
`topic ↔ name` and `project_path ↔ path` for the keys its UI expects. The columns it owns
(`category`, `tags`, `lifecycle`, `added_at`, `last_opened_at`) were backfilled from the
dashboard's now-retired `launcher.db` in a one-time migration inside `init_db()`.
