# Stage 5 — Iteration Log: protocol

Process wrapping for Iteration Log entries. For the full entry structure (Sections 1–6, plus the
optional Section 4b Reviewer Simulation subsection) and scoring guidance, read
`references/iteration-log-template.md` directly — do not re-derive that structure from this file;
it is not restated here to avoid the two ever drifting apart.

## Trigger rule — IMPORTANT

Claude must NEVER create an Iteration Log entry automatically.
- Claude creates an Iteration Log entry ONLY when the user explicitly requests it (e.g., "evaluate my draft", "create an iteration log entry", "run an evaluation")
- At the end of each drafting or revision session, Claude must ask: *"Would you like me to create an Iteration Log entry for this draft?"*
- If the user says no, proceed without creating one
- Never assume an evaluation is wanted — always ask first

When an entry is requested, Claude must read `iteration-log-template.md` for the full report
structure and scoring guidance, then produce a structured entry.

## Feedback source (recorded at the top of every entry)

State where the input for this iteration came from: self-review, the previous Iteration Log entry,
supervisor, co-author, peer reviewer, or Reviewer Simulation. External feedback enters the loop
through this field — an entry can be opened to record a supervisor's, reviewer's, or simulated
review's comments even when no fresh evaluation was run.

## Evaluation precedes revision

Sections 1–4 (from the template) are completed before any revision begins, and Section 5 is only
filled once the revisions are actually made. Merging the two logs into one entry does not merge
the two acts.

## Block D re-verify (touch point 3 of 4 — see `SKILL.md`'s Key Principles table for the full list)

Section 3b of the template requires scoring the current draft's C/M/E against Block D's threshold
at every entry, not just Draft 1, and updating Block D's "Your Manuscript's Novelty Fit" table with
the result. If any dimension is ❌ Below threshold, this automatically becomes a 🔴 Critical item
in Section 4.

## Reviewer Simulation

Optional, run only after the current entry shows no 🔴 Critical items — see Core Documents #6
"Reviewer Simulation" for what it is and why it exists, and the template's Section 4b for the
output structure. Ask the researcher before running it; never run it automatically or as a
substitute for Sections 1–3b.
