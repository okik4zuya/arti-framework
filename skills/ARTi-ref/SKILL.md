---
name: ARTi-ref
description: >
  Literature CRUD, fulltext ingestion, and paper-content retrieval against `arti-lit.db` — a
  project's canonical bibliography, one row per source, keyed `author-year[a|b]`. Use this skill
  for: adding/updating/removing a reference, checking for a DOI duplicate before adding one,
  regenerating `writing\references.md` from a Scratchbook's citation tags, batch-converting PDFs to
  fulltext Markdown, and answering "what does this paper say" / "summarize paper X" / "extract this
  paper" style requests about one specific reference. This skill owns the mechanics of *retrieving
  and storing* literature; it does not decide what a paper's content is used *for* — that stays
  with the calling skill. Do NOT use this skill for: Scratchbook population mechanics, paraphrase/
  plagiarism/hallucination rules, or `[LIT: key]` tagging inside manuscript prose (ARTi-writing);
  Gap Map construction or novelty scoring (ARTi-idea); ranking candidate journals or Scimago lookups
  (ARTi-jfinder).
---

# ARTi-ref Skill

Thin, mechanics-only wrapper around the `arti-lit` CLI/database (and the `arti-pdf-ingest` batch
tool) for a project's literature. Modeled on `ARTi-jfinder`'s shape: one clear job, an explicit
"Not this skill" section, and no document of its own beyond the generated exports the CLI already
produces (`literature\library.md`, `writing\references.md`).

## What this is

`arti-lit.db` is the **canonical**, per-project bibliography (unlike `arti-jfinder`'s cross-project
Scimago singleton, this one takes `--project PATH` on every call). One reference = one row, keyed
`author-year[a|b]` (e.g. `kaw-2016`, `pintrich-1991a`, `pintrich-1991b` for two same-author-year
papers). This skill owns three things that used to be independently documented in both
`ARTi-writing` and `ARTi-idea` — the exact duplication that let one copy go stale while the other
was updated:

1. **`arti-lit` invocation and CRUD** — `library add/get/update/remove/search`, `refs generate`.
2. **Fulltext ingestion** — `arti-pdf-ingest`'s batch PDF→Markdown conversion and the
   `local_file`/`read_status` semantics.
3. **The retrieval-trigger rule and Paper Extraction** — naming a reference is a retrieval trigger,
   not a recall trigger; extracting a paper's structured content is a mechanical action any caller
   can invoke.

What a paper's content gets used *for* — folded into a Gap Map (`ARTi-idea`) vs. a Scratchbook
section (`ARTi-writing`) — is the caller's job, not this skill's. This skill answers the retrieval
question and hands back the row; the caller decides what to do with it.

## Invocation

