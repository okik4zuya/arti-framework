# arti-lit

SQLite-backed store for Layer 2 (`literature\library.md`, canonical bibliography) and Layer 3
(`writing\references.md`, generated per-draft reference list) of the `ARTi-ref` skill's literature
system (CRUD, fulltext ingestion, retrieval-trigger rule, Paper Extraction). `ARTi-writing` and
`ARTi-idea` both call into `ARTi-ref` for these mechanics rather than documenting them separately.

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
            [--status export-only|abstract|fulltext|read] [--used-in TEXT] [--summary TEXT]
            [--abstract TEXT] [--project PATH]
    # rejects (does not insert) if --doi is given and already exists on a different key,
    # surfacing that key so Claude can dedupe instead of creating a near-duplicate row.
library update --key KEY [--citation TEXT] [--doi TEXT] [--local-file TEXT] [--status TEXT] [--used-in TEXT] [--summary TEXT] [--abstract TEXT] [--project PATH]
    # for bulk export-only/abstract -> fulltext conversion, see tools/arti-pdf-ingest -- it
    # converts a batch of PDFs to Markdown and calls this same update itself, row by row
library get --key KEY [--project PATH]
library list [--status TEXT] [--journal TEXT] [--article-type TEXT] [--project PATH]
    # --journal and --article-type are substring (LIKE) filters on journal_name/article_type --
    # only rows added via import-ris have those columns populated (see Schema)
library search KEYWORDS... [--project PATH]   # LIKE-match over citation/key/used_in -- cheap dedup check before adding
library remove --key KEY [--project PATH]
library export [--project PATH]         # regenerates literature\library.md
library import-ris --files PATH[,PATH...] [--project PATH]
    # batch-imports RIS exports (Scopus, ScienceDirect, or any other database that exports RIS)
    # in one call, so DOI-dedup works across files in the same batch. Synthesizes `citation` from
    # AU/TI/PY/T2 (falling back to T1 for title, Y1 for year, JO/JF for source). Also populates
    # `journal_name` (from T2/JO/JF), `issn` (from SN), `abstract` (from AB/N2), and `article_type`
    # (from the record's own RIS TY tag, e.g. "JOUR", "CONF") when present -- article_type is
    # best-effort: many exports (including some Scopus RIS) tag every record JOUR regardless of
    # review vs. original research, so a title-based screening pass is still needed as a fallback,
    # not replaced by this column.
    # DOI-only dedup: rows without a DOI always insert; a DOI already in the
    # DB or seen earlier in the same batch goes to `skipped_duplicate` instead of raising. A record
    # missing both title and authors goes to `skipped_invalid` with file/record_index; never aborts
    # the whole batch. Prints {"ok": true, "imported": N, "skipped_duplicate": [...],
    # "skipped_invalid": [...]}. This is also the path the dashboard's References window uses
    # in-process (see dashboard/server/lit.py), not by shelling out to this CLI.

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

`sources` deliberately does *not* split `citation` into authors/journal/volume/etc. — the current
system already stores one pre-formatted citation string per the target journal's style (Claude
composes it when adding), and a citation-style formatting engine (Harvard/APA/Vancouver/numbered
auto-conversion) is out of scope for this tool. `citation` stays a Claude-composed pre-formatted
string, same as before this tool existed.

`sources.summary` is a single free-text field, set via `library add`/`library update`, read back
via `library get` (already returns the full row). It is not included in the generated
`library.md` — a summary can be arbitrarily long prose and would break that table's row-per-line
shape. Because `key` is `UNIQUE` and `update` always targets one existing row by key, saving a
summary for an already-tracked source is structurally an overwrite, never a duplicate row.

`sources.abstract` is the same shape as `summary` — free-text, not included in `library.md`, read
back via `library get`/`library list`. Set via `library add`/`library update --abstract`, or
captured automatically from an RIS export's `AB` (falling back to `N2`) tag on `library
import-ris`. It is the source's own abstract (what the database wrote), distinct from `summary`
(Claude's own notes on the source).

`sources.journal_name`, `sources.issn`, and `sources.article_type` are populated automatically by
`library import-ris` (from RIS `T2`/`JO`/`JF`, `SN`, and `TY` respectively) and are otherwise NULL
-- `library add`/`library update` have no flags for them today, so a manually-added row leaves
these unset unless the caller extends those commands. `library list --journal`/`--article-type`
filter on them (substring match); manually-added rows simply won't match either filter.

## Not in this tool

- Layer 1 (`search-log.md`) / `scopus-ris-batch-export` — separate, already-scoped future work.
- Citation-style reformatting engine.
- Fuzzy title/year dedup — `library import-ris` dedupes on DOI only; rows without a DOI always
  import as new rows.
