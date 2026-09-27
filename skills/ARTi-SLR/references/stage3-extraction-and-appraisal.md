# Stage 3 — Extraction and Quality Appraisal: procedure

Full procedure for turning an `eligible` row into an `included` one. Read this when Stage 3 fires —
see `SKILL.md`'s Stage 3 stub for the trigger condition.

## Extraction

- For each `eligible` row, extract the structured fields the review needs to synthesize: key
  findings relevant to each PICO(C) element, study design, sample/context, and any
  limitation the authors themselves note.
- This reuses the same mechanics as `ARTi-ref`'s Paper Extraction (on-demand) — "summarize paper
  [title]" against a paper already tracked in `arti-lit` — rather than a new extraction format.
  Save the extraction as that row's `summary` field: `library update --key KEY --summary "..."
  --project PATH`.
- No new field for structured data extraction — `sources.summary` (free text) is the extraction's
  home, same as every other `arti-lit` project. Do not invent a parallel extraction document.

## Quality Appraisal — folded into Summary, no new field

- Apply the checklist/rubric the Protocol named (`slr\protocol.md`'s Quality Appraisal Approach
  section) to this paper, and append the appraisal's outcome to the same `summary` field written
  above — a short block (e.g. `Quality appraisal: [checklist] — [pass/concerns/fail] — [reason]`)
  rather than a separate write.
- A paper kept despite quality concerns must have its justification recorded in this same summary
  block — this becomes one of the SLR Handoff's "open notes" at Stage 4 if the concern is
  unresolved.

## Closing the gate

- Once extraction + appraisal are both recorded in `summary`, mark the row included: `library
  update --key KEY --screening-stage included --project PATH`.
- A row never sits at `eligible` waiting — extraction and the stage-4 transition to `included`
  happen in the same pass, per paper, so the count of `eligible` rows at any moment reflects only
  papers actively being worked on, not a backlog.

## Reporting

After each paper (or small batch), report: which paper, key findings summary (one line), quality
appraisal outcome, and updated `included` count — running total, same as Stage 2's reporting
discipline.
