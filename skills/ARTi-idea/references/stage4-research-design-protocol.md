# Stage 4 — Research Design: protocol

Full procedure for building the Research Design (Core Document #4). Read this when Stage 4 fires
— see `SKILL.md`'s Stage 4 stub for the trigger condition, schema, and output file.

## Purpose

The Research Design is the guide that locks the study *before* data collection begins —
finalizing hypotheses, methods, and analysis plan early is what keeps major changes and
unpredictable problems from surfacing mid-study. Every proposed technique and method is
cross-referenced against the Researcher Profile. Unfeasible elements are flagged and alternatives
proposed.

## When to create

After one idea is confirmed on the Idea Canvas. This is the most collaborative stage — Claude
proposes, researcher confirms or adjusts based on actual lab knowledge.

## Procedure

- Claude proposes the experiment design based on the confirmed idea
- Every technique is checked against the Researcher Profile
- Feasibility flags are assigned: 🔴 🟡 🟢
- 🔴 flags must be resolved (via collaboration, alternative technique, or scope change) before
  the design is finalized
- Claude must confirm that the experiment as designed actually produces the data needed to
  support the novelty claim — if not, revise the design or revise the score

## Closing step — print it

Once feasibility flags are resolved and the design is confirmed, render `research-design.md` →
`research-design.pdf` (A4, via the shared pipeline documented in `~/.arti/tools/arti-pdf/README.md`)
as the frozen reference the researcher keeps at hand during execution. See
`references/research-design-template.md` for the print-specific requirements.
