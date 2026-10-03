# SLR Handoff — [topic]

**Date:** [YYYY-MM-DD]
**Status:** [in progress / ready for ARTi-writing]

> Same convention as ARTi-idea's `idea\handoff.md` — copy decisions, point at content, never
> transcribe. This document sits in the same project folder as the source documents below and
> is read directly by ARTi-writing at handoff; a transcribed copy goes stale the moment any source
> is edited.

**Final Judul + RQ + PICO(C):** [title] — [RQ] — P:[ ] I:[ ] C:[ ] O:[ ] C:[ ]

**Protocol summary:** [N] databases searched ([list]); [N] inclusion criteria, [N] exclusion
criteria (see `slr\protocol.md`)

**PRISMA counts per stage:**

| Stage | Count | Top exclusion reasons (if applicable) |
|---|---|---|
| Identified | [n] | — |
| After deduplication | [n] | — |
| Title/abstract screened | [n] | [reason 1 (n), reason 2 (n)] |
| Eligibility assessed | [n] | [reason 1 (n), reason 2 (n)] |
| Included | [n] | — |

**PRISMA Flow Diagram:** [pointer to `figures/Fig_N_prisma-flow.png`/`.drawio`]

**Prior Review Check:** verdict [clear / partial overlap / near-duplicate], last re-run
[YYYY-MM-DD] — see `slr\prior-reviews.md`

**Matriks Sintesis:** [pointer to `slr\synthesis-matrix.md`]

**SLR Manuscript Blueprint:** [pointer to `slr\manuscript-blueprint.md`]

**Included-paper key list:** [author-year, author-year, ... — full set from
`library list --screening-stage included`]

**Journal Target Sheet decision:** [confirmed journal] (fallback: [journal]) — see
`slr\journal-target-sheet.md`

**Open flags:**
- Scopus `DOCTYPE(re)` re-run: [pending / YYYY-MM-DD]. The Introduction says "to our knowledge"
  until this flag is closed (see `slr\prior-reviews.md`).

**Open notes:** [unresolved contradictions, low-quality papers kept with justification, dangling
`[DATA NEEDED]`/`[NEEDS MORE LITERATURE]` flags, or "none"]

---

## Where the content lives

| Source file | Feeds |
|---|---|
| `slr\judul-rq-pico.md` | Manuscript title, Introduction RQ statement |
| `slr\prior-reviews.md` | Introduction paragraph 2 (novelty vs. existing reviews) |
| `slr\protocol.md` | Methods section (eligibility, information sources, search strategy) |
| `slr\prisma-counts.md` (reconciled with `arti-lit.db`) | PRISMA Flow Diagram counts |
| `slr\synthesis-matrix.md` | Results/Discussion section content; Idea Canvas gap routing (optional); Journal Target Sheet input |
| `slr\manuscript-blueprint.md` | ARTi-writing's Manuscript Blueprint (paragraph-level shape) |
| `slr\journal-target-sheet.md` | Journal Profile Block A + D threshold |

**Project index cadence:** run `project upsert` for this project's row at the phase boundary —
status "SLR complete / handed off" — same cadence ARTi-idea's own handoff uses, not per-stage.

Claude must explicitly tell the researcher when the handoff is ready: *"Your systematic review's
protocol was followed, screening is complete with [n] papers included, and your target journal is
selected. `slr\handoff.md` is ready — you are ready to begin the ARTi-writing workflow. Start by
building the full Journal Profile from example review papers from [Journal Name]."*
