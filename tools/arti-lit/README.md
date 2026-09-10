# arti-lit

SQLite-backed store for Layer 2 (`literature\library.md`, canonical bibliography) and Layer 3
(`writing\references.md`, generated per-draft reference list) of ARTi-writing's Reference System.

**Per-project, not shared** — unlike `tools/arti-db` (a cross-project singleton living under
`~/.arti/memory/arti.db`), `arti-lit` manages one SQLite file *inside the paper project it's
running against*: `literature\arti-lit.db`. There is no single "the" arti-lit database; every
invocation needs `--project PATH` (default: current working directory) to know which project's
bibliography it's touching. Layer 1 (`literature\search-log.md`) is untouched by this tool — its
own future home is `tools/scopus-ris-batch-export`, not here.

Every `add`/`update`/`remove` auto-regenerates `literature\library.md`, so the plain-text view
stays current, git-diffable, and human-readable without a separate export step.

## Invocation

Same convention as every other `~/.arti/tools/*` tool — the vendored interpreter's absolute path:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" <subcommand> ... [--project PATH]
```

(Mac/Linux: `~/.arti/python/bin/python3`.)

Every subcommand prints one JSON object to stdout: `{"ok": true, "row"/"rows"/...}` or
`{"ok": false, "error": ...}`, exit 0/1.

## Subcommands

```
init [--project PATH]                   # explicit init/migration trigger; also auto-runs lazily on first use

library add --key KEY --citation TEXT [--doi TEXT] [--local-file TEXT]
            [--status export-only|abstract|fulltext|read] [--used-in TEXT] [--project PATH]
    # rejects (does not insert) if --doi is given and already exists on a different key,
    # surfacing that key so Claude can dedupe instead of creating a near-duplicate row.
library update --key KEY [--citation TEXT] [--doi TEXT] [--local-file TEXT] [--status TEXT] [--used-in TEXT] [--project PATH]
    # for bulk export-only/abstract -> fulltext conversion, see tools/arti-pdf-ingest -- it
    # converts a batch of PDFs to Markdown and calls this same update itself, row by row
library get --key KEY [--project PATH]
library list [--status TEXT] [--project PATH]
library search KEYWORDS... [--project PATH]   # LIKE-match over citation/key/used_in -- cheap dedup check before adding
library remove --key KEY [--project PATH]
library export [--project PATH]         # regenerates literature\library.md

refs generate --keys KEY,KEY,... [--order alpha|appearance] [--output PATH] [--project PATH]
    # keys not found in the library go into `unresolved` in the JSON result -- never silently
    # dropped, never invented. Writes writing\references.md (or --output) as a numbered list of
    # each resolved row's pre-formatted `citation` string. order=alpha sorts by the key's
    # author-year[ab] shape; order=appearance preserves the order --keys was passed in.
```

## Migration

The first time a project's `literature\arti-lit.db` doesn't exist yet, `init_db()` (run
automatically by every subcommand) one-time imports that project's `literature\library.md` table.
A row that fails to parse is skipped with a `warning:` line on stderr rather than aborting the
whole migration. The source `.md` file is kept, not deleted — it becomes a generated export from
that point on, still readable with no tool, but no longer hand-edited.

## Schema

One table, `sources`, deliberately *not* splitting `citation` into authors/journal/volume/etc. —
the current system already stores one pre-formatted citation string per the target journal's
style (Claude composes it when adding), and a citation-style formatting engine
(Harvard/APA/Vancouver/numbered auto-conversion) is out of scope for this tool. `citation` stays a
Claude-composed pre-formatted string, same as before this tool existed.

## Not in this tool

- Layer 1 (`search-log.md`) / `scopus-ris-batch-export` — separate, already-scoped future work.
- Citation-style reformatting engine.
- Any dashboard integration — no read/write path from `dashboard/` to `arti-lit.db`.
