# Review Protocol

**Date Created:** [YYYY-MM-DD]
**Last Updated:** [YYYY-MM-DD]
**Locked before search begins:** ✅ / ❌ — see note below

> Registered a priori, before any database search runs (Kitchenham's *plan* phase). Changing the
> protocol after search has started is not forbidden but must be logged in the Change log below
> with a reason — silent revision defeats the point of pre-registration.

---

## Databases to Search

> The full target list, fixed before Stage 2's search loop starts. Stage 2 repeats the search
> **once per database listed here** — this list is what that loop iterates over.

| # | Database | Access via | Notes |
|---|---|---|---|
| 1 | [e.g. Scopus] | [institutional login / open] | |
| 2 | [e.g. Web of Science] | | |
| 3 | [e.g. IEEE Xplore] | | |

---

## Inclusion Criteria

- [Criterion 1 — e.g. peer-reviewed original research or review article]
- [Criterion 2 — e.g. published [YYYY]–present]
- [Criterion 3 — e.g. addresses [P] in the context of [I]]

## Exclusion Criteria

- [Criterion 1 — e.g. non-English, no translation available]
- [Criterion 2 — e.g. conference abstract only, no full text]
- [Criterion 3 — e.g. does not report [O]]

> Every screening reject in Stage 2 must cite one of these criteria (or a close paraphrase) as its
> `exclusion_reason` — a reason that doesn't map back to a listed criterion is a signal the
> criteria list itself is incomplete, not that the reject was wrong.

---

## Search String Construction

**Core terms (from PICO(C)):**
| PICO(C) element | Terms |
|---|---|
| P | [term1 OR term2 OR ...] |
| I | [sub-strategy A terms] / [sub-strategy B terms] / ... — see note below |
| O | ["exact phrase 1" OR "exact phrase 2" OR ...] |

> If the Intervention decomposes into multiple distinct sub-strategies (e.g. doping,
> heterostructure, defect engineering), **do not OR them into one combined string** — that lets a
> paper match on any single sub-strategy and inflates the hit count well past what's screenable.
> Split into **one query per sub-strategy angle** instead (5–8 is typical), each combining the same
> P and O terms with just that one sub-strategy's I-terms. Prefer exact multi-word phrases over bare
> generic words for O (`"photocatalytic CO2 reduction"`, not `"reduction"`) — a bare word matches
> enormous unrelated literature.

**Per-angle queries (adapt syntax per database, include the database's explicit field-scope
function — e.g. Scopus's `TITLE-ABS-KEY(...)` — never omit it):**

| # | Angle (I sub-strategy) | Query | Hit count | Notes |
|---|---|---|---|---|
| 1 | [e.g. doping] | `TITLE-ABS-KEY(([P terms]) AND ([O terms]) AND ([angle-1 I terms]))` | | Target: low hundreds or fewer. If thousands+, narrow O; if single digits, widen O with a few alternate phrasings and re-test before concluding the niche is genuinely small. |
| 2 | [e.g. heterojunction] | | | |
| 3 | [e.g. defect engineering] | | | |

> Log each query's actual hit count in this table before moving to the next — a count wildly off
> from the target range is a signal to revise the query, not a place to just note it and continue.

---

## Quality Appraisal Approach

[Which checklist/rubric will be applied per included paper — e.g. a study-design-appropriate
checklist (CASP, MMAT, or a field-specific rubric). Folded into each source's `summary` field
during Stage 3 extraction — no separate quality-appraisal document.]

---

## Change log

> Only needed if the protocol is revised after search has started.

- [YYYY-MM-DD] — [what changed and why]
