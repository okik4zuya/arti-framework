# Stage 2 — Search, Deduplication, and Screening: procedure

Full procedure for populating `arti-lit` from the Protocol's database list through both screening
gates. Read this when Stage 2 fires — see `SKILL.md`'s Stage 2 stub for the trigger condition.

## Search — repeated per database

- Loop explicitly over every row in `slr\protocol.md`'s database list — one search pass per
  database, never assume a single source is enough.
- For each database: run the combined search string (adapted to that database's syntax), export
  results (RIS where available), and register with `arti-lit`:
  - Batch RIS export → `library import-ris --files PATH --project PATH` (see `ARTi-ref`'s
    Invocation section for the full command).
  - A record without an RIS export (manual entry) → `library add --key KEY --citation TEXT
    --search-source "DATABASE: SEARCH STRING" --screening-stage identified --project PATH`.
  - Every record, regardless of import path, must end up with `search_source` set to which
    database/string surfaced it — `import-ris` doesn't set this automatically (it's not an RIS
    field), so follow an `import-ris` batch with one `library update --key KEY --search-source
    "..." --screening-stage identified` per imported row.
  - **Do this immediately after each individual `import-ris` call, before running the next one** —
    especially when the Protocol has multiple per-angle queries (see Stage 1's search-string
    guidance). Batching several `import-ris` calls back-to-back before backfilling `search_source`
    loses the ability to attribute which angle surfaced which record: `created_at` timestamps land
    within the same second across rapid-fire imports and can't reliably distinguish import batches
    after the fact. If this has already happened, check first whether the researcher still has the
    per-angle RIS export files (ask them to save/copy each into `literature\exports\` if not) —
    attribution is recoverable by parsing each RIS file's `DO`/`TI` fields and matching against
    `sources.doi`/`citation`, attributing each row to the *earliest* angle (by search order) whose
    file contains a match, since `import-ris`'s DOI-dedup keeps the first-imported occurrence and a
    paper can legitimately match multiple angle queries. Only fall back to a database-level
    `search_source` (e.g. "Scopus", no per-angle detail) if the RIS files themselves are gone —
    this doesn't break PRISMA counts (which only need database-level source) but does lose any
    later "which angle contributed the included papers" breakdown.
- **Fulltext Paper step** (when a candidate needs full-text read for eligibility or extraction):
  use `arti-pdf-ingest` unmodified — see `ARTi-ref`'s Fulltext ingestion section. This registers
  `local_file`/`read_status` itself; it does not touch `screening_stage`.

## Deduplication — before screening starts

- Before screening any newly-searched batch, check `arti-lit` for existing rows: `library search
  KEYWORDS...` (title/author terms) and rely on the DOI-uniqueness rejection already built into
  `library add`/`import-ris` (see `ARTi-ref`'s DOI-dedup rule) — a record whose DOI is already
  tracked is skipped, not re-added, regardless of which database surfaced it this round.
- This is not a new dedup subcommand — it's the same `arti-lit` mechanic `ARTi-ref` already
  documents, just applied here before every screening pass rather than only at import time.

## Screening — two gates, both must log rejects with a reason

### Gate 1: Title/Abstract Screening

- For each `identified` row: read title + abstract (from `sources.abstract` if populated by
  import, else fetch/read manually), apply the Protocol's inclusion/exclusion criteria.
- **Passes:** `library update --key KEY --screening-stage title_abstract --project PATH`
- **Rejected:** `library update --key KEY --screening-stage excluded_title_abstract
  --exclusion-reason "REASON" --project PATH` — the reason must cite one of the Protocol's listed
  exclusion criteria (or a close paraphrase); a reason that doesn't map to a listed criterion is a
  signal the Protocol's criteria list is incomplete, not that the reject is wrong.
- **Every row gets a stage set, pass or reject — never left at `identified`.** This is what makes
  the PRISMA Flow Diagram's counts real (Stage 4 reads them straight from these stage values)
  rather than reconstructed from memory after the fact.

### Gate 2: Eligibility Screening (full-text)

- For each `title_abstract` row: obtain full text (Fulltext Paper step above if not already done),
  apply the Protocol's criteria at full-text depth (this catches exclusions title/abstract
  couldn't — e.g. wrong outcome measure, duplicate dataset, retracted).
- **Passes:** `library update --key KEY --screening-stage eligible --project PATH`
- **Rejected:** `library update --key KEY --screening-stage excluded_eligibility --exclusion-reason
  "REASON" --project PATH` — same rule: reason must cite a Protocol criterion.
- Once a row is `eligible`, it proceeds to Stage 3 extraction, after which its stage becomes
  `included`. `eligible` is a transient stage, not a stopping point — Stage 3 always follows
  immediately for every `eligible` row, no separate confirmation step.

## Reporting after each database/batch

After each database search or screening pass, report: how many identified, how many deduplicated
away, how many passed/rejected at this gate, and running totals — the researcher should never have
to ask "where are we" mid-Stage-2.
