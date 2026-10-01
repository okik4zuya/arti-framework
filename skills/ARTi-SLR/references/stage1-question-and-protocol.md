# Stage 1 — Judul + RQ + PICO(C), then Protocol: procedure

Full procedure for the first two core documents. Read this when Stage 1 fires — see `SKILL.md`'s
Stage 1 stub for the trigger condition and output files.

## Part A — Judul + RQ + PICO(C)

- Reuse the existing Researcher Profile / Wawancara flow (`ARTi-idea`/`ARTi-setup`) — do not build
  a new interview step. If `~/.arti/memory/researcher-profile.md` doesn't exist yet, run
  `ARTi-setup`'s Workflow A first.
- Judul and RQ are decided **together, not sequentially**: draft the RQ from the researcher's
  stated topic, decompose it into PICO(C) terms, then compress the RQ into a working title — never
  the other way around (a title invented first and reverse-engineered into an RQ tends to hide
  scope creep).
- Every RQ must decompose into explicit P/I/(C)/O terms — an RQ that can't be written this way
  isn't specific enough for Stage 2's search-string construction.
- Run the Researcher Profile Check (see template) before treating the RQ as confirmed: a review
  scope the researcher cannot source/screen/extract within their stated timeline and access is not
  a real question yet — narrow it.
- **Output:** `slr\judul-rq-pico.md`, using `references/judul-rq-pico-template.md`.

## Part C — Cek Review Terdahulu

**Trigger:** Judul + RQ + PICO(C) confirmed, before Part B locks the Protocol. A review whose
scope an existing review already covers is not worth the Protocol and search effort, so check
first. **Output:** `slr\prior-reviews.md` (`references/prior-review-check-template.md`).

- **OpenAlex, narrow to broad.** Run `count_openalex_works` first (same filters, `group_by="type"`
  or `"publication_year"`) to measure each query's width without pulling records, then pull hits
  with `search_openalex_works(work_type="review", search_in="title_abstract",
  exclude_retracted=True)`. Climb a ladder, one angle per query: the exact material + reaction
  phrase → the material class (e.g. metal oxide / semiconductor) + reaction → the reaction alone,
  general. A zero on the narrow rung means nothing until the broader rungs are checked — the
  review that overlaps is usually written about the class, not the single material. Use
  `search_in="all"` only deliberately: it also matches full text and is broader and pricier.
- **Scopus is required, not optional.** Give the researcher a query of the form
  `TITLE-ABS-KEY(...) AND DOCTYPE(re)` (narrow, one angle per code block, bare and copy-ready, per
  the Part B conventions below); the researcher runs it and pastes the count and hits in chat. Ask
  for an RIS export only when there are more than ~50 hits. OpenAlex's `review` type comes from
  Crossref and misses some reviews Scopus classifies as such, which is why both run.
- **Read before judging.** For every candidate review, read its abstract (and fulltext when the
  abstract does not settle scope): material scope, reaction scope, modification strategies,
  year window, systematic vs. narrative. Fill the template's table; a title match alone is not
  evidence of overlap.
- **Store the reviews in `arti-lit`** with `library add --screening-stage prior_review
  --search-source openalex-prior-review` (or `scopus-prior-review`), after the usual DOI dedup
  check. `prior_review` rows stay out of the PRISMA counts (exact-match stage queries).
- **Verdict:** `clear` / `partial overlap` / `near-duplicate`, plus the differentiating sentence
  for the Introduction. On `near-duplicate`, stop and take the RQ back to the researcher before
  Part B. Log each query's date and hit count in the template.

## Part B — Protocol

**Trigger:** Judul + RQ + PICO(C) confirmed.

- The database list is fixed **here**, before any search runs — Stage 2 loops over exactly this
  list, so an incomplete list here means an incomplete search later, not a place to add databases
  ad hoc mid-search.
