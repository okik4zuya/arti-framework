# Prior Review Check — [topic]

**Date:** [YYYY-MM-DD]
**Verdict:** [clear / partial overlap / near-duplicate]

> Output of Stage 1 Part C (`stage1-question-and-protocol.md`). Records which published reviews
> already cover this review's question, so the novelty claim in the Introduction (paragraph 2) is
> backed by logged searches, not memory. Re-run before submission (Stage 4) — reviews appear
> continuously.

## Searches run

One row per query, narrowest first. Log the count before running the next.

| # | Database | Query (OpenAlex: copy `meta.oql`) | Filters | Hits | Date run |
|---|---|---|---|---|---|
| 1 | OpenAlex | [e.g. SnO2 AND "CO2 photoreduction"] | type=review, title_abstract | [n] | [YYYY-MM-DD] |
| 2 | Scopus | [TITLE-ABS-KEY(...) AND DOCTYPE(re)] | — | [n] | [YYYY-MM-DD] |

## Reviews found

One row per review that touches the topic; add each to `arti-lit` as `prior_review`
(`--search-source openalex-prior-review` / `scopus-prior-review`).

| Key (arti-lit) | Year | Type (systematic / narrative / bibliometric) | Material scope (this review's material vs. general class) | Reaction scope (e.g. CO2 only vs. broader) | Modification strategies covered | Year window searched | Overlap |
|---|---|---|---|---|---|---|---|
| [author-year] | [YYYY] | [ ] | [ ] | [ ] | [ ] | [ ] | [none / partial / high] |

## Verdict

- **clear** — no review covers this material + reaction + strategy combination.
- **partial overlap** — reviews exist on the broader class or adjacent reaction; name what each
  leaves uncovered.
- **near-duplicate** — a recent review covers the same scope; stop and revisit the RQ with the
  researcher before Protocol.

## Differentiating sentence (Introduction, paragraph 2)

> If the Scopus `DOCTYPE(re)` re-run is still pending, the Introduction says "to our knowledge"
> and the handoff carries an open flag (`slr-handoff-template.md`) until it is closed.

[One or two sentences: what the closest prior reviews cover, and what this review adds — the
material scope, strategy coverage, or time window they do not reach.]
