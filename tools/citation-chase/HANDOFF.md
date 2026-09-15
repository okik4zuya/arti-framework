# Citation-Chase Tool — Development Brief

**Status:** brief only. No code exists yet. Written 2026-09-14.

This document is the complete brief for a small cross-project tool. It assumes **no** knowledge of
any specific paper the researcher is writing, no memory of the conversation that produced it, and
no knowledge of the "ARTi" workflow beyond what's restated here. Everything needed to start is
here. Real DOIs from one live use case are given in the Appendix as fixtures — use them, don't
invent test data.

---

## 1. Purpose and the motivating case

A researcher building a systematic literature review (SLR) needs to answer a narrow, recurring
question: **"does paper/cluster A already cite paper/cluster B, or vice versa?"** — not a full
bibliometric analysis, just a bounded overlap check between two named sets of papers.

**Concrete motivating case** (project: `Paper SLR Nanobubble in Reaction`, see Appendix): the
review's central novelty claim depends on two literatures — a "mechanistic dispute" cluster (7
anchor papers) and an "emerging application" cluster (14 papers) — never having been cross-read.
The Gap Map supporting this claim was built from **abstracts only**. Before the claim can be
written into the manuscript, someone must check: do any of the 14 papers already cite any of the
7, or vice versa? If yes even for 2–3 papers, the claim needs qualifying language instead of a flat
"no existing work has done this."

Today this check would be done by hand — opening each paper's reference list and cited-by page one
at a time across up to 21+ papers, either in Scopus (institutional access, UI-based) or Google
Scholar (no login, but no official API either). That does not scale past a handful of papers and
leaves no audit trail of what was checked.

**This is a generically useful tool, not a one-project script** — any future ARTi-idea Gap Map
that claims "these two clusters don't cite each other" needs the same check. Build it as a
cross-project singleton under `~/.arti/tools/`, the same way `arti-jfinder` and `arti-db` are
cross-project (no `--project` flag; a project's own files are only ever an *input* — a list of DOIs
— never a scope the tool is aware of).

---

## 2. Success criteria

Given two named sets of papers (by DOI), the tool reports, for every paper in Set A:

1. Whether it **cites** (backward / reference list) any paper in Set B.
2. Whether it **is cited by** (forward / cited-by) any paper in Set B.
3. A **confidence/source** field — which citation database answered the question, since different
   databases (OpenAlex, Semantic Scholar, Scopus, Google Scholar) do not agree on citation counts
   and coverage varies especially for very recent (2025–2026) papers.

A run must be:
- **Resumable** — a DOI already resolved is not re-queried on a re-run.
- **Partial-failure-tolerant** — one DOI that can't be resolved (no database has it, rate-limited,
  malformed) is recorded as `error` and does not abort the batch.
- **Auditable** — output says exactly which database and which query answered each verdict, not
  just a bare yes/no.

---

## 3. Implementation paths — decide this first, in this order

### Path A — OpenAlex API (recommended default; check this first)

`https://api.openalex.org/works/https://doi.org/<DOI>` — free, keyless, no rate-limit
registration required for reasonable volumes (polite pool via a `mailto` query param is enough).

Each OpenAlex "work" object already carries:
- `referenced_works` — a list of OpenAlex IDs this paper cites (**backward citations, structured,
  no fulltext needed**).
- A `cited_by_api_url` field — a ready-made query (`filter=cites:<openalex_id>`) that returns every
  work citing this one (**forward citations**).

This means the entire citation-chase — both directions — is potentially answerable from OpenAlex's
structured metadata alone, without ever touching fulltext PDFs or scraping anything. **Verify this
claim in-browser/via curl before coding** (see §6) — OpenAlex's reference-list coverage is good but
not universal, especially for 2025–2026 papers that may not be indexed yet.

### Path B — Semantic Scholar Graph API (fallback / cross-check)

`https://api.semanticscholar.org/graph/v1/paper/DOI:<DOI>?fields=references,citations` — free,
keyless for low volume, generous rate limits. Similar structured citations+references payload.
Use as a **cross-check when OpenAlex has no record**, or when a second source is wanted for
confidence — not as the sole source, since coverage/data quality differs paper-to-paper.

### Path C — Scopus Search/Citation API (only if entitlement confirmed)

