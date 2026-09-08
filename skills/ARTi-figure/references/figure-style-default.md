---
name: figure-style-default
description: Shipped starting-point visual baseline for ARTi-figure diagrams — copied into ~/.arti/memory/figure-style.md on first install (missing-only), then owned and customized by the researcher from there
metadata:
  type: reference
---

Same pattern as `~/.arti/voice-profiles/`: one shared baseline reused across every paper project,
not re-invented per figure or per project. This file is the **generic seed** — installed once into
`~/.arti/memory/figure-style.md` if that file doesn't exist yet, then never touched again by the
installer. From that point on, `~/.arti/memory/figure-style.md` is the researcher's own living copy:
add named styles to it as real figures get approved, per the instructions there.

A paper-specific render still pulls dpi and print/column width from that paper's own
`writing/journal-profile_*.md` (Block A/B) at render/export time — those are per-journal
constraints, not part of the shared visual language, and don't get a second copy here.

## Defaults (fonts, weights, spacing)

| Property | Value |
|---|---|
| `fontFamily` | `Arial, Helvetica, sans-serif` |
| `fontSize` | 20 |
| `lineHeight` | 1.2 |
| `strokeWidth` | 2 |
| `padX` | 20 |
| `wrapPad` | 6 |

## Palette (named styles)

Only the two universal roles every box-and-arrow diagram needs are seeded here. Add
domain-specific styles (e.g. a pretest/posttest pair for an education-research design, or a
before/after pair for a synthesis route) to the researcher's own copy once a second figure reuses
them — don't expand this shipped default with any one project's vocabulary.

| Style name | Fill | Stroke | Text | Use |
|---|---|---|---|---|
| `dark` | `#4D4D4D` | `#000000` | `#FFFFFF` | Emphasis / summary boxes (opening condition, final analysis step) |
| `plain` | `#FFFFFF` | `#000000` | `#000000` | Ordinary process/description boxes |

Add a new named style to the researcher's own `~/.arti/memory/figure-style.md` (not here) once it's
used in a second figure — a style used only once stays local to that figure's own JSON.

## When starting a new figure spec

1. Copy the `defaults` block above verbatim unless the researcher asks for a different look.
2. Reuse an existing named style from the researcher's own palette table if the box's role matches
   one already defined; only add a new named style for a genuinely new role.
3. Check the target paper's `writing/journal-profile_*.md` Block A/B for a dpi or column-width
   constraint before the final export step; if that block says "not confirmed," flag it rather
   than guessing a number.

## Change log
- 2026-09-06 — Created as the shipped default, split off from a researcher's own populated
  `figure-style.md` (which had grown a `pretest`/`posttest` pair specific to one education-research
  project). Trimmed to the two universal styles so a new install doesn't inherit one project's
  domain vocabulary.
