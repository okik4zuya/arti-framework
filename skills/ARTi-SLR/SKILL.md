---
name: ARTi-SLR
description: >
  A structured, PRISMA-compliant workflow for planning and conducting a systematic literature
  review (SLR) as a standalone review paper — from title/RQ/PICO(C) framing through protocol
  registration, multi-database search, deduplication, two-gate screening with logged exclusion
  reasons, extraction, quality appraisal, PRISMA Flow Diagram, and synthesis, ending with a
  handoff to ARTi-writing for drafting. Use this skill whenever a researcher wants to conduct a
  systematic review, scoping review, or PRISMA-reported literature review as the paper itself —
  not an informal scoping pass to justify novelty for an empirical paper (that stays
  `ARTi-idea`'s Gap Map). Triggers include: "I want to do a systematic literature review", "help me
  run an SLR", "PRISMA flow diagram", "screen these papers for inclusion/exclusion", "what's my
  PRISMA count", "build a synthesis matrix", "protocol for my review", "I want to publish a review
  paper". Always use this skill instead of ARTi-idea when the deliverable itself is the review
  (not an empirical study a review happens to support). Reuses `arti-lit` as the one literature
  database — no parallel Markdown log for paper records.
---

# ARTi-SLR Skill

A document-driven workflow for planning and conducting a standalone, PRISMA-compliant systematic
literature review — before handing off to `ARTi-writing` for actual drafting. Organized around
**six core documents** and **four sequential stages**, ending with a confirmed included-paper set,
a real PRISMA Flow Diagram, a synthesis matrix, and a target journal, ready to hand off.

**Not this skill:** an informal literature scoping pass to justify novelty for an *empirical*
paper — that is `ARTi-idea`'s Gap Map (Stage 2 there). If the researcher's deliverable is an
experiment/study and the literature review is just its Introduction section, use `ARTi-idea`, not
this skill. Use this skill only when the review itself is the publishable output. The Prior Review Check is
not `ARTi-crosscite` (does cluster A cite cluster B) and does not score novelty — it only records
which published reviews already cover the topic.

---

## Core Documents

### 1. Judul + RQ + PICO(C)
Title and research question decided together, framed with PICO(C) (Population, Intervention,
Comparison, Outcome, Context), checked against the Researcher Profile. See
`references/stage1-question-and-protocol.md` (Part A) and
`references/judul-rq-pico-template.md`.

**File:** `slr\judul-rq-pico.md`

---

### 2. Prior Review Check
Run after the Judul + RQ + PICO(C) is confirmed and before the Protocol is locked: do published
reviews already cover this question? OpenAlex ladder (narrow material to broad class) plus a
required Scopus `DOCTYPE(re)` query, a table of reviews found with their scope, a verdict (`clear`
/ `partial overlap` / `near-duplicate`) and the differentiating sentence for the Introduction. See
`references/stage1-question-and-protocol.md` (Part C) and `references/prior-review-check-template.md`.

**File:** `slr\prior-reviews.md`

---

### 3. Protocol
Locked before any search runs: the target database list, inclusion/exclusion criteria, search
strings derived from PICO(C) terms, and the quality-appraisal approach to be applied later. See
`references/stage1-question-and-protocol.md` (Part B) and `references/protocol-template.md`.

**File:** `slr\protocol.md`

---

### 4. Literature (via `arti-lit`, no new document)
Every candidate, screened or not, lives as one row in the project's existing `arti-lit.db` — the
same database `ARTi-ref` already owns. This skill adds three additive columns
(`search_source`, `screening_stage`, `exclusion_reason`) rather than a parallel store. See
`references/stage2-search-and-screening.md` for the search/dedup/screening procedure.

**File:** `literature\arti-lit.db` (owned by `ARTi-ref`; this skill only adds columns/values to it)

---

### 5. Matriks Sintesis (Synthesis Matrix)
Cross-paper themes and findings across every `included` source, built once extraction (Stage 3) is
complete. Has **three separate downstream outputs** — Blueprint content, an Idea Canvas gap-routing
check, and Journal Target Sheet input — not just one. See
`references/stage4-synthesis-and-handoff.md` and `references/synthesis-matrix-template.md`.

**File:** `slr\synthesis-matrix.md`

---

### 6. SLR Manuscript Blueprint
A paragraph-level outline for the review manuscript, shaped to drop into `ARTi-writing`'s own
Manuscript Blueprint stage alongside a Journal Profile. See
`references/slr-manuscript-blueprint-template.md`.

**File:** `slr\manuscript-blueprint.md`

---

## Workflow Stages

```
[U] Topik awal + [U] Wawancara → [M] Researcher Profile
        │                              │
        └──────────────┬───────────────┘
                        ▼
        [M] Judul + RQ + PICO(C)        (title and question decided together)
                        │
                        ▼
        [M] Cek Review Terdahulu ──w──► [DB] arti-lit (screening_stage=prior_review,
                        │                     di luar hitungan PRISMA)
                        │              (OpenAlex type=review + Scopus DOCTYPE(re), wajib)
                        ▼
        [M] Protokol  (kriteria inklusi/eksklusi + daftar database yang akan dicari)
                        │
                        ▼
        [M] Search Keyword → [U] Ris file, diulang PER DATABASE dalam daftar Protokol
                        │
                        ▼
        [M] Deduplikasi  ──r── [DB] arti-lit (skip yang sudah pernah masuk)
                        │
                        ▼
        [M] Screening Judul/Abstrak
                   │             │
                lolos      ditolak+alasan ──w──► [DB] arti-lit
                   │             (screening_stage=excluded_title_abstract, exclusion_reason=...)
                   ▼
        [U] Fulltext Paper ──w──► [DB] arti-lit
                   │
                   ▼
        [M] Screening Kelayakan
                   │             │
                lolos      ditolak+alasan ──w──► [DB] arti-lit
                   │             (screening_stage=excluded_eligibility, exclusion_reason=...)
                   ▼
        [M] Extract paper → Summary ──w──► [DB] arti-lit
                   │
                   ▼
        [M] Penilaian kualitas  (dilipat ke dalam Summary, tidak field baru)
                   │
          ┌────────┴─────────────────────────┐
          ▼                                   ▼
   [M] PRISMA Flow ◄──r── [DB] arti-lit       [M] Matriks Sintesis ◄──r── [DB] arti-lit
       (hitung tiap screening_stage)                 │
                                                       ├──► [M] SLR Manuscript Blueprint
                                                       ├──► [M] Idea Canvas (+Novelty)
                                                       │      (gerbang novelty yang SUDAH ADA
                                                       │       di ARTi-idea — bukan node baru)
                                                       │              ▼
                                                       │      [DB] Idea Bank Database
                                                       └──► [M] Journal Target Sheet ◄── [DB] Jfinder DB
                        ┌──────────────────────────────────┘
                        ▼
              [M] SLR Handoff   (dokumen penutup ARTi-SLR)
                        ▼ (lintas ke ARTi-writing)
              [M] Journal profile ◄── [U] Contoh paper
                        ▼
              [M] Manuscript Blueprint  ◄── SLR Handoff + Journal profile
                        ▼
              [M] Manuscript ◄──r── [DB] arti-lit
```

See `figures/arti-slr-workflow.png` for the submission diagram (intentionally simplified — the
dedup/exclusion-branch/multi-database/PRISMA-count detail above lives only here, not redrawn
there).

---

### Stage 1: Judul + RQ + PICO(C), Prior Review Check, then Protocol
**Trigger:** Researcher Profile exists (or `ARTi-setup` runs first if not); researcher has a
review topic in mind. **Output:** `slr\judul-rq-pico.md`, `slr\prior-reviews.md`,
`slr\protocol.md`. See
`references/stage1-question-and-protocol.md` for the full procedure.

---

### Stage 2: Search, Deduplication, and Screening
**Trigger:** Protocol locked. **Output:** every candidate registered in `arti-lit` with
`search_source`, and every row moved through `identified → title_abstract → eligible` (or an
`excluded_*` stage with a reason), looping the search once per database in the Protocol. See
`references/stage2-search-and-screening.md` for the full procedure.

---

### Stage 3: Extraction and Quality Appraisal
**Trigger:** At least one row reaches `eligible`. **Output:** each `eligible` row's `summary`
field carries both the structured extraction and the quality-appraisal outcome, then the row
moves to `included`. See `references/stage3-extraction-and-appraisal.md` for the full procedure.

---

### Stage 4: PRISMA Flow, Synthesis, and Handoff
**Trigger:** Screening complete (no rows left at `identified`/`title_abstract`/`eligible` that
should have a final stage). **Output:** PRISMA Flow Diagram (via `ARTi-figure`), `slr
\synthesis-matrix.md` (with all three outputs fired), `slr\manuscript-blueprint.md`, a Journal
Target Sheet, and the closing `slr\handoff.md`. See `references/stage4-synthesis-and-handoff.md`
for the full procedure.

---

## Handoff to ARTi-writing

When Stage 4 is complete, Claude writes `slr\handoff.md` (`references/slr-handoff-template.md`) —
the same "copy decisions, point at content, never transcribe" convention `ARTi-idea`'s own handoff
manifest uses. ARTi-writing's Manuscript Blueprint stage then has **two converging inputs**: this
handoff (which itself points at the SLR Manuscript Blueprint) and the Journal Profile (scope/voice
from the target journal's own example review papers) — the same two-input pattern the empirical
path already uses with Research Design + Journal profile.

Claude must explicitly tell the researcher when the handoff is ready — see the closing line in
`references/slr-handoff-template.md`.

---

## Key Principles

1. **Judul and RQ are decided together** — never draft a title before the RQ, never confirm an RQ
   without immediately compressing it into a working title.
2. **Check for a prior review before locking the Protocol** — the overlap check (OpenAlex ladder
   plus the required Scopus `DOCTYPE(re)` query) runs after the RQ is confirmed and before any
   Protocol effort; a `near-duplicate` verdict sends the RQ back to the researcher. Re-run it
   before submission.
3. **Protocol before search** — the database list and inclusion/exclusion criteria are locked
   before Stage 2 runs; a change after search starts is logged, not silently made.
4. **Search is repeated per database, never assumed single-source** — Stage 2 loops explicitly
   over the Protocol's database list.
5. **Deduplication reads `arti-lit` before every screening pass** — reuse the existing DOI-dedup
   rule and `library search` pre-check; no new dedup subcommand.
6. **Every screening reject carries a reason tied to a Protocol criterion** — a pass with no
   logged reject count, or a reject with no reason, breaks the PRISMA Flow Diagram's honesty.
7. **PRISMA counts are computed, never asserted** — one `library list --screening-stage X` call
   per stage value, not a number recalled from memory or estimated late.
8. **No new fields for what free text already covers** — quality appraisal and structured
   extraction both live in `sources.summary`; do not propose a parallel table or document for
   either.
9. **Matriks Sintesis has three outputs, not one** — Blueprint content, Idea Canvas gap-routing,
   and Journal Target Sheet input all fire from the same synthesis pass.
10. **Novelty scoring never happens directly on a review's own gaps** — any future-study gap
   noticed during synthesis is routed through ARTi-idea's existing Idea Canvas gate, keeping the
   Idea Bank's quality bar consistent regardless of source. The review's own journal choice is
   topic-driven and bypasses that gate entirely. The Prior Review Check (Principle 2) is a different
   thing: a factual overlap check against published reviews, never a novelty score of an idea.
11. **Copy decisions, point at content** — the SLR Handoff records what was decided and where each
    document lives; it never transcribes those documents.

---

## Reference Files

**`arti-lit` invocation** — every `library`/`refs` command below runs as: `"~/.arti/python/
python.exe" "~/.arti/tools/arti-lit/cli.py" <subcommand> ... --project PATH` (Mac/Linux:
`~/.arti/python/bin/python3`). See `ARTi-ref`'s SKILL.md for the base invocation and
`~/.arti/tools/arti-lit/README.md`'s Schema section for the `search_source`/`screening_stage`/
`exclusion_reason` columns this skill adds. `screening_stage` is a closed vocabulary: `identified |
title_abstract | eligible | included | excluded_title_abstract | excluded_eligibility |
prior_review` — both `library add`/`update` reject any other value. `prior_review` marks a
previously published review from the Prior Review Check; it is outside the PRISMA flow, so exact-match
stage counts never include it.

**`arti-pdf-ingest` invocation** — unmodified, see `ARTi-ref`'s Fulltext ingestion section, used
for the Fulltext Paper step in Stage 2.

**`arti-figure` invocation** — unmodified, see its own SKILL.md's diagram lane, used to render the
PRISMA Flow Diagram from the counts Stage 4 computes.

**`arti-db`/`arti-jfinder` invocation** — unmodified, see `ARTi-idea`'s Reference Files section;
used for Idea Bank writes (via the Idea Canvas gate) and Journal Target Sheet lookups respectively.

- `references/stage1-question-and-protocol.md` — Stage 1 procedure (Judul+RQ+PICO(C), Prior
  Review Check, then Protocol)
- `references/prior-review-check-template.md` — blank Prior Review Check document
- `references/judul-rq-pico-template.md` — blank Judul + RQ + PICO(C) document
- `references/protocol-template.md` — blank Protocol document
- `references/stage2-search-and-screening.md` — Stage 2 procedure: per-database search loop, dedup
  rule, both screening gates with reason logging
- `references/stage3-extraction-and-appraisal.md` — Stage 3 procedure: extraction + quality
  appraisal folded into `summary`, closing the `eligible → included` gate
- `references/stage4-synthesis-and-handoff.md` — Stage 4 procedure: PRISMA count query, the
  three-way Matriks Sintesis output, closing SLR Handoff
- `references/synthesis-matrix-template.md` — blank Matriks Sintesis
- `references/slr-manuscript-blueprint-template.md` — blank SLR Manuscript Blueprint
- `references/slr-handoff-template.md` — blank SLR Handoff (closing document)

Read the relevant reference file before starting any stage.

## Change log
- 2026-10-01 — Added the Prior Review Check (Stage 1 Part C, `references/prior-review-check-template.md`,
  output `slr\prior-reviews.md`): OpenAlex narrow-to-broad ladder via the upgraded
  `arti-ref-search-mcp` (`count_openalex_works`, `search_openalex_works(work_type="review")`) plus a
  required researcher-run Scopus `DOCTYPE(re)` query; found reviews stored in `arti-lit` with the new
  `prior_review` screening stage (outside PRISMA counts). Core documents 5 → 6, Principles 10 → 11.
  Pointers added to the Blueprint template (Introduction paragraph 2), Stage 4 and the Handoff.
- 2026-09-27 — Added a sanity-check step to Stage 1 Part B (`stage1-question-and-protocol.md`):
  before locking the Intervention angle list, check it against at least one paper already known to
  be in scope, and specifically watch for two commonly-missed angle types in materials/synthesis
  reviews — surface/synthesis-condition modification (annealing, hydroxylation, facet engineering)
  as distinct from doping/heterostructure/defect-engineering, and pristine/unmodified baseline
  studies (needed for the review's own Comparison element, easy to assume will show up embedded in
  other papers when it doesn't get its own angle). Learned from the same live SLR session: a
  5-angle search missed Torres et al. (2020) — a pristine-SnO2 surface-hydroxylation CO2-
  photoreduction study — because none of the 5 locked angles covered either missed category; the
  gap was only caught when the researcher manually found the paper and asked why it wasn't in
  Scopus results, well after Stage 2 search had already started.
- 2026-09-27 — Stage 2's `search_source` backfill instruction (`stage2-search-and-screening.md`)
  strengthened: do the `library update --search-source` backfill immediately after each individual
  `import-ris` call, before running the next one, especially with multiple per-angle queries —
  batching imports first loses per-angle attribution since `created_at` timestamps land within the
  same second. Added a recovery path for when this already happened: if the per-angle RIS export
  files still exist (or the researcher can supply them), parse each file's `DO`/`TI` fields and
  match against `sources.doi`/`citation`, attributing to the *earliest* angle whose file matches
  (mirroring `import-ris`'s first-import-wins dedup) — only fall back to a database-level
  `search_source` if the RIS files are genuinely gone. Learned from a live SLR session: 5 angle-query
  RIS files were all imported before any backfill; the researcher then supplied the kept RIS files,
  which let 80 rows be re-attributed per-angle instead of staying at a flat "Scopus" tag (39 DOIs
  had overlapped 2+ angle files, requiring the earliest-match rule).
- 2026-09-27 — Stage 1's search-string construction guidance (`stage1-question-and-protocol.md`
  Part B, `protocol-template.md`) revised: never OR multiple Intervention sub-strategies into one
  combined string (inflates hits into the thousands+), split into one query per sub-strategy angle
  instead; prefer exact multi-word Outcome phrases over bare generic words; always include the
  database's explicit field-scope function (e.g. Scopus `TITLE-ABS-KEY(...)`) — omitting it changes
  the search mode to a broad fuzzy match, not a simplification. Learned from a live SLR session
  (Paper Review SLR SnO2 Photocatalyst project) where a combined string hit 22,062 results, and
  removing the field-scope wrapper (misread as just verbose syntax) hit 14,000 results with the
  core P-term not even appearing in returned titles/abstracts.
- 2026-09-27 — created: single-skill ARTi-SLR (not the roadmap's originally-listed two-skill
  split), reusing `arti-lit` as the one literature database via three additive columns
  (`search_source`/`screening_stage`/`exclusion_reason`) rather than a new tool. See
  `~/.arti/memory/memories/arti-slr-build.md` for the design record.
