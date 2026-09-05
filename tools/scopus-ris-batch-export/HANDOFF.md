# Scopus RIS Batch Export — Development Brief

**Status:** brief only. No code exists yet. Written 2026-09-05.

This document is the complete brief for a small tool project. It assumes **no** knowledge of the
researcher's other work, no knowledge of the "ARTi" writing workflow, and no memory of the
conversation that produced it. Everything needed to start is here.

Facts about Scopus below are either **cited to a real file** the researcher exported on 2026-09-04
(paths given, all under `G:\My Drive\RESEARCH\2026 Jul-Des\Paper Metnum ECE\literature\scopus_2\`),
or listed in **§6 as an unknown to verify in-browser before coding**. Nothing is asserted from
assumption.

---

## 1. Purpose and the measured current flow

A researcher runs literature searches on Scopus using institutional access, one query at a time, and
exports each result set as RIS. In one search round on 2026-09-04 this produced **27 RIS files** from
27 queries.

| Step | Done by | Measured cost in that round |
|---|---|---|
| Draft the list of queries | assistant, in chat | 30+ queries across two rounds |
| Paste one query into Scopus, press enter | researcher | ×27 |
| Read the hit count off the screen | researcher | ×27 |
| Select all → Export → RIS → download | researcher | ×27 |
| Rename the downloaded file by hand | researcher | every file, to `scopus_export_<Mon D-YYYY>_<query>.ris` — e.g. `scopus_export_Sep 4-2026_ Eberlein AND POGIL .ris` (note the stray spaces, which are in the real filenames) |
| Hand-type `query: hit count` into a notes file | researcher | 27 lines in `scopus_2.md` |
| Copy the files into the project | researcher | five ad-hoc folders resulted |

**The defect worth fixing is not the clicking — it is that provenance is lost.**

Hit count, applied filters, and date are re-keyed by hand into free prose and drift immediately.
Two verified illustrations from that round:

- `scopus_2.md` line 13 reads, in full: `"Motivated Strategies for Learning Questionnaire" : 675, but extracted only 84, filter in engineering subject from 2015`. The corresponding RIS file contains exactly **84 records** (counted: 84 × `ER  -`). That sentence is the only record anywhere that a subject/year filter was applied to that query, and it is unparseable by anything but a human.
- The same file mixes two query notations — bare (`"peer instruction" AND "Mazur"`) and field-wrapped (`TITLE-ABS-KEY ( "cognitive load" AND "novice programmers" )`) — plus trailing spaces and inconsistent leading indentation used informally to mean "this query refines the one above."

**Critical verified constraint:** *the query string is not recoverable from the exported file.* A
Scopus RIS record carries `TY / AU / TI / PY / T2 / VL / IS / SP / EP / DO / UR / AB / M3 / DB / N1`,
where `N1` is only `Export Date: 04 September 2026; Cited By: 399` (verified in
`scopus_export_Sep 4-2026_ Effectiveness of Mastery Learning Programs .ris`). There is **no query
field, no hit-count field, and no filter field.** Provenance therefore has to be captured at export
time or it does not exist. That single fact is the reason this tool's primary output is a manifest,
not the RIS files.

---

## 2. Success criteria

One paste of N newline-separated queries produces:

1. **N RIS files**, deterministically named, with **zero hand-renaming**.
2. **One machine-readable manifest** (`search-log.json`, §5) with **zero hand-typed hit counts**, recording for each query: what was typed, what was actually run, which filters applied, how many hits existed, how many records were exported, and whether it succeeded.
3. A run that can be **interrupted and resumed** without re-exporting what already succeeded.
4. A per-query failure that is **recorded and skipped**, never one that aborts the batch.

Corollary: after a run, `hit count` and `records exported` differing (675 vs 84 above) must be
visible as two separate numeric fields, not inferable only from a human sentence.

---

## 3. Two implementation paths — decide this first

### Path A — Elsevier Scopus Search API (recommended to evaluate first)

`api.elsevier.com/content/search/scopus`, authenticated with an API key plus, for full institutional
entitlement, an institutional token; requests generally must originate from the subscribing
institution's network or be tied to that entitlement.

| Pro | Con |
|---|---|
| Sanctioned, documented, stable — immune to UI churn and bot detection | Entitlement varies by institution; the researcher's level is **unknown and must be checked** |
| Returns hit count as a first-class field | Returns JSON/XML with a limited field set, so **RIS must be synthesized** from it |
| Pagination and result caps are documented rather than guessed | Abstract/keyword availability depends on the entitlement tier |

### Path B — MV3 browser extension driving the logged-in Scopus UI

| Pro | Con |
|---|---|
| Uses exactly the access the researcher already has, with no entitlement question | Every DOM selector is fragile against an SPA that can change without notice |
| Reproduces the flow they already perform by hand | Repeated automated queries risk session challenges / CAPTCHA |

### Recommendation

**Check the API entitlement before writing any extension code.** If Path A is available it removes
every DOM-fragility and bot-detection risk at once, and the only real work becomes JSON → RIS
synthesis. Fall back to Path B only if entitlement is absent or too limited.

### Constraint that shapes either design (read before the spec)

Elsevier's terms restrict automated and systematic downloading. This tool must therefore stay inside
**normal interactive use of the researcher's own institutional access**. If Path B is built, scope it
as a **human-paced queue assistant**, not a headless bulk scraper:

- The researcher stays on the Scopus page, logged in, watching it happen.
- Queries run **one at a time**, with a visible inter-query delay and a **stop control** that halts the queue immediately.
- No parallel tabs, no background execution with the browser unattended, no attempt to evade rate limits or challenges. If Scopus presents a challenge, the tool **pauses and hands control back** — it never tries to solve or route around it.
- The tool automates the *bookkeeping* the researcher does badly by hand; it does not increase the volume of what they retrieve.

State this constraint in the repo's README too, so it shapes the design rather than being discovered
late.

---

## 4. Functional spec

**Input.** A textarea accepting newline-separated queries, **taken verbatim**. Both notations must be
accepted and preserved as typed, because they mean different things to the researcher:

```
"peer instruction" AND "Mazur"
"POGIL" AND ( "meta-analysis" OR "effectiveness" )
TITLE ( "Effectiveness of Mastery Learning Programs" )
SRCTITLE ( "Education for Chemical Engineers" )
```

Bare strings go to the basic search box, which already scopes to title/abstract/keywords. Field
wrappers that encode a genuinely different scope (`TITLE(...)` for an exact-title search,
`SRCTITLE(...)` to restrict to one journal) are kept wrapped. The tool must not rewrite either form —
it records the query **as typed** and, separately, **as normalized/submitted**.

**Optional run-level settings.** Any filters to apply uniformly (subject area, year range) — recorded
per row in the manifest, since this is precisely the provenance that is lost today.

**Per query, in order:**

1. Submit the query.
2. Capture the **hit count**.
3. Apply configured filters; re-capture the post-filter count.
4. Select all → export RIS.
5. Save with a deterministic filename (§8).
6. Append a manifest row.
7. Wait the configured delay, then continue.

**Robustness requirements.**

- **Resume after interruption** — reload the existing manifest on startup, keep completed rows.
- **Skip-if-already-exported** — a query whose row is `ok` and whose file exists is not re-run.
- **Per-query failure is recorded, not fatal** — write the row with `status: "error"` and a message, then continue to the next query.
- **Export cap handling** — if a result set exceeds whatever per-export record cap Scopus enforces (§6), record `records_exported` honestly and set `status: "partial"`. Never silently report a truncated export as complete.

---

## 5. Manifest schema — `search-log.json`

Written next to the RIS files. One object per query, in run order.

```json
{
  "run_id": "2026-09-04T09:12:33+07:00",
  "source": "scopus",
  "access_path": "api | ui",
  "filters_run_level": "subject: Engineering; years: 2015-2026",
  "queries": [
    {
      "id": "k01",
      "query_as_typed": "\"Motivated Strategies for Learning Questionnaire\"",
      "query_normalized": "TITLE-ABS-KEY(\"Motivated Strategies for Learning Questionnaire\")",
      "filters_applied": "subject: Engineering; years: 2015-2026",
      "hits_total": 675,
      "hits_after_filters": 84,
      "records_exported": 84,
      "timestamp": "2026-09-04T09:14:02+07:00",
      "output_file": "k01_motivated-strategies-for-learning-questionnaire.ris",
      "status": "ok",
      "message": ""
    }
  ]
}
```

`status` ∈ `ok` | `partial` | `error` | `pending`. `hits_total` is the pre-filter count;
`hits_after_filters` equals it when no filter was applied. Keeping the two separate is what makes the
`675 / 84` case machine-readable instead of a sentence.

**Field-for-field map to the consuming workflow's log table** (a markdown table with columns
`ID | query | date | hits | export file | target claim | status`):

| `search-log.json` field | markdown column |
|---|---|
| `id` | ID |
| `query_as_typed` | query |
| `timestamp` | date |
| `hits_after_filters` (with `hits_total` in parentheses when they differ) | hits |
| `output_file` | export file |
| — *(filled in later by the researcher/assistant, not the tool)* | target claim |
| `status` | status *(the consuming table then narrows `ok` to `screened — N used` / `screened — none relevant` after screening)* |

`filters_applied` has no markdown column and is deliberately kept only in the JSON — it is
reference detail, surfaced on demand rather than in the at-a-glance table.

---

## 6. Scopus mechanics to verify in-browser before coding

Do not guess any of these. Open Scopus logged in, run one query by hand with devtools open, and
answer each:

1. **Result count** — is the hit count present in the DOM, or only in an XHR/fetch JSON response? If the latter, capture it there; it is more stable than scraping rendered text.
2. **Search submission** — does the SPA update the URL with the query (making direct navigation possible), or does it require driving the input element and a submit event?
3. **Select-all ceiling** — is there a maximum number of results selectable at once, and does the UI cap export size independently? **Largest export observed in the sample data: 571 records** in one file (`scopus_export_Sep 4-2026_self-efficacy AND Bandura AND social cognitive theory.ris`, counted as 571 × `ER  -`, matching the 571 hits recorded by hand). So the cap, if any, is **above 571** — but the actual limit is unverified.
4. **Export request shape** — what POST (URL, headers, body) does "Export → RIS" issue? Can it be replayed directly with the session's cookies, which would remove all download-plumbing fragility?
5. **Filename control** — can `chrome.downloads.onDeterminingFilename` rename the download, or must the response body be captured and written directly? Scopus's default download name is generic, which is why every file was renamed by hand.
6. **Session behaviour under repeated queries** — how many queries in a row before a challenge, a slowdown, or a session expiry appears? This sets the default inter-query delay.
7. **Filter application** — are subject-area and year filters expressible in the query string itself, or only as post-search UI facets? This decides whether `filters_applied` is set before or after the search.

---

## 7. Known data defect to normalize

Scopus RIS emits **un-substituted i18n keys** in place of RIS type codes. Counted across all 27 files
in the sample folder:

| `TY` value emitted | Count | Correct RIS code |
|---|---|---|
| `JOUR` | 984 | — (valid) |
| `CONF` | 480 | — (valid) |
| `label.ris.referenceType.BOOK_CHAPTER` | 125 | `CHAP` |
| `label.ris.referenceType.CONFERENCE_REVIEW.p` | 16 | `JOUR` (or `CONF`, per the importing tool's convention) |
| `BOOK` | 7 | — (valid) |

First line of `scopus_export_Sep 4-2026_ Eberlein AND POGIL .ris` is literally
`TY  - label.ris.referenceType.BOOK_CHAPTER`.

**This brief assigns the fix to the tool:** normalize `TY` on write, and record in the manifest that
normalization was applied (so a downstream parser knows whether to expect raw or cleaned files).
Map any unrecognized `label.ris.referenceType.*` value to `GEN` rather than dropping the record, and
log it.

---

## 8. Output contract

- **Location:** the consuming project's `literature\exports\` folder — a plain directory of raw exports plus the manifest. Configurable; nothing else in that folder is touched.
- **Filename:** `<id>_<slugified query>.ris` — e.g. `k01_motivated-strategies-for-learning-questionnaire.ris`. Lowercase, spaces and punctuation to hyphens, truncated to a safe length, `id` guaranteeing uniqueness when two queries slugify alike.
- **Manifest:** `search-log.json` in the same folder — this is the handoff artifact. A downstream assistant reads it to build its own literature log; it never needs to re-derive provenance from filenames.
- **Idempotence:** re-running the same query list against an existing manifest is a no-op for rows already `ok`.

---

## 9. Non-goals (v1)

- No screening, ranking, or relevance judgement.
- No deduplication across queries — downstream does that by DOI.
- No fulltext or PDF retrieval.
- No databases other than Scopus.
- No headless or unattended operation (see §3's constraint).

---

## 10. Walking skeleton

Smallest thing that proves the whole chain, before any batching:

**One query → one RIS file on disk → one correct manifest row.**

Specifically: type `"Eberlein" AND "POGIL"` (2 hits in the sample round, so it is fast and its
expected output is known — `scopus_export_Sep 4-2026_ Eberlein AND POGIL .ris` in the sample folder
holds the answer to compare against), capture the hit count, export, save as
`k01_eberlein-and-pogil.ris`, and write a `search-log.json` with one row where `hits_total`,
`records_exported`, and `status: "ok"` are all correct. Everything in §4 is an increment on top of
that.

Suggested order after the skeleton: (1) the query queue with delay and stop control, (2) manifest
resume + skip-if-exported, (3) filters and the `hits_total`/`hits_after_filters` split, (4) `TY`
normalization, (5) error rows and `partial` status.

---

## Appendix — sample data for development

All under `G:\My Drive\RESEARCH\2026 Jul-Des\Paper Metnum ECE\literature\scopus_2\`, exported
2026-09-04. Useful as fixtures without touching Scopus:

| File / fact | Use |
|---|---|
| 27 `scopus_export_Sep 4-2026_*.ris` files | parser fixtures, hand-renaming evidence |
| `scopus_2.md` | the hand-kept log this tool replaces; line 13 is the provenance-loss example |
| `...Effectiveness of Mastery Learning Programs .ris` | 1 record — minimal well-formed fixture, shows the complete field set |
| `... Eberlein AND POGIL .ris` | 2 records — both carry the `BOOK_CHAPTER` i18n defect |
| `...self-efficacy AND Bandura AND social cognitive theory.ris` | 571 records — largest observed export |
| `... Motivated Strategies for Learning Questionnaire .ris` | 84 records against 675 hits — the filtered case the manifest must represent |