- Inclusion/exclusion criteria are derived from the PICO(C) elements plus standard SLR scope
  controls (date range, language, article type, full-text availability).
- Search strings are constructed from the PICO(C) term table, one column per element, combined
  with boolean AND/OR — adapt exact syntax per database in Stage 2, but the term table here is the
  single source of truth for which words are used.
- **Never lock a single combined string with a broad OR-group on the Intervention side** — if the
  Intervention decomposes into multiple distinct sub-strategies (e.g. doping, heterostructure,
  defect engineering), one string ORing all of them together lets a paper match on *any* one, which
  inflates the hit count into the thousands/tens-of-thousands and defeats the point of scoping.
  **Split into one query per sub-strategy angle** (5–8 queries is typical), each narrow enough to
  land in the low hundreds or fewer. Report and log each query's count before moving to the next —
  a query still landing in the thousands needs a narrower Outcome phrase, not to be left as-is.
- **Prefer exact multi-word phrases over single generic words for the Outcome element** — a bare
  word like "composite" or "reduction" matches enormous unrelated literature; a quoted phrase like
  `"photocatalytic CO2 reduction"` or `"CO2 photoreduction"` scopes correctly. If the first pass on
  a phrase-scoped query comes back surprisingly low (single digits to ~20), widen the Outcome
  phrase set with a few known alternate phrasings (e.g. add `"photocatalytic reduction of CO2"`,
  `"CO2 photocatalytic conversion"`) and re-test rather than assuming the topic itself is empty.
- **Always include the database's explicit field-scope function in the locked string** (e.g.
  Scopus's `TITLE-ABS-KEY(...)` or the narrower `TITLE-ABS(...)`) — omitting it is not a
  simplification, it changes the search mode. In Scopus specifically, a query submitted through
  Advanced Search without a field-scope wrapper falls back to a broad/fuzzy match across all
  indexed fields (references, funding text, etc.) rather than enforcing the boolean structure on
  title/abstract/keywords, which silently inflates the count with irrelevant hits — confirmed by a
  sample check where the core P-term didn't even appear in the returned hits' title/abstract. If
  hit counts look implausible relative to the query's specificity, re-verify the field scope before
  assuming the topic is broader than expected.
- **Before locking the Intervention angle list, sanity-check it against at least one paper the
  researcher already knows is in scope** (from their own citation list, a prior manuscript, or a
  manual spot-check search) — run it through every angle query mentally (does it contain any of
  angle N's I-terms?) rather than assuming the sub-strategy list is exhaustive just because it
  covers the "obvious" categories. In a materials/synthesis-modification review specifically, watch
  for two commonly-missed angle types: (1) **surface/synthesis-condition modification** (annealing,
  calcination, hydroxylation, facet engineering, morphology control) as a distinct class from
  doping/heterostructure/defect-engineering, and (2) **pristine/unmodified baseline studies** — a
  paper reporting only the unmodified material's performance has no "intervention" in the narrow
  sense, but the review's own Comparison (C) element usually depends on this data existing
  somewhere in the corpus, so it needs its own angle (e.g. P + O + `"pristine" OR "pure" OR
  "undoped" OR "unmodified" OR "bare"`), not an assumption that baselines will show up embedded in
  other papers. A missed angle here isn't caught by re-running the same queries — it only surfaces
  when a known-relevant paper is checked against the locked list and doesn't match, so do that
  check before Stage 2 search starts, not after a researcher stumbles on the gap manually.
- Quality appraisal approach (which checklist/rubric) is decided now, even though it isn't applied
  until Stage 3 — deciding it after papers are already extracted risks picking a rubric that
  flatters whatever was found.
- **Protocol is locked before search begins.** If it must change after Stage 2 has started (a
  database turns out to be inaccessible, a criterion proves unworkable), log the change with a
  reason in the template's Change log section rather than silently editing.
- **Output:** `slr\protocol.md`, using `references/protocol-template.md`.