Same institutional-entitlement question already open for the sibling tool
`~/.arti/tools/scopus-ris-batch-export/HANDOFF.md` (§3 there) — if that tool's entitlement check
was ever done, **reuse the answer instead of re-deriving it**; check that tool's directory for any
resolution notes before assuming Scopus API access is or isn't available. If entitlement exists,
Scopus's own cited-by count is authoritative for the researcher's own literature reviews and worth
adding as a third source. Do not build this path first — it duplicates infrastructure Paths A/B
give for free.

### Path D — Google Scholar — do not build this

No official API. Any programmatic access is scraping against Google's terms, is fragile against
layout/bot-detection changes, and every existing "Scholar API" wrapper library exists in this same
grey zone. **Do not implement this path.** If OpenAlex and Semantic Scholar both miss a paper
(realistic for very new preprints or non-English-indexed venues), the honest output is
`"not found in queried sources"` — surfaced to the researcher to check by hand — not a scraper.

### Recommendation

Build Path A alone first (walking skeleton, §8). Add Path B only for DOIs Path A can't resolve.
Do not touch Path C without checking the sibling tool's entitlement notes first. Never build Path D.

---

## 4. Functional spec

**Input:** two named sets of DOIs — `--set-a` and `--set-b` — each a newline- or comma-separated
list, or a `--file PATH` pointing at a plain-text file with one DOI per line. (A convenience layer
that resolves `arti-lit` keys to DOIs via `library get --key KEY --project PATH` is a nice-to-have,
not required for v1 — plain DOIs in, per the walking skeleton.)

**Per DOI in Set A, in order:**

1. Resolve the DOI to an OpenAlex work ID (`GET /works/https://doi.org/<doi>`).
2. Extract `referenced_works` (backward) — resolve each referenced work's DOI, check membership in
   Set B.
3. Query the work's `cited_by_api_url` (forward) — resolve each citing work's DOI, check membership
   in Set B.
4. If the OpenAlex lookup 404s (DOI not indexed), fall back to Path B (Semantic Scholar) for that
   DOI only.
5. Emit one result row per Set-A DOI: which Set-B DOIs it cites, which Set-B DOIs cite it, which
   source(s) answered, and `status: ok | partial | error`.

**Repeat symmetrically is not required** — checking A→B in both citation directions for every A-DOI
already answers "do these two clusters cite each other," since a B-paper citing an A-paper is the
same edge as the A-paper being cited by a B-paper. Do not double-query B→A as well; it's redundant
work against the same free-tier rate limits.

**Robustness requirements** — same shape as `scopus-ris-batch-export`'s manifest:
- Resume: reload existing output on startup, skip DOIs already `ok`.
- Skip-if-answered: a DOI whose row is `ok` is not re-queried.
- Per-DOI failure is recorded (`status: error`, message), never fatal to the batch.
- Rate-limit backoff: OpenAlex/Semantic Scholar both 429 under burst load — a simple exponential
  backoff with a fixed max-retry count is enough; do not build a queue-management system.

---

## 5. Output schema — one JSON object per row + a final summary

Follow the existing `~/.arti/tools/*` convention exactly (see `arti-pdf-ingest/README.md` for the
precedent): print one JSON object per Set-A DOI to stdout as it resolves, plus a final summary
object. Never a single all-or-nothing exit code.

```json
{"doi": "10.1021/acsestengg.3c00124", "key": "Chae-2023 (if resolved)", "cites_from_set_b": [], "cited_by_from_set_b": ["10.xxxx/..."], "source": "openalex", "status": "ok"}
...
{"summary": {"ok": 6, "partial": 1, "error": 0, "overlaps_found": 1}}
```

`overlaps_found` in the summary is the number that actually matters to the researcher — if it's 0
across the whole batch, the "these clusters have never been cross-read" claim is confirmed; if
nonzero, the specific overlapping pairs are what needs surfacing into the manuscript's wording.

Optionally also write a human-readable Markdown table (`overlap-report.md`) next to the JSON,
listing only rows where an overlap was found — the researcher should not have to read raw JSON to
get the answer that matters.

---

## 6. Facts to verify before coding (do not assume)

1. **Does OpenAlex actually resolve all 21 DOIs in the Appendix?** Some are 2026-dated (not yet
   published at brief-writing time from the researcher's perspective, but real entries in their
   `arti-lit.db` — check whether OpenAlex has indexed them yet; if not, that DOI is `status:
   "not_found"`, not an error).