Every `library`/`refs` command runs as: `"~/.arti/python/python.exe"
"~/.arti/tools/arti-lit/cli.py" <subcommand> ... --project PATH` (Mac/Linux:
`~/.arti/python/bin/python3`). Per-project, not a cross-project singleton — `--project` is
required on every call, unlike `arti-jfinder`/`arti-db`. Each call prints one JSON object
(`{"ok": true, ...}` or `{"ok": false, "error": ...}`); see `~/.arti/tools/arti-lit/README.md` for
the full subcommand surface.

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library add --key KEY --citation TEXT [--doi TEXT] [--local-file TEXT] [--status export-only|abstract|fulltext|read] [--used-in TEXT] [--summary TEXT] [--abstract TEXT] --project PATH
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library update --key KEY [--citation TEXT] [--doi TEXT] [--local-file TEXT] [--status TEXT] [--used-in TEXT] [--summary TEXT] [--abstract TEXT] --project PATH
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library get --key KEY --project PATH
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library search KEYWORDS... --project PATH
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library remove --key KEY --project PATH
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library import-ris --files PATH[,PATH...] --project PATH
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library list [--status TEXT] [--journal TEXT] [--article-type TEXT] --project PATH
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" refs generate --keys KEY,KEY,... --order appearance|alpha --project PATH
```

**Key format:** `author-year[a|b]` (e.g. `kaw-2016`), always lowercase — the CLI normalizes any key
you pass at every write path, but don't rely on that; type it lowercase to begin with. Two papers
sharing an author-year get `a`/`b` suffixes.

**DOI-dedup rule:** `library add`/`update` reject a duplicate DOI already present on a different
key, instead of inserting a near-duplicate row. Run `library search KEYWORDS...` first when in
doubt about whether a source is already tracked.

**`journal_name`/`article_type` are import-only fields:** they're populated automatically by
`library import-ris` (from the RIS record's `T2`/`JO`/`JF` and `TY` tags) but have no equivalent
flag on `library add`/`update` — a row added by hand will have both NULL unless the caller extends
those commands. `library list --journal`/`--article-type` filter on them (substring match); don't
expect either filter to match manually-added rows.

**`library.md` is a generated export — never hand-edit it.** It regenerates automatically on every
`add`/`update`/`remove`, but stays plain, always-current Markdown, so a browsing read ("what have I
collected so far", "what's still export-only") can just read the file directly — no CLI call
needed for that. The CLI is required for anything that *changes* the data.

**Saving a source's literature summary:** `library update --key KEY --summary TEXT` (or `library
add ... --summary TEXT` first if the key isn't tracked yet). `sources.summary` is one free-text
field per key, read back via `library get`; because `key` is `UNIQUE`, saving a summary for an
already-tracked source overwrites in place, never creates a duplicate row.

## Bulk import

`library import-ris --files PATH[,PATH...] --project PATH` is the supported path for a
researcher-provided `.ris` export (Scopus, ScienceDirect, or any other database that exports RIS).
It dedups on DOI within the batch and against the existing library, same rule as manual `add`, and
best-effort populates `journal_name`/`issn`/`article_type`/`abstract` from the RIS record — see the
import-only fields note above and `~/.arti/tools/arti-lit/README.md` for exactly which RIS tags map
to which columns.

**After any `import-ris` call — whether Claude runs it or the researcher reports having run it
directly — treat it as a retrieval-trigger for logging, not just for reading.** Ask for (or locate)
the source `.ris` file, move/copy it into `literature/exports/` unrenamed, and hand the
query/date/hit-count/target-claim back to the caller so it can fill a `literature/search-log.md`
Layer-1 row. That file stays the calling skill's (`ARTi-writing`'s Reference System) to write —
this skill's job is just to flag that the row is owed, not to write it.

To answer "what's new since an import," use `library list` (ordered by `key`) and compare against
what was already known — there's no `created_at` filter today, so don't hand-roll SQL against
`arti-lit.db` directly. If a real time-window is needed and `list`'s `--status`/`--journal`/
`--article-type` filters can't express it, ask the researcher to confirm scope instead (e.g. "all
JECE rows").

## The retrieval-trigger rule

**Naming a reference is a retrieval trigger, not a recall trigger.** The moment anyone — the
researcher, or a calling skill's own workflow — names a reference by its `author-year[a|b]` key or
an informal equivalent ("jelaskan tentang paper xie-2026", "what does xie-2026 say", "summarize
smith-2020"), call `library get --key KEY` (`sources.citation`/`abstract`/`summary`/`local_file`)
and, if `local_file` is set, read that fulltext before answering — **never answer from
pretrained/general knowledge of the paper, even when the title or authors seem familiar.** If
`library get` returns no row, run `library search KEYWORDS...` for a close match and confirm which
paper is meant rather than guessing; only report "not in the library" once that search comes back
empty too.

This rule applies regardless of which skill is active — `ARTi-writing` mid-drafting, `ARTi-idea`
mid-Gap-Map, or a standalone question with no other skill running.

## Fulltext ingestion

When a batch of PDFs already has `library.md` rows (`local file: —`, status `export-only` or
`abstract`) and needs bulk conversion to fulltext Markdown, use `arti-pdf-ingest` instead of
ingesting one-by-one:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-pdf-ingest/cli.py" ingest --project PATH --manifest PATH
```

It requires the `key` to already exist in `library.md` — screening/`library add` still happens
first, this tool never creates new library rows — and it registers the result itself via `arti-lit
library update --status fulltext`, so no separate registration step follows. See
`~/.arti/tools/arti-pdf-ingest/README.md` for the manifest format.

`read_status` vocabulary: `export-only` / `abstract` / `fulltext` / `read`. Being a superset that
includes screened-out sources is what stops a query from being re-run.

## Regenerating `writing\references.md`

