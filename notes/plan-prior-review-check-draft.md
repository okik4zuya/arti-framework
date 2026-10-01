# Plan: Prior-Review (novelty) check for the SnO2 SLR and for ARTi-SLR

## Context

The SnO2/CO2-photoreduction SLR is at Stage 2 (35 papers passed Gate 1, 23 fulltexts retrieved, 12 still
blocked). The protocol was locked on 2026-09-27 without checking whether a review on this topic already exists.
The workflow diagram (`arti-slr-workflow.png`) and `ARTi-SLR` skill confirm the gap is structural: "Idea Canvas
(+Novelty)" only scores future empirical studies (Key Principle 9), and Blueprint paragraph 2 ("why a review is
needed now") has no upstream step producing its content. Two reviews already sit in the corpus (pinto-2022,
lu-2014) but were excluded at Gate 1 and never used to map the gap.

Goal: (A) run the check for this project now, before Gate 2; (B) add it to the skill so future SLRs get it by default.

## Part A — Run the prior-review check for this project

**Where it sits:** between locked PICO(C)/RQ and the (already locked) Protocol. It runs late here, so its verdict
is treated as able to reopen scope, with any change logged in `slr/protocol.md`'s Change log (not silently edited).

**Steps**
1. Seed from the corpus: pull pinto-2022 and lu-2014 from `literature/arti-lit.db` (read-only `library`
   queries via the vendored `~/.arti/python/python.exe` + `~/.arti/tools/arti-lit/cli.py`) and read their
   abstracts/fulltext if present.
2. Search for existing reviews with narrow, phrase-scoped queries (one per angle, per working-preferences):
   - SnO2 (tin oxide) + "CO2 photoreduction" / "photocatalytic CO2 reduction" + review
   - SnO2 modification strategies (doping, heterojunction, oxygen vacancy) + review
   - SnO2 photocatalysis general reviews that include a CO2 section
   - Tools: `mcp__scite__search_literature` and `mcp__arti-ref-search-mcp__search_openalex_works` (review
     doc-type filter where available). Check `editorialNotices` for retractions before citing.
   - Scopus is paywalled and the researcher's chosen database: give the researcher one bare, copy-ready
     Scopus query with `DOCTYPE(re)` to run and export, rather than assuming access.
3. Optionally run `ARTi-crosscite` only if two literature clusters need a "never cross-cited" claim; not needed
   for the basic check.
4. For every review found, record: year, systematic/PRISMA or narrative, SnO2 vs broad-oxide scope, CO2
   reduction coverage, which modification strategies it covers, pristine-baseline coverage, date window.
5. Write the verdict with a recommended default (per working-preferences): **clear** (no close review),
   **partial overlap** (state the differentiator, e.g. SnO2-specific, 2015-2026 window, modification-vs-pristine
   comparison, PRISMA-systematic), or **near-duplicate** (recommend reframing RQ/PICO(C); flag as reopening a
   "confirmed" decision).
6. Output the differentiator as 2-3 sentences ready for Blueprint Introduction paragraph 2.

**Files written (only after plan approval)**
- New: `slr/prior-reviews.md` (table of reviews + verdict + differentiator)
- New: `memory/memories/prior-review-check.md` (topic file with frontmatter + Change log; timestamps from a real
  `date` call)
- Update: `memory/MEMORY.md` (one pointer line), `memory/todo-list.md` (add item; also fix the stale fulltext
  line to reflect 23/35 retrieved and the 12 blocked in `.side-note.md`), `memory/status.md` (overwrite Current
  state block, 2-4 sentences, `[[prior-review-check]]` link)
- Only if the verdict changes scope: `slr/protocol.md` + `slr/judul-rq-pico.md` with a Change log entry

**Sequencing:** run Part A first; the researcher can download the 12 blocked fulltexts in parallel. Gate 2 on the
23 available papers starts after the verdict (no criteria change expected unless verdict = near-duplicate).

## Part B — Add the step to the ARTi-SLR skill

All edits go in `~/.arti/skills/ARTi-SLR/` (never `~/.claude/skills/` symlink). Proposed step name:
**"Cek Review Terdahulu"** (Prior-Review Check), Stage 1 Part C.

1. `references/stage1-question-and-protocol.md` — add **Part C — Prior-Review Check** between Part A and Part B
   (trigger: Judul + RQ + PICO(C) confirmed; runs before Protocol locks). Contents: the Steps 1-6 above
   generalized (corpus seed optional, narrow phrase-scoped queries, Scopus `DOCTYPE(re)` delegated to
   researcher, verdict taxonomy, differentiator sentence). Include the lesson from this project: a late check
   can only reopen scope, so do it before Protocol.
2. New `references/prior-review-check-template.md` — table (review, year, type, scope, CO2 coverage,
   strategies covered, window) + verdict + differentiator + Change log; mirrors the style of
   `judul-rq-pico-template.md`.
3. `SKILL.md` — (a) Core Documents: add a 6th document `slr\prior-reviews.md` (and update "five core
   documents" wording); (b) Workflow Stages diagram: insert `[M] Cek Review Terdahulu` between Judul+RQ+PICO(C)
   and Protokol; (c) Stage 1 stub: mention Part C and the new output; (d) Key Principles: add "A review's own
   novelty is a prior-review check, run before Protocol" and amend Principle 9 so it's clear Idea Canvas
   novelty covers future studies only, not the review itself; (e) reword the "Not this skill" note to
   cross-reference this step.
4. `references/slr-manuscript-blueprint-template.md` — Introduction paragraph 2: point to
   `slr/prior-reviews.md` as its source.
5. `references/stage4-synthesis-and-handoff.md` and `references/slr-handoff-template.md` — add a short
   "re-run the prior-review search before submission" note (new reviews may have appeared during the project)
   and a pointer to `prior-reviews.md` in the handoff.
6. `ARTi-idea` Gap Map is not touched (SLR path stays separate per the skill's own scope rule).

**Diagram:** `arti-slr-workflow.png` is the researcher's own file; I will not edit it. Hand-over spec for
draw.io: one white (model-made) box "Cek review terdahulu" between "RQ + PICO(C)" and "Protokol", arrow in/out
vertically, optional arrow from Reference Database; no new yellow (user-supplied) box needed. Note the skill's
own `figures/arti-slr-workflow.png` is a simplified copy, so it needs the same one-box addition by the
researcher.

## Verification

- Part A: every cited review is retrieved via scite/OpenAlex (never from memory) with DOI; `prior-reviews.md`
  counts match the search log; memory files satisfy CLAUDE.md rules (3 flat files, one-line todo items, status
  block overwritten not stacked, `date`-sourced timestamps).
- Part B: grep `~/.arti/skills/ARTi-SLR` for "prior-review"/"Cek Review Terdahulu" to confirm all six touch
  points are consistent; confirm the skill's stage/doc counts in prose match the new totals; confirm no edit
  landed under `~/.claude/skills/`.
- Dry run: read the updated Stage 1 flow top to bottom and check Part C reads correctly as a step between A and B.

## Out of scope

No git commits. No edits to the PNG diagrams. No change to Stage 2 screening results.
