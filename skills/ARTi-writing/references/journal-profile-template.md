# Journal Profile
**Date Created:** [YYYY-MM-DD]
**Last Updated:** [YYYY-MM-DD]
**Example Articles Analyzed:** [N of 5–8 — list titles or DOIs. Mark with * the papers already
read in ARTi-idea Stage 5; they count toward the total and are not re-read.]

> Blocks B, C, and D are extracted in a **single reading pass per paper**, then synthesized once
> across all papers. Do not read the same paper three times, once per block.

---

## Block A — Administrative Requirements

| Field | Details |
|---|---|
| Journal Name | |
| Publisher | |
| Aims & Scope | |
| Target Audience | |
| Discipline / Field | |
| Indexing | Scopus / WoS / other |
| Q-Ranking | Q1 / Q2 / Q3 / Q4 |
| Impact Factor / CiteScore | |
| Accepted Article Types | Research article / Communication / Review / other |
| Manuscript Structure | Combined Results & Discussion / Separate / other |
| Total Word Limit | |
| Word Limit per Section | Introduction: / Methods: / Results: / Discussion: / Conclusion: |
| Abstract Format | Structured (with subheadings) / Unstructured paragraph |
| Abstract Word Limit | |
| Keywords | Min: / Max: / Placement: |
| Max Figures | |
| Max Tables | |
| Figure Format & Resolution | |
| Reference Style | Numbered / APA / ACS / Vancouver / other |
| Supplementary Material | Allowed / Not allowed |
| Cover Letter Required | Yes / No |
| Highlights Required | Yes / No |
| Graphical Abstract Required | Yes / No |

**Unusual Requirements / Notes:**
- [Any requirements that will significantly affect manuscript structure or preparation]

---

## Block B — Voice Profile Pointer

> Block B no longer holds a full writing-style extraction. That content is a reusable,
> cross-project **Voice Profile** — see `voice-profile-template.md` — built once per researcher
> and reused across every project. This block only records which Voice Profile is in effect here
> and what, if anything, this specific journal requires that differs from it.

**Voice Profile in effect:** `~/.arti/voice-profiles/[voice-slug].md`

**Journal-specific style delta** (only fill fields that genuinely differ from the Voice Profile —
leave the rest blank; a mostly-empty table here is the expected, healthy result):

| Dimension | Voice Profile says | This journal requires instead |
|---|---|---|
| Citation style | | |
| Hedging / claim strength | | |
| Section-level structure | | |
| [Other, if observed] | | |

---

## Block C — Technical Depth Profile

> Extracted from analysis of example articles. Populated by Claude after user feeds example papers.

### Characterization Panel
- **Techniques always present:** [List — e.g., XRD, FTIR, SEM/TEM, UV-Vis/DRS]
- **Techniques commonly present:** [List — e.g., BET, XPS, PL spectroscopy]
- **Techniques occasionally present:** [List — e.g., TGA, EIS, DFT]
- **Typical technique count per paper:** [N techniques]
- **Techniques used for mechanistic insight (not just characterization):** [List]

### Data Reporting Standards
- **Error bars / standard deviation:** [Always reported / Sometimes / Rarely]
- **Reproducibility experiments:** [Standard / Occasional / Not common]
- **Significant figures convention:** [N sig figs typical for key measurements]
- **How efficiency/yield/rate is reported:** [Specific format observed]

### Analysis Depth Benchmark
- **Discussion depth:** [Primarily descriptive / Interpretive / Mechanistic]
- **Computational/theoretical support (DFT, modeling):** [Common / Occasional / Rare]
- **Kinetic or thermodynamic analysis:** [Common / Occasional / Rare]
- **Control experiments:** [Standard — always included / Occasional / Rare]
- **Mechanism proposal:** [Always / Sometimes / Rarely — with or without supporting evidence]

### Claim Strength Norms
- **Novelty statement style:** [Bold and explicit / Moderate / Conservative]
- **State-of-the-art benchmarking:** [Performance comparison table standard / Sometimes / Rare]
- **Limitations acknowledged:** [Explicitly in Discussion / In Conclusion / Rarely]
- **Comparative claims vs. prior work:** [Quantitative / Qualitative / Both]

### Figure Construction Norms
- **Panel type:** [Mostly single / Mostly composite / Mixed]
- **Typical figure count:** [N figures per paper]
- **Schematic diagrams / mechanism illustrations:** [Common / Occasional / Rare]
- **Scheme figures (synthesis route, etc.):** [Common / Occasional / Rare]