`references.md` is generated, filtered to citations actually present in the current draft. Grep
the caller's own draft/Scratchbook for its citation-tag convention (cheap, targeted — not a full
regex pass) to get the key list in appearance order, then:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" refs generate --keys KEY,KEY,... --order appearance|alpha --project PATH
```

`--order appearance` preserves the order the tags were found in; `--order alpha` sorts by the
key's `author-year[ab]` shape. Any key in the result's `unresolved` list is reported back to the
caller as unresolved, never silently dropped or invented.

## Paper Extraction (on-demand)

**Trigger:** "summarize paper [title]", "extract this paper", "give me the NotebookLM extraction
for [paper]", or any request to pull structured notes from one specific paper. Works standalone,
independent of any other skill's stage gating.

**Behavior:**
- If the paper's text or PDF is available in the conversation (attached, pasted, or already
  ingested via `arti-pdf-ingest`), perform the extraction directly, following
  `references/paper-extraction-template.md`'s field structure exactly — terse bullets, no prose
  padding, anything inferred rather than read off the page tagged `[SUGGESTED — USER MUST
  VERIFY]`.
- If the researcher instead wants to run the extraction in NotebookLM (e.g. the paper only exists
  there), hand them `references/notebooklm-extraction-prompt.md` verbatim to paste in — same
  fields, wrapped as a standalone instruction block.
- Register the paper in `arti-lit` if not already present (`library add --key author-year[a|b]
  --citation ... --doi ...`), then save the **full extraction text** as that row's `--summary`
  (`library update --key KEY --summary "..."`) — this is what makes the extraction retrievable
  later via `library get` without re-reading the PDF.
- `Novelty Signals` in the extraction are raw, unscored input — scoring them is the caller's job
  (e.g. `ARTi-idea`'s Idea Canvas), never done here.
- Hand the extraction's pieces back to the caller rather than deciding where they go: the
  `REFERENCE ENTRY` block and any `⚠️ CONTRADICTION` lines are Gap-Map-shaped; `Citable Claims` are
  Scratchbook-shaped. Fold them in only if the caller's own document already exists and the caller
  asks for it — this skill does not maintain a Gap Map or Scratchbook itself.

**File written to:** none of its own — the extraction lives in the `arti-lit` summary field; the
caller decides which of its own documents (if any) get the folded-in pieces.

## Not this skill

- **Scratchbook population mechanics, paraphrase/plagiarism/hallucination rules, and `[LIT: key]`
  tagging inside manuscript prose** — that's `ARTi-writing`'s job (manuscript-writing epistemics,
  not literature CRUD). `ARTi-writing` calls into this skill for the mechanics (`library get/add`,
  fulltext), then folds the result into its own Scratchbook under its own tagging rules.
- **Gap Map construction and novelty scoring** — that's `ARTi-idea`'s job. `ARTi-idea` calls into
  this skill for Paper Extraction and `library get/search`, then folds the result into its own Gap
  Map / Idea Canvas.
- **Journal lookup and ranking (Scimago data)** — that's `ARTi-jfinder`'s job; unrelated database,
  unrelated CLI.
- **Legacy hand-maintained citation records** (e.g. a pre-`arti-lit` project's own
  `citation-map.md`) — once a project has adopted `arti-lit`, that legacy file is a frozen,
  historical record, not a live store this skill reads from or writes to. See
  `ARTi-setup/references/project-scaffold-template.md`'s legacy-record convention.

## Reference Files

- `references/paper-extraction-template.md` — blank single-paper extraction shape, filled directly
  when the paper's text is available in-conversation
- `references/notebooklm-extraction-prompt.md` — same field set, wrapped as a copy-paste prompt for
  NotebookLM

## Change log
- 2026-09-15 — documented `library import-ris`/`library list --journal/--article-type` in the
  Invocation block, added the Bulk import subsection (search-log Layer-1 logging obligation after
  an import-ris call), and noted `journal_name`/`article_type` are import-only fields with no
  `add`/`update` equivalent. Prompted by a real session where these gaps forced ad-hoc `sqlite3`
  queries and a regex-based review-article guess against a 96-row RIS batch.
- 2026-09-14 — created, extracting the `arti-lit` invocation convention, fulltext-ingestion
  mechanics, retrieval-trigger rule, and Paper Extraction out of `ARTi-writing` and `ARTi-idea`
  (which had independently duplicated this material — the duplication that let one copy go stale
  while the other was updated, the root cause of a bug where a `xie-2026` lookup fell through to a
  dead grep path). Both callers now point here instead of documenting the mechanics themselves.
