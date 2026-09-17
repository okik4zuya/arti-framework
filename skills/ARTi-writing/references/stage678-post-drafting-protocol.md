# Stages 6–8 — post-drafting: Cover Letter, Rebuttal, Publication Growth Log

Full procedure for the three post-drafting stages. Merged into one file since each is a short,
self-contained trigger/output block — three separate files would cost three extra hops for no
savings. Read this when Stage 6, 7, or 8 fires — see `SKILL.md`'s stage stubs for trigger
conditions and output files.

---

## Stage 6: Cover Letter

Run once the manuscript is submission-ready — the latest Iteration Log entry shows no 🔴 Critical
items outstanding.

- Pull Journal Profile Block A (editor name if known, scope statement to address) and Block D (the
  novelty threshold this manuscript clears, stated as a fit claim, not restated as a C/M/E number)
- If ARTi-idea was used, pull the Idea Canvas's contribution statement via the handoff manifest
  rather than re-deriving a summary of the abstract
- Verify the letter argues fit, not summary: check that a specific sentence connects this
  manuscript to something this journal specifically publishes or has stated it wants
- Write to `submission\cover-letter_[journal-abbreviation].md`
- See `references/cover-letter-template.md` for the blank template

**Project index cadence:** once the researcher confirms the package was actually submitted to the
journal (not merely that the cover letter draft is done), run
`project upsert --stage "Submitted" --status "Under review"` (or the journal name if not already
set) for this project's row. Consider whether `--summary` needs updating too.

---

## Stage 7: Rebuttal / Response to Reviewers

Triggered when reviewer comments arrive after peer review — never speculatively before that.

- Open one entry per individual reviewer comment, not per reviewer and not per round as a whole
- Tag each entry with exactly one category: Technical / Methodological / Conceptual / Strategic
- As each comment is addressed, cross-link the entry to the Iteration Log entry that made the
  resolving manuscript change
- If a subsequent review round arrives, append new entries to the same document rather than
  starting a new one for the same journal submission
- Write to `submission\rebuttal_[journal-abbreviation]_round[N].md`
- See `references/rebuttal-template.md` for the blank template

---

## Stage 8: Publication Growth Log

Triggered by the researcher confirming acceptance — never speculatively before that. This is the
only stage that runs after the paper is done, and the one that closes the loop back to ARTi-idea.

- Walk the post-acceptance visibility checklist: DOI registered, ORCID linked, repository archiving
  done where the publisher allows it
- Ask directly: *"What did this paper's Limitations section leave on the table?"* — review the
  Manuscript's own Limitations paragraph, plus any Strategic-category comments from Reviewer
  Simulation or real reviewers that were deliberately deferred rather than resolved, for concrete
  follow-up directions
- Record the answer in `submission\growth-log.md`, and in the same turn run `idea-bank add` so it
  surfaces automatically the next time a Gap Map is started
- See `references/publication-growth-log-template.md` for the blank template
