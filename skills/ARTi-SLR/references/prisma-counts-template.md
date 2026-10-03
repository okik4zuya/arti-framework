# PRISMA Counts

**Date Created:** [YYYY-MM-DD]
**Last Updated:** [YYYY-MM-DD]
**Status:** [open / 🔒 LOCKED YYYY-MM-DD (reason). Reopen only by logging a Protocol change.]
**Source:** funnel log below (written during Stage 2), reconciled against `library list
--screening-stage X` queries on `literature/arti-lit.db` on [YYYY-MM-DD].

> The source of truth for PRISMA numbers. `arti-lit` stores per-record decisions; this file stores
> the funnel as it was recorded. Stage 4 reconciles the two and shows any difference to the
> researcher instead of resolving it silently.

---

## Import log (path A, database searches)

| Date | Database | Angle | Raw hits | Newly imported | Duplicates rejected at import |
|---|---|---|---|---|---|
| [YYYY-MM-DD] | [Scopus] | [angle 1] | [n] | [n] | [n] |
| | | **Total** | [n] | [n] | [n] |

## Records from other methods (path B)

| Key | Method (`OTHER:citation-chase:<seed>` / `OTHER:researcher-supplied`) | Passed Gate 1/2? |
|---|---|---|
| [author-year] | [ ] | [yes / no] |

## Identification

| Item | n | Source |
|---|---|---|
| Total database hits | [n] | import log |
| Duplicates removed at import | [n] | import log |
| Records from other methods | [n] | path B table |
| **Records entering the flow** | **[n]** | newly imported + other methods |

## Screening and eligibility

| Stage | n |
|---|---|
| Records screened (title/abstract) | [n] |
| Excluded at title/abstract (`excluded_title_abstract`) | [n] |
| Full texts assessed for eligibility | [n] |
| Excluded at eligibility (`excluded_eligibility`) | [n] |
| **Included in review (`included`)** | **[n]** |

Check: [screened - excluded = assessed; assessed - excluded = included]. Rows left at `identified`,
`title_abstract`, `eligible`: [0].

## Exclusions by reason code

| Code | Criterion | Title/abstract (n) | Eligibility (n) |
|---|---|---|---|
| E1 | [ ] | [n] | [n] |
| DUP | duplicate record found during screening | [n] | [n] |

Eligibility exclusions listed individually:

| Key | Reason |
|---|---|
| [author-year] | [E#: reason] |

Judgment calls (reversible): [keys, or none]

## Protocol deviations (path D)

[Papers included despite failing a criterion, with the Protocol Change log date, or "none".]

## Outside the flow

| Item | n |
|---|---|
| Previously published reviews (`prior_review`) | [n] |
| Cited or background only (`outside_flow`) | [n] |
| **Total rows in `arti-lit`** | **[n]** (flow rows + the two lines above) |

## Reconciliation (Stage 4)

| Path × stage | Funnel log | `arti-lit` rows | Difference |
|---|---|---|---|
| [A / included] | [n] | [n] | [0] |

Rows with no path prefix in `search_source` are listed as "unclassified"; the researcher decides
A / B / C / D for each.

## Open points for the figure

- [Decisions still needed at figure time, or none]

## Change log

- [YYYY-MM-DD]: [what changed]
