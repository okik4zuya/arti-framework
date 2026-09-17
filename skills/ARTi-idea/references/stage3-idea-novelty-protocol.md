# Stage 3 — Idea generation & novelty scoring: protocol

Full procedure for Idea Canvas generation, scoring, and the two side effects it can trigger
(Research Idea Bank auto-park, Positioning Line). Read this when Stage 3 fires — see `SKILL.md`'s
Stage 3 stub for the trigger condition and output file. Scoring itself follows the inline Novelty
Scoring System (Core Documents section) and `references/novelty-scoring-guide.md` for detailed
examples.

## Procedure

- Claude generates 3–5 candidate ideas directly from the Gap Map
- Researcher may add their own ideas
- Every idea is scored C/M/E immediately — no idea proceeds without a score
- Ceiling check is applied to every idea before a decision
- Ideas that fail the sweet spot rule are redesigned, not discarded
- Claude must explain *why* each score was assigned — not just the number

## Decision rules

- Composite = Incremental → ❌ Reject (or major redesign required)
- Composite = Meaningful and within ceiling → ✅ Viable candidate
- Composite = Significant and within ceiling → ✅ Strong candidate, advance
- Any dimension exceeds ceiling → ⚠️ Redesign required before advancing

When multiple ideas are viable, rank them and ask the researcher to select one before proceeding
to Stage 4.

## Research Idea Bank auto-park (side effect)

Any idea that clears Meaningful-or-above but is not the one selected to advance is automatically
recorded via `idea-bank add` — never silently discarded. Pass idea text, C/M/E score, composite
label, date, source project, and reason parked (lost selection vs. explicitly deferred by the
researcher); the command regenerates `~/.arti/memory/research-idea-bank.md` itself.

## Positioning Line trigger (side effect, one-directional into Stage 1's document)

The first time a Research Idea Bank entry is ever written (i.e., the first time the paragraph
above fires for this researcher), Claude also writes a one-sentence "Positioning Line" into
`~/.arti/memory/researcher-profile.md` (Stage 1's document), capturing the researcher's standing
thematic axis from that entry plus the rest of the Researcher Profile. This only happens once
unless the researcher asks to revise it. Stage 1 never triggers this write — it is one-directional,
fired only from here.
