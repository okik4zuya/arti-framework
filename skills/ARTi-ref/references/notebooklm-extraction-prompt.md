# NotebookLM Paper-Extraction Prompt

A copy-paste-ready prompt for NotebookLM (or any LLM with the paper's PDF/text loaded) that
extracts everything ARTi-idea and ARTi-writing need from one research or review paper, in a format
that pastes straight into a Gap Map, Scratchbook, or Reference List without reformatting.

Feed it one paper at a time. Paste the block below into NotebookLM's chat alongside the source
PDF, run it, then copy the output into the Gap Map / Scratchbook / literature library as needed.

When the paper's text or PDF is available directly in the conversation instead, Claude runs this
same extraction in-session against `references/paper-extraction-template.md` (identical field
set, without the NotebookLM instruction wrapper) rather than asking the researcher to round-trip
through NotebookLM — see that file and `SKILL.md`'s "Paper Extraction" section for the trigger and
handling. **Keep the two field sets in sync.**

---

## The prompt

```
You are extracting structured notes from one research or review paper for a systematic literature
review. Read the attached paper and produce output in exactly the format below — terse bullets, no
prose padding, no restating the section headers as sentences. This output will be re-read by
another LLM later, so density matters more than readability.

If you are inferring or uncertain about anything (a value not explicitly stated, a category you
had to judge rather than read off the page), mark that item `[SUGGESTED — USER MUST VERIFY]`
instead of stating it as fact. Never silently guess.

---

## Summary
[One paragraph, plain language: what this paper did and found, and why it matters. This is the
first thing a reader sees — make it stand alone.]

## Article Type & Field
- Type: [Original research / Review / Meta-analysis / other]
- Field / sub-field: [discipline and narrower sub-area]

## Research Question / Objective
[What the paper is actually trying to answer or test — the hypothesis or objective, stated as
precisely as the paper allows.]

## Authors' Stated Motivation
[Why the authors say this study was needed — their framing of the gap, in their own logic, not
your assessment of it. Distinct from "Limitations" below — this is motivation stated *before* the
work, not gaps found *after* it.]

## Methods Summary
- Study design: [experimental / computational / observational / etc.]
- Materials / system studied: [what was used or examined]
- Key techniques / instruments: [named methods, with enough technical detail that a specialist
  reader would recognize the specific protocol — do not flatten to a generic label]
- Sample size / scale: [n, replicates, dataset size, etc. — whatever the field's equivalent is]
- Notable parameters: [conditions, ranges, controls worth carrying forward]

## Key Findings
- [Finding 1 — include the number/effect size/direction if the paper reports one]
- [Finding 2]
- [Finding 3 — add more as needed]

## Authors' Stated Limitations & Unresolved Gaps
- [What the authors themselves say is missing, unresolved, or a limitation of this study]

## Contradictions / Agreements with Prior Work
- [⚠️ CONTRADICTION: This paper vs. Author, Year — what conflicts and how]
- [AGREEMENT: This paper vs. Author, Year — what confirms prior work]
(Omit either line type if the paper does not make that kind of comparison. Reviews should have
more of these than original-research papers.)

## Novelty Signals (raw, unscored)
[What the authors themselves claim is new — new method, new system studied, first-reported
result, confirms vs. contradicts prior consensus. Report their claim, not a C/M/E score — scoring
happens later, across papers, elsewhere.]
- [Signal 1]
- [Signal 2]

## Future Work Suggested by Authors
- [Explicit future-work statements from the paper — not your own suggestions]

## Citable Claims
[Short, paraphrased (never verbatim-quoted) statements ready to drop into a scratchbook, each
tagged with this paper's citation key.]
- [LIT: Author, Year] — [claim, paraphrased]
- [LIT: Author, Year] — [claim, paraphrased]

---
REFERENCE ENTRY

Authors: [Last, F. et al.]
Title: [Full title]
Journal: [Journal name]
Year: [YYYY]
DOI: [if available]

Key findings relevant to this gap map:
- [Finding 1]
- [Finding 2]

Gaps or limitations noted by authors:
- [What the authors themselves say is missing or unresolved]
---
```

---

## Notes on using the output

- **Gap Map** (`gap-map-template.md`): the `REFERENCE ENTRY` block pastes directly into that
  file's Reference List. "Authors' Stated Limitations" feeds "Gaps or limitations noted by
  authors" in the same block. "Contradictions / Agreements" feeds the Gap Map's
  `## Contradictions & Debates` section verbatim (same `⚠️ CONTRADICTION: A, Year vs. B, Year`
  tag format).
- **Scratchbook** (`scratchbook-template.md`): "Citable Claims" entries paste directly under
  whichever section they support, already tagged `[LIT: Author, Year]` in the Scratchbook's own
  convention.
- **Novelty scoring** (`novelty-scoring-guide.md`): "Novelty Signals" is raw input for the C/M/E
  rubric — ARTi-idea applies the scoring across multiple papers; this prompt does not score.
- Anything tagged `[SUGGESTED — USER MUST VERIFY]` in the output must be checked against the paper
  before it is trusted in a Gap Map or Scratchbook entry.

## Change log
- 2026-09-13 — created.
- 2026-09-13 — wired into `SKILL.md`'s "Paper Extraction" section; split the blank field shape out
  to `paper-extraction-template.md` for Claude's own in-session use.