2. **Coverage of `referenced_works`** — OpenAlex resolves this from Crossref/publisher metadata;
   confirm empirically that at least the older Appendix DOIs (Yasui-2018, John-2024) return a
   non-empty reference list before assuming the backward-citation direction works at all.
3. **Rate limits** — OpenAlex's stated polite-pool guidance and Semantic Scholar's unauthenticated
   rate limit; confirm both are workable for a ~21-DOI batch without needing an API key from either.

---

## 7. Non-goals (v1)

- No citation-network visualization or graph export.
- No full bibliometric analysis (h-index, co-citation clustering, etc.) — this is a yes/no overlap
  check between two named sets, nothing more.
- No Google Scholar path, ever (see Path D).
- No automatic manuscript-text generation from the overlap result — the tool reports facts; the
  researcher/Claude decides how to phrase the novelty claim based on them.
- No project-awareness (`--project` flag) — this tool takes DOI lists in and returns overlap facts
  out; where those DOIs came from is the caller's concern, not this tool's.

---

## 8. Walking skeleton

Smallest thing that proves the whole chain, before any batching:

**One DOI in Set A → OpenAlex lookup → check against a 2-DOI Set B → one correct JSON row.**

Specifically: use `Chae-2023` (`10.1021/acsestengg.3c00124`) as the sole Set-A entry and
`Bose-2026` (`10.1126/sciadv.aec4225`) + `Zheng-2025` (`10.3390/nano15161270`) as Set B (both real
Appendix fixtures). Confirm the tool correctly reports whichever of "cites" / "cited by" / neither
is actually true for that trio, with `source: "openalex"` and `status: "ok"`. Everything in §4 is
an increment on top of that.

Suggested order after the skeleton: (1) full Set-A batch against the Appendix's real 7-vs-14 case,
(2) resume/skip-if-answered, (3) Semantic Scholar fallback for `not_found` DOIs, (4) the
`overlap-report.md` human-readable summary, (5) 429 backoff handling.

---

## Appendix — real fixtures for development (live use case, not invented test data)

From `Paper SLR Nanobubble in Reaction`'s `idea/research-design.md` (2026-09-14) — the exact
citation-chase this tool needs to run once built.

**Set A — Gap 1 mechanistic-dispute anchors (7 DOIs):**

| Key | DOI |
|---|---|
| Chae-2023 | 10.1021/acsestengg.3c00124 |
| Yasui-2018 | 10.1016/j.ultsonch.2018.05.038 |
| Wang-2026a | 10.1016/j.watres.2026.126310 |
| John-2024 | 10.1016/j.ces.2023.119369 |
| Messina-2025 | 10.1016/j.cej.2025.169390 |
| Yang-2025 | 10.1038/s41467-025-63899-w |
| Xu-2026 | 10.1021/jacs.5c16083 |

**Set B — Gap 6 CO₂-nanobubble cluster (14 DOIs):**

| Key | DOI |
|---|---|
| Li-2026f | 10.1016/j.watres.2025.124714 |
| Li-2026g | 10.2118/232804-PA |
| Mao-2025 | 10.2118/228090-MS |
| Mao-2026 | 10.2118/228090-PA |
| Montazeri-2025 | 10.1007/s40831-025-01081-8 |
| Li-2025a | 10.1038/s42004-025-01645-5 |
| Yin-2025 | 10.12438/cst.2025-0447 |
| Zeitoun-2026 | 10.1016/j.cep.2026.111041 |
| Sharma-2025 | 10.1016/j.jece.2025.119559 |
| Shen-2023 | 10.1016/j.cjche.2023.06.003 |
| Shi-2026 | 10.1016/j.memsci.2026.125825 |
| Sun-2022 | 10.1016/j.biortech.2022.127991 |
| Pang-2025 | 10.1021/acs.langmuir.5c00646 |
| Zheng-2025 | 10.3390/nano15161270 |

Expected use once built: `citation-chase --set-a <7 DOIs above> --set-b <14 DOIs above>` — the
output's `overlaps_found` count directly resolves the open 🟡 feasibility flag in that project's
`idea/research-design.md` ("cross-domain citation-chase not yet run").

## Change log
- 2026-09-14: brief written, no code yet.
