# Stage 4 — PRISMA Flow, Matriks Sintesis, and Handoff: procedure

Full procedure for the closing stage. Read this when Stage 4 fires — see `SKILL.md`'s Stage 4 stub
for the trigger condition.

## PRISMA Flow Diagram — computed from `screening_stage` counts, not a late-stage input

- Run one `library list --screening-stage X --project PATH` call per stage value: `identified`,
  `title_abstract`, `eligible`, `included`, `excluded_title_abstract`, `excluded_eligibility`. The
  length of each `rows` array is that stage's PRISMA count — never ask the researcher for these
  numbers or reconstruct them from memory, they are queries against real screening history.
- "After deduplication" is `identified` minus whatever `library import-ris`/`library add` already
  rejected as duplicates during Stage 2 — read those totals back from Stage 2's own reporting, or
  re-derive by comparing raw search-hit totals (logged during Stage 2) against the `identified`
  count now.
- Feed these counts into the standard PRISMA 2020 flow shape (Identification → Screening →
  Eligibility → Included, with exclusion counts + top reasons at each screening gate — group
  `excluded_title_abstract`/`excluded_eligibility` rows by `exclusion_reason` text to get "top
  reasons").
- Render via **ARTi-figure**'s diagram lane: author a JSON spec (`figures/Fig_N.json`) with one
  node per PRISMA box and the counts filled in, render with `arti-render`, then run ARTi-figure's
  own verification loop (read the rendered PNG back, check legibility) before treating the figure
  as done. Register it in `figures/figure-register.md` as usual.

## Re-check prior reviews before handoff

- Re-run the Prior Review Check queries (`slr\prior-reviews.md`, same queries, newest year window)
  before the handoff is written: a review published since Stage 1 can change the Introduction's
  novelty claim. Add any new review to `arti-lit` as `prior_review`, update the verdict and the
  differentiating sentence, and log the new date and counts in the document.
- `prior_review` rows are outside the PRISMA counts above — do not add them to any stage total.

## Matriks Sintesis — build once every `included` row has a `summary`

- Confirm every `included` row (from the query above) has a non-null `summary` before building the
  matrix — an included paper without extraction is a Stage 3 gap, not a Stage 4 problem to work
  around.
- Populate `slr\synthesis-matrix.md` (`references/synthesis-matrix-template.md`): one row per
  included paper, one column per recurring theme, plus Contradictions and Underexplored Areas
  sections (same shape as `ARTi-idea`'s Gap Map, deliberately — a review's synthesis matrix and an
  empirical paper's gap map are the same kind of document).
- Fire the **three separate outputs** — do not stop after (a):
  - **(a) SLR Manuscript Blueprint** — theme rows become the Results/Discussion outline directly;
    fill `slr\manuscript-blueprint.md` (`references/slr-manuscript-blueprint-template.md`).
  - **(b) Idea Canvas gate** — for every gap noticed that looks like a future empirical study (not
    just "more review needed"), invoke `ARTi-idea`'s existing Idea Canvas step (Stage 3 there) —
    never score it here, never write directly to the Research Idea Bank. This keeps the Idea
    Bank's quality bar identical regardless of whether the gap was noticed during an SLR or a Gap
    Map.
  - **(c) Journal Target Sheet input** — feed the Theme Table + Contradictions into
    `journal-target-sheet-template.md`'s Free-Signal Ranking directly. This journal choice is
    topic-driven (which journals publish reviews on this subject), not routed through Idea
    Canvas's novelty scoring — a review paper's journal fit isn't a novelty question.

## Closing: SLR Handoff

- Once the PRISMA Flow Diagram, Matriks Sintesis (all three outputs fired), and Journal Target
  Sheet are all in place, write `slr\handoff.md` using `references/slr-handoff-template.md` — copy
  the decisions, point at the content, same "never transcribe" rule `ARTi-idea`'s own handoff
  documents.
- Run `project upsert` for this project's row (status "SLR complete / handed off") — phase-boundary
  cadence, not per-stage.
- Tell the researcher explicitly the handoff is ready, per the template's closing line, and that
  the next step is building the full Journal Profile in `ARTi-writing` from example review papers
  in the confirmed journal.
