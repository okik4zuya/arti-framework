# Stage 1 — Journal Profile: protocol

Full procedure for building the Journal Profile (Core Document #1: Blocks A, B, C, D). Read this
when Stage 1 fires — see `SKILL.md`'s Stage 1 stub for the trigger condition and output file. See
`references/journal-profile-template.md` for the blank template.

## Block A — Administrative Requirements

- Help the user identify and fill in all journal requirement fields
- Search for or analyze provided journal guidelines
- Flag any unusual requirements that will affect manuscript structure
- **Indexing and ranking (Scopus, WoS, Q-rank, Impact Factor) is sourced from `arti-jfinder`, not
  hand-typed or recalled from general knowledge.** Call `journal get --id SOURCEID` (resolving the
  id first via `journal search --keyword TEXT` if only the journal's name is known) to populate
  this field from the real Scimago snapshot — same pattern `ARTi-idea` Stage 5 already uses for the
  Journal Target Sheet. Fall back to general-knowledge/user-supplied values only if the lookup
  misses (empty/missing database), per `ARTi-jfinder`'s own documented fallback.

## Block B — pointer only (read/extend-half of the Stage 0 ↔ Stage 1 coupling)

Record which Voice Profile file is in effect for this project — this is the same pointer line
Stage 0's Selection step writes (see `references/stage0-voice-profile-protocol.md`); Stage 1 reads
and extends it, never re-writes it from scratch. While reading the journal's example articles for
Blocks C and D (below), note only the deltas that actually differ from that Voice Profile — e.g.,
this journal's citation format, or a section-length norm the researcher's own papers don't share.
Do not re-extract the full style profile here; that work now lives in Stage 0.

## Blocks C, D — Single-Pass Extraction Protocol

Example papers are read **once each**. For every paper, Claude extracts technical depth and
novelty in the same reading pass, then runs **one synthesis pass** across all papers to produce
Blocks C and D. Do not run separate protocols over the same paper set — the output is identical
and the reading cost is doubled.

**How many papers:** 5–8, **inclusive of the 2–3 already read in ARTi-idea Stage 5**. Those papers
count toward the total; do not re-read them from scratch — extend what was already extracted.

### Pass 1 — Per paper (one reading, two profiles)

*Technical depth (feeds Block C):*

*Characterization panel:*
- Which techniques are used and in what combination
- Which techniques serve characterization only vs. mechanistic insight
- Typical number of characterization techniques per paper

*Data reporting standards:*
- Whether error bars, standard deviations, or repeatability data are reported
- How measurements are quantified and reported (significant figures, units)
- Whether reproducibility experiments are standard

*Analysis depth benchmark:*
- Whether Discussion is primarily descriptive, interpretive, or mechanistic
- Whether computational or theoretical support (DFT, modeling, kinetics, thermodynamics) is common or rare
- Whether control experiments are standard

*Claim strength norms:*
- How boldly novelty is stated in the Introduction and Conclusion
- Whether state-of-the-art benchmarking or performance comparison tables are expected
- How limitations are acknowledged

*Figure construction norms:*
- Single vs. composite panel figures
- Typical total figure count per paper
- Whether schematic diagrams or mechanism illustrations are common

*Novelty (feeds Block D):*

Score the paper's novelty across three dimensions:
- **C — Conceptual novelty** (1–5): How new is the research question?
  1=Replication, 2=Extension, 3=Gap-filling, 4=Reframing, 5=Paradigm-shifting
- **M — Methodological novelty** (1–5): How new is the approach?
  1=Standard methods, 2=Adaptation, 3=Cross-field application, 4=Method development, 5=New technique
- **E — Empirical novelty** (1–5): How new are the findings?
  1=Confirmatory, 2=Incremental data, 3=First-reported, 4=Quantitative revision, 5=Contradictory finding

Claude must justify each score with a specific observation from the paper — not just assign a number.
Example: "C=3 because the paper asks a question not previously addressed in the literature
(the authors explicitly state no prior study has examined X in Y context)."

*Section-level outline norms (review-type articles only, feeds Block C):*

For a review-type article, also record each paper's **verbatim top-level (and, where used,
second-level) section headings**, copied directly from the paper's own fulltext file as Pass 1
reads it — not reconstructed from memory or a narrative skim afterward. This is what Pass 2 checks
frequency claims against and what Stage 2's Blueprint later consults instead of defaulting to a
generic IMRaD heading.

### Pass 2 — Synthesis across all papers

Run once, after every paper has been through Pass 1:

*For Block C:*
1. Synthesize a consensus Technical Depth Profile across all articles
2. Note where papers vary in technical rigor
3. Flag any technique or analysis type appearing in most papers that the user has not yet addressed
4. **Verify frequency claims before stating them.** Any claim about how many papers follow a
   structural or content convention ("N/5 examples do X") must be checked against the literal
   per-paper text, not asserted from a single earlier reading pass's impression. For a convention
   whose presence or absence isn't obvious from the section-heading list alone (e.g., whether a
   search methodology is explicitly stated, or which of several papers actually pair Conclusions
   with a separate Future Research Directions section), re-open the paper's fulltext and search for
   it directly rather than relying on recall. (Illustrative, not exhaustive — this project's own
   Block C once wrongly reported 3/5 examples stating an explicit search methodology when the true
   count was 1/5, and 4/5 pairing Conclusions with Future Research Directions when the true split
   was 1/5 clean pair, 1/5 merged heading, 1/5 nested elsewhere, 2/5 absent.)
5. For review-type articles, synthesize the per-paper verbatim headings from Pass 1 into the
   **Section-Level Outline Norms** table (see the Block C template) — what's universal across all
   examples, what's common but not universal, and what's genuinely variable/minority-pattern
6. Produce a completed Block C ready to paste into the Journal Profile

*For Block D:*
1. Complete the Novelty Scores of Example Articles table
2. Derive the Journal Novelty Threshold: record the range and typical minimum for each dimension,
   identify which dimension(s) the journal weights most heavily, state the minimum composite label
   the journal accepts, and note whether any dimension can be low if compensated by another
3. Note which novelty dimension is most critical for this journal
4. Produce a completed Block D (threshold section only) ready to paste into the Journal Profile

*Manuscript novelty fit (filled per draft, not at creation — Block D touch point 2 of 4, see
`SKILL.md`'s Key Principles table for the full list):*
When producing an Iteration Log entry, Claude must also update Block D's
"Your Manuscript's Novelty Fit" section by scoring the current draft's C/M/E
against the journal's threshold. If any dimension falls below the threshold,
flag it as 🔴 Critical in the Iteration Log Priority Action List.

## If ARTi-idea was used

- The Stage 5 light novelty threshold for this journal is **extended, not re-derived from zero**.
  Start from the recorded light threshold and deepen it with the additional papers.
- The 2–3 papers already read in Stage 5 **count toward the 5–8**. Only the remaining papers need
  a fresh Pass 1.
- Import the confirmed C/M/E scores from the Idea Canvas directly into Block D's
  "Your Manuscript's Novelty Fit" table. Use these as the starting scores for Draft 1. This is
  Block D touch point 1 of 4 (threshold-set) — see `SKILL.md`'s Key Principles table for the full
  list. Update the scores if the manuscript content changes the novelty profile during drafting.
