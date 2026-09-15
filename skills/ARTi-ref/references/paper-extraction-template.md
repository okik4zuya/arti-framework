# Paper Extraction Template

Blank output shape for a single-paper extraction, produced directly by Claude when the paper's
text or PDF is available in the conversation (attached file, `arti-pdf-ingest` fulltext Markdown,
or pasted text). Same field set as `notebooklm-extraction-prompt.md` — that file wraps this exact
structure in an instruction block meant to be copy-pasted into NotebookLM instead, for when the
researcher wants to run the extraction there rather than have Claude do it in-session. **Keep the
two in sync** — if a field is added or reworded here, mirror it there and vice versa.

Terse bullets, no prose padding — this output is meant to be re-read by another LLM/Claude
session later, so density matters more than readability. Anything inferred or uncertain rather
than read directly off the page is tagged `[SUGGESTED — USER MUST VERIFY]`.

---

```
## Summary
[One paragraph, plain language: what this paper did and found, and why it matters.]

## Article Type & Field
- Type: [Original research / Review / Meta-analysis / other]
- Field / sub-field: [discipline and narrower sub-area]

## Research Question / Objective
[What the paper is actually trying to answer or test.]

## Authors' Stated Motivation
[Why the authors say this study was needed — their framing, not your assessment.]

## Methods Summary
- Study design:
- Materials / system studied:
- Key techniques / instruments:
- Sample size / scale:
- Notable parameters:

## Key Findings
- [Finding 1 — with number/effect size/direction if reported]
- [Finding 2]

## Authors' Stated Limitations & Unresolved Gaps
- [What the authors themselves flag as missing or unresolved]

## Contradictions / Agreements with Prior Work
- [⚠️ CONTRADICTION: This paper vs. Author, Year — what conflicts and how]
- [AGREEMENT: This paper vs. Author, Year — what confirms prior work]

## Novelty Signals (raw, unscored)
- [What the authors claim is new — do not assign a C/M/E score here; that happens on the Idea
  Canvas, across papers]

## Future Work Suggested by Authors
- [Explicit future-work statements from the paper]

## Citable Claims
- [LIT: Author, Year] — [claim, paraphrased — never pasted verbatim]

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

## Where each field goes

- `REFERENCE ENTRY` → Gap Map's `## Reference List` (`gap-map-template.md`), verbatim.
- `Authors' Stated Limitations & Unresolved Gaps` → the same block's "Gaps or limitations noted
  by authors" line.
- `Contradictions / Agreements` → Gap Map's `## Contradictions & Debates` (same
  `⚠️ CONTRADICTION: A, Year vs. B, Year` tag format).
- `Citable Claims` → Scratchbook (`scratchbook-template.md`), already tagged `[LIT: Author, Year]`.
- `Novelty Signals` → raw input for Idea Canvas scoring (`novelty-scoring-guide.md`); never a
  score itself.
- The whole extraction, in full → saved as that paper's `--summary` in `arti-lit` (see
  `~/.arti/tools/arti-lit/README.md`), keyed `author-year[a|b]`, so it's retrievable later via
  `library get` without re-reading the PDF.

## Change log
- 2026-09-13 — created, split out of `notebooklm-extraction-prompt.md` so Claude has a bare
  template to fill directly, separate from the NotebookLM-facing instruction wrapper.
