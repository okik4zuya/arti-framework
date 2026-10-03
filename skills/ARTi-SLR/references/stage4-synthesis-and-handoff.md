# Stage 4 — PRISMA Flow, Matriks Sintesis, and Handoff: procedure

Full procedure for the closing stage. Read this when Stage 4 fires — see `SKILL.md`'s Stage 4 stub
for the trigger condition.

## PRISMA Flow Diagram — funnel log reconciled with `arti-lit`

`arti-lit` is a reference store, not the source of truth for PRISMA. The numbers come from
`slr\prisma-counts.md` (`references/prisma-counts-template.md`), the funnel log kept during Stage 2.

- Run one `library list --screening-stage X --project PATH` call per stage value: `identified`,
  `title_abstract`, `eligible`, `included`, `excluded_title_abstract`, `excluded_eligibility`,
  plus `prior_review` and `outside_flow` for the "Outside the flow" section. The length of each
  `rows` array is the `arti-lit` side of the reconciliation — never ask the researcher for these
  numbers or reconstruct them from memory.
- **Reconcile per path × stage** (path = the `search_source` prefix: `DB:`, `OTHER:`, `OUTSIDE:`).
  Row counts per path must equal the funnel log. Show any difference to the researcher; do not
  settle it silently. A row with no path prefix is "unclassified": the researcher decides A / B / C
  / D (see Stage 2) before the counts are locked.
- "After deduplication" and import duplicates come from the funnel log's import table, not from
  re-deriving `identified` minus something.
- Feed these counts into the standard PRISMA 2020 flow shape (Identification → Screening →
  Eligibility → Included, with the "other methods" arm, and exclusion counts + reasons at each
  gate — group `excluded_*` rows by the code that starts `exclusion_reason`: E1, E2, ..., DUP). A
  Protocol deviation (path D) is flagged in the box, not folded into the counts.
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
- Fire up to **three outputs**. (a) and (c) are required; (b) only when the researcher plans a
  follow-up empirical study:
  - **(a) SLR Manuscript Blueprint** — theme rows become the Results/Discussion outline directly;
    fill `slr\manuscript-blueprint.md` (`references/slr-manuscript-blueprint-template.md`).
  - **(b) Idea Canvas gate (optional)** — the gate exists for follow-up studies and the Idea Bank,
    not for the review itself. Ask one question first: "is there a planned follow-up study?" If
    not, mark (b) "N/A, not pursued" and move on. If yes, for every gap that looks like a future
    empirical study (not just "more review needed"), invoke `ARTi-idea`'s existing Idea Canvas
    step (Stage 3 there) — never score it here, never write directly to the Research Idea Bank.
    - The synthesis matrix (Contradictions + Underexplored) serves as the Gap Map; ARTi-idea is
      not asked to build a new one.
    - A claim of the form "nobody has done X" holds only for the selected corpus. Tag it
      `[NEEDS CHECK]` and run a targeted search before it becomes a novelty claim in the
      manuscript.
    - Before writing a canvas, check the Idea Bank and `~/.arti/memory/project-index.md` (the
      researcher's other projects) for overlap.
  - **(c) Journal Target Sheet input** — feed the Theme Table + Contradictions into
    `journal-target-sheet-template.md`'s Free-Signal Ranking directly. This journal choice is
    topic-driven (which journals publish reviews on this subject), not routed through Idea
    Canvas's novelty scoring — a review paper's journal fit isn't a novelty question.

## Closing: SLR Handoff

- Once the PRISMA Flow Diagram, Matriks Sintesis ((a) and (c) done; (b) done or N/A), and Journal
  Target Sheet are all in place, write `slr\handoff.md` using `references/slr-handoff-template.md` — copy
  the decisions, point at the content, same "never transcribe" rule `ARTi-idea`'s own handoff
  documents.
- Run `project upsert` for this project's row (status "SLR complete / handed off") — phase-boundary
  cadence, not per-stage.
- Tell the researcher explicitly the handoff is ready, per the template's closing line, and that
  the next step is building the full Journal Profile in `ARTi-writing` from example review papers
  in the confirmed journal.
