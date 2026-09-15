---
name: ARTi-jfinder
description: >
  Ad-hoc journal lookup and ranking questions against the Scimago Journal Rank snapshot backing
  `arti-jfinder` — journal search by category/quartile/keyword, single-journal identity and
  metrics, aims-and-scope lookup. Use for one-off journal lookups and ranking questions asked
  outside the target-journal decision workflow: "find journals about X", "what's the SJR/quartile
  of journal Y", "list Q1 journals in materials science", "look up aims and scope for journal Z",
  "is journal X Scopus-indexed". Do NOT use for selecting/committing a paper's target journal —
  that decision process (candidate ranking, predatory-journal screen, novelty threshold, Journal
  Target Sheet) belongs to ARTi-idea Stage 5; defer to that skill if the researcher is choosing a
  journal for a specific paper.
---

# ARTi-jfinder Skill

Thin, stateless lookup wrapper around the `arti-jfinder` CLI/database for mid-conversation journal
questions. No documents, no state, no `references/` — answer the question and stop.

## What this is

A SQLite-backed store of Scimago Journal Rank data (`~/.arti/tools/arti-jfinder/`), exposing
`journal search/get/categories` and `scope get/set`. **Manually-supplied import, not a live
scraper** — Scimago's export is a single current-year snapshot downloaded by hand (no public API);
metrics are SJR-based only, not true JIF/Clarivate. **Cross-project singleton** — one database
shared across every ARTi paper project, like `arti-db`; no `--project` flag on any subcommand.

This skill is the ad-hoc lookup surface. It does not decide, rank against a specific paper, or
write any project document — that's ARTi-idea Stage 5 (see "Not this skill" below).

## Invocation

Every `journal`/`scope` command run as: `"~/.arti/python/python.exe"
"~/.arti/tools/arti-jfinder/cli.py" <subcommand> ...` (Mac/Linux: `~/.arti/python/bin/python3`).
No `--project` flag — it is a cross-project singleton like `arti-db`. Each call prints one JSON
object (`{"ok": true, ...}` or `{"ok": false, "error": ...}`); see
`~/.arti/tools/arti-jfinder/README.md` for the full subcommand surface. Backed by a
researcher-downloaded Scimago snapshot — if `journal search`/`get` returns `{"ok": false}` because
the database is empty or missing, tell the researcher to download the current-year export from
Scimago and run `ingest --file PATH --year YYYY`, then fall back to general knowledge rather than
blocking.

## Lookup flow

- **Free-text topic** ("journals about X", "list Q1 journals in materials science") → run
  `journal categories` first to get exact category strings (categories are matched exactly,
  case-insensitive — not free text), then `journal search --category TEXT [--quartile Q1|Q2|Q3|Q4]
  [--keyword TEXT] [--min-sjr N]`. Present results as a ranked table: title · SJR · quartile ·
  publisher.
- **Specific known journal** (name or Scimago source id) → `journal get --id SOURCEID` for full
  identity + latest-year metrics + categories. If only a name is known, resolve the id first with
  `journal search --keyword TEXT`.
- **Aims-and-scope question** → `scope get --id SOURCEID` first (cached). If it returns
  `{"ok": true, "row": null}` (never fetched), WebFetch the journal's own site and cache the result
  with `scope set --id SOURCEID --text TEXT --source-url URL` — same lazy-cache pattern as
  ARTi-idea Stage 5: never bulk-prefetch scope text for journals not actually asked about.
- **Empty/missing database** → same fallback as the invocation note above: tell the researcher to
  download the Scimago export and run `ingest`, then answer the current question from general
  knowledge rather than blocking.

## Not this skill

Defer to **ARTi-idea Stage 5** ("Journal Target Sheet") for:
- Ranking multiple candidate journals against a specific paper's idea/design
- The Predatory Journal Screen
- Novelty-threshold (C/M/E) analysis against a journal's fit
- Writing or updating `idea/journal-target-sheet.md`

This skill only answers standalone lookup/ranking questions — it never produces or edits a project
document.