### Technical Gaps to Watch
> Filled by Claude after Block C analysis — techniques or analyses typical for this journal
> that the user's current Scratchbook does not yet address.

- [Gap 1 — e.g., "XPS analysis present in 4/5 example papers — not yet in Scratchbook"]
- [Gap 2]
- [Gap 3]

---

## Block D — Novelty Profile

> Extracted from analysis of example articles. Populated by Claude after user feeds example papers.
> Answers the critical question: what level of novelty does this journal actually require?

### Novelty Scores of Example Articles

> For each example article, Claude estimates the C/M/E novelty score based on what the paper
> actually contributes — not just how it is described by the authors.

| Article | C — Conceptual | M — Methodological | E — Empirical | Composite |
|---|---|---|---|---|
| [Author, Year — short title] | [1–5] | [1–5] | [1–5] | [Label] |
| [Author, Year — short title] | [1–5] | [1–5] | [1–5] | [Label] |
| [Author, Year — short title] | [1–5] | [1–5] | [1–5] | [Label] |
| [Author, Year — short title] | [1–5] | [1–5] | [1–5] | [Label] |
| [Author, Year — short title] | [1–5] | [1–5] | [1–5] | [Label] |

**Scoring reference:**
- C 1=Replication, 2=Extension, 3=Gap-filling, 4=Reframing, 5=Paradigm-shifting
- M 1=Standard methods, 2=Adaptation, 3=Cross-field application, 4=Method development, 5=New technique
- E 1=Confirmatory, 2=Incremental data, 3=First-reported, 4=Quantitative revision, 5=Contradictory finding

### Journal Novelty Threshold

> Synthesized from the example article scores above.

| Dimension | Observed range | Typical minimum | Notes |
|---|---|---|---|
| C — Conceptual | [n–n] | [n] | [e.g., "Gap-filling is the minimum; reframing appears in top-cited papers"] |
| M — Methodological | [n–n] | [n] | [e.g., "Standard methods accepted if C and E are strong"] |
| E — Empirical | [n–n] | [n] | [e.g., "First-reported data always required"] |

**Minimum composite label this journal accepts:** [Incremental / Meaningful / Significant / Paradigm-shifting]

**Novelty emphasis:** [Which dimension does this journal weight most?
e.g., "Empirical novelty is non-negotiable — all papers report first-reported or
quantitatively revised findings. Methodological novelty is less important if the
conceptual and empirical contributions are strong."]

### Your Manuscript's Novelty Fit

> Filled by Claude when evaluating the manuscript against this journal.
> If ARTi-idea was used, import scores from the Idea Canvas directly (the handoff manifest names the file).
> If not, Claude estimates scores from the Scratchbook and manuscript content.

**Your manuscript's novelty score:**

| Dimension | Your score | Journal minimum | Fit |
|---|---|---|---|
| C — Conceptual | [1–5] | [n] | ✅ Meets / ⚠️ Borderline / ❌ Below threshold |
| M — Methodological | [1–5] | [n] | ✅ Meets / ⚠️ Borderline / ❌ Below threshold |
| E — Empirical | [1–5] | [n] | ✅ Meets / ⚠️ Borderline / ❌ Below threshold |

**Overall novelty fit:** ✅ Meets journal threshold / ⚠️ Borderline / ❌ Below threshold

**Novelty fit assessment:**
[Claude writes 2–3 sentences: does this manuscript's novelty profile match what this journal
publishes? If borderline or below — what specifically needs to be strengthened, and in which
dimension? If the gap cannot be resolved through writing, flag whether the research itself
needs to be extended before submission.]

**Action required before submission:**
- 🔴 Critical novelty gap: [Dimension below threshold — specific action needed]
- 🟡 Borderline dimension: [Dimension at threshold — how to strengthen the framing]
- ✅ No novelty action needed

---

## Block D Update Protocol

> Block D is a living section. It must be updated at two points:

**1. At Journal Profile creation (after feeding example papers):**
Claude completes the Novelty Scores of Example Articles table and derives the Journal
Novelty Threshold. The "Your Manuscript's Novelty Fit" section is left blank until
a draft exists.

**2. At Iteration Log creation (for each draft):**
Claude updates "Your Manuscript's Novelty Fit" based on the current draft content.
If the novelty fit changes between drafts (e.g., the Discussion now makes a stronger
empirical claim), update the scores and assessment accordingly.

If the manuscript's novelty score falls below the journal threshold at any evaluation,
this is a 🔴 Critical item in the Iteration Log Priority Action List — it must be
resolved before the next draft.