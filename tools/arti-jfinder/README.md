# arti-jfinder

SQLite-backed store for Scimago Journal Rank data, backing ARTi-idea's Stage 5 ("Journal Target
Sheet") with real ranking/scope data instead of Claude's general knowledge alone.

**Cross-project singleton** — like `tools/arti-db` (unlike per-project `tools/arti-lit`), there is
exactly one database, `arti-jfinder.db`, shared across every ARTi paper project. No `--project`
flag on any subcommand.

**Manually-supplied import, not a live scraper** — Scimago's export
(`journalrank.php?out=xls`, downloaded by hand from their website; there is no public API) is a
single current-year snapshot covering all ~32k journals, all categories/quartiles embedded in one
`Categories` column. `ingest` loads whatever file path the researcher points it at. Re-download and
re-`ingest` (e.g. once a year) to refresh; there is no automated fetch loop, no historical-year
backfill.

## Invocation

Same convention as every other `~/.arti/tools/*` tool — the vendored interpreter's absolute path:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-jfinder/cli.py" <subcommand> ...
```

(Mac/Linux: `~/.arti/python/bin/python3`.)

Every subcommand prints one JSON object to stdout: `{"ok": true, "row"/"rows"/...}` or
`{"ok": false, "error": ...}`, exit 0/1.

## Subcommands

```
init                                     # explicit init trigger; also auto-runs lazily on first use

ingest --file PATH --year YYYY
    # parses a Scimago export snapshot; upserts `journals` (identity fields always overwritten to
    # the latest ingest), replaces that year's `journal_metrics`/`journal_categories` rows wholesale
    # (re-running the same --year is idempotent, not additive)

journal search [--category TEXT] [--quartile Q1|Q2|Q3|Q4] [--min-sjr N] [--keyword TEXT]
               [--year YYYY] [--limit N (default 20)]
    # ranked by SJR descending; --category must match a string from `journal categories` exactly
    # (case-insensitive) -- it is one half of a "Category Name (Qn)" pair, not a free-text search;
    # use --keyword for free-text title matching; --year defaults to the latest ingested year

journal get --id SOURCEID
    # identity + latest-year metrics + latest-year categories, or {"ok": false} if unknown

journal categories [--year YYYY]
    # distinct category strings for that year (default: latest) -- look here first to get the
    # exact text `journal search --category` needs

scope get --id SOURCEID
    # cached aims-and-scope text, or {"ok": true, "row": null} if never fetched
scope set --id SOURCEID --text TEXT [--source-url URL]
    # Claude writes back here after a WebFetch against the journal's own site during shortlist
    # consultation -- lazy cache, never bulk pre-scraped
```

## Schema

- `journals` — identity: `sourceid` (Scimago id, PK), `title`, `issn`, `eissn`, `type`,
  `publisher`, `country`, `coverage`. The source `Issn` column packs print+electronic ISSN
  comma-separated in one unlabeled field — stored positionally (`issn` = first, `eissn` = second),
  not verified against which is actually print vs. electronic.
- `journal_metrics` — one row per journal per ingested year: `sjr`, `sjr_best_quartile`,
  `h_index`, `total_docs`, `total_docs_3y`, `total_refs`, `total_cites_3y`, `citable_docs_3y`,
  `cites_per_doc_2y`, `ref_per_doc`, `female_pct`, `overton`, `sdg`. `sdg` has no source column in
  the 2025 export and stays `NULL` — kept in the schema so a future snapshot that does carry it
  needs no migration.
- `journal_categories` — one row per category+quartile pair exploded from the source `Categories`
  column (e.g. `"Materials Science (miscellaneous) (Q1); Chemistry (Q2)"` → two rows).
- `journal_scope` — lazy cache: `aims_scope_text`, `source_url`, `fetched_at`. Populated only via
  `scope set`, one row per journal (a second `set` overwrites, not appends).

Metrics are SJR-based only — true Journal Impact Factor (Clarivate/JCR) is a separate paid source,
out of scope for this tool.

## Parsing notes

Despite Scimago's UI suggesting Latin-1/cp1252, the actual downloaded export decodes cleanly as
UTF-8 (accented publisher/country names survive round-trip) — `ingest` reads with
`encoding="utf-8-sig"`. `;`-delimited, decimal-comma numerics (`"104,065"` → `104.065`, converted
before `float()`). Parsed with stdlib `csv` only — no pandas dependency.

## Not in this tool

- Automated/historical scraping — Scimago has no public API; every refresh is a manual download +
  `ingest` of the current-year snapshot.
- True JIF/Clarivate metrics.
- Bulk aims-and-scope pre-scraping — `journal_scope` is populated lazily, one `scope set` call per
  shortlist candidate during actual consultation.
