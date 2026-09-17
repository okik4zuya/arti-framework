# Stage 5 — Journal Target Sheet: rank cheap, read narrow

Full procedure for building the Journal Target Sheet (Core Document #5). Read this when Stage 5
fires — see `SKILL.md`'s Stage 5 stub for the trigger condition and output file. For the blank
output structure (per-journal fields, Journal Comparison Table, ranked shortlist), see
`references/journal-target-sheet-template.md` — this file covers process only.

Researchers do not run a five-way comparative study; they have a target and a fallback. Ranking
happens on free signals first, and papers are read only for the top two.

## Step (i) — Rank on free signals. No papers are read here.

- Researcher nominates candidate journals (3–5 is typical)
- Rank them on signals that cost nothing to obtain:
  - **Scope fit** — the journal's own aims & scope against the confirmed research question
  - **Q-rank / indexing** — Scopus, WoS, quartile
  - **The group's own history** — journals the researcher, their supervisor, or their group has
    published in before
- Present the ranking and confirm the top two with the researcher before reading anything

Candidates are ranked using real Scimago data via `arti-jfinder` rather than general knowledge
alone: run `journal categories` to get exact category text, then `journal search --category TEXT
[--quartile Q1] [--keyword TEXT]` for a ranked-by-SJR candidate list, and `journal get --id
SOURCEID` for a specific candidate's full metrics.

## Step (ii) — Light analysis for the top 2 only

For each of the two, in order:
- Check `~/.arti/journal-library/<journal-slug>.md` first. If a cached entry exists and its
  `last verified` date is recent, offer to reuse it instead of re-extracting; otherwise run the
  analysis below and write/update the cache entry
- Run the **Predatory Journal Screen** (conditional — see below)
- Analyze 2–3 example papers (provided by the researcher) for any journal not served from cache
- For each paper: extract the novelty profile (C/M/E estimate) to establish the journal's typical
  novelty threshold
- Compare the research idea's novelty score against that threshold

Aims-and-scope text is not bulk-fetched — for the top two candidates only, WebFetch the journal's
own site and cache the result with `scope set --id SOURCEID --text TEXT --source-url URL` (check
`scope get` first so a re-run doesn't refetch).

## Step (iii) — Stop as soon as #1 clears

If the top-ranked journal passes the predatory screen, fits on scope, and clears the novelty
threshold, it is confirmed — **#2's papers are never opened.** Only fall through to #2 if #1
fails on one of those three. Candidates ranked below the top two are recorded by name and
free-signal rationale only; no papers are read for them at all.

## Predatory Journal Screen — conditional, not universal

- **Auto-pass** a journal indexed in Scopus at Q1–Q2 that the researcher or their group has
  already published in. Record a one-line reason for the auto-pass — the verdict is still written
  down, only the investigation is skipped
- **Run the full screen** (`references/predatory-journal-screen.md`) for any journal unfamiliar to
  the researcher — review-speed plausibility, editorial board verifiability, Scopus/WoS indexing
  cross-check
- Either way the verdict + reason is cached in that journal's `journal-library` entry — there is
  no separate predatory-screen cache file
- A ❌ Fail still excludes the journal outright; it is not merely down-ranked

## Then

- Reshape the per-journal fields into the two-row Journal Comparison Table (target + fallback) —
  a decision record documenting why this journal over that one, not a separate research pass
- Researcher confirms the target journal
- Confirmed journal is flagged for full Journal Profile construction in ARTi-writing. The 2–3
  papers read here **count toward** that skill's 5–8, and the light novelty threshold derived
  here is **extended there, not re-derived from zero**
- Only the **top two** candidates get a light analysis (2–3 papers each). Journals the researcher
  or their group has already published in at Scopus Q1–Q2 auto-pass the Predatory Journal Screen
  with a recorded reason; unfamiliar journals get the full screen. Per-journal light-analysis
  results are cached in `~/.arti/journal-library/` so a journal already targeted before doesn't
  need re-extraction — a separate cache from `arti-jfinder`'s own `journal_scope` table
  (aims-and-scope text only; no novelty/screening data). The final committed journal is handed off
  to the ARTi-writing skill for full Journal Profile construction, where its 2–3 papers count
  toward that skill's 5–8

## Light extraction from example papers (Stage 5 only)

- Scope and aims fit: ✅ / ⚠️ / ❌
- Article type published
- Novelty level evident in each paper (C/M/E estimate)
- Typical study design (techniques, sample type)
- Do NOT extract writing style or technical depth at this stage — that is done in ARTi-writing

**When to create:** After the Research Design is stable. Uses 2–3 papers for the top two
candidates only — enough to assess novelty threshold and scope fit, not a full style extraction
(that happens in ARTi-writing).
