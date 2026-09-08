# Research Design — print template

This is **not** a duplicate of the Research Design's field structure — that lives inline in
`SKILL.md` under "### 4. Research Design" (Research Objective, Hypotheses, Experimental Design,
Feasibility Flags, Novelty-Experiment Alignment), same as every other Core Document in this skill.
This file documents only the print-specific requirements, mirroring the role
`~/.arti/skills/ARTi-writing/references/completion-plan-template.md` plays for the Completion Plan.

## Output

`idea\research-design.md` (source of truth) rendered to `idea\research-design.pdf` via the shared
Markdown→A4-PDF pipeline documented in `~/.arti/tools/arti-pdf/README.md`. Reformat the Core Document's
field structure into compact print-friendly Markdown sections/tables — same style as
`completion-plan.md` — before rendering: Research Objective, Hypotheses, Experimental Design
(Materials/Samples, Synthesis/Preparation Protocol, Characterization Plan table, Analysis Plan,
Controls, Timeline), Feasibility Flags, Novelty-Experiment Alignment.

## When to render

Once feasibility flags are resolved and the design is confirmed with the researcher — this is the
closing step of Stage 4, not something re-rendered on every edit. It exists to be **frozen and
printed early**, before data collection starts, so the researcher has a stable reference at hand
during execution.

## Frozen-snapshot semantics

Same relationship the Completion Plan already has to its own sources: hand-maintained, not
auto-generated. If the researcher's actual `idea\experiment-blueprint.md`-equivalent content
changes after printing (a scope revision mid-study), `research-design.md`/`.pdf` needs a manual
re-sync and re-render — it does not regenerate automatically. Re-render only if the design
genuinely changes before data collection starts; this is a stop-scope-drift artifact, not a living
document to keep in sync on every session.

## Render command

```
python ~/.arti/tools/arti-pdf/render.py --md idea\research-design.md --out-dir idea
```

## Change log
Keep this template's own history to a one-line-per-date list if it is ever revised; do not
document individual project designs here — those live in each project's own
`idea\research-design.md`.
