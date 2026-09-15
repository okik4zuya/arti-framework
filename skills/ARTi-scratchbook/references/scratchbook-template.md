# Scratchbook
**Paper Topic:** [Brief description of your research]
**Target Journal:** [Journal name — link to Journal Profile]
**Date Started:** [YYYY-MM-DD]
**Last Updated:** [YYYY-MM-DD]

---

## Tagging System Legend

| Tag | Meaning |
|---|---|
| `[OWN]` | Your own data, observation, or experimental finding |
| `[LIT: Author, Year]` | Claim sourced from literature — must match Reference List |
| `[SOURCE NEEDED]` | Claim without a source — resolve before drafting |
| `[CONNECTION: Author, Year → note]` | How a reference connects to your specific research |
| `[⚠️ CONTRADICTION: A, Year vs. B, Year — note]` | Conflicting findings — flag for Discussion synthesis |
| `[UNVERIFIED — USER MUST CONFIRM]` | Claude-suggested reference not yet verified by user |
| `[CITATION NEEDED]` | Manuscript claim with no source in Scratchbook |
| `[DATA NEEDED]` | Missing numerical value or result needed for drafting |

> **Rule:** Every entry must carry a tag. Every `[LIT:]` tag must have a matching entry in `## Reference List`.
> **Plagiarism reminder:** Paraphrase all literature at the point of entry — never paste source text verbatim.

---

## The `Argumen saat ini` line

Every content section below opens with an **`Argumen saat ini`** (current argument) line: one to
three sentences stating what that section currently argues or has found. It is the condensed
counterpart to the raw dumps sitting directly beneath it — not a dump, not raw tags, not full
citations.

Update it in the same edit as the material below it, whenever that material changes what the
section is actually arguing. Because it lives inside the section it summarizes, it cannot fall out
of sync with a separate file. A dump that doesn't change the argument (e.g. a reference parked in
`## Unassigned Literature`) needs no update to the line.

Read these lines first for a fast orientation on where the paper stands; go to the dumps for the
supporting material.

---

## Introduction

**Argumen saat ini:** [1–3 sentences: the gap being addressed and the novelty claim, as currently understood]

> *Dump here: background context, research gap, motivation, novelty claims, relevant literature.*
> *No need for flow or coherence — just get it all down.*

<!--
EXAMPLE ENTRIES:
[LIT: Wang, 2021] SnO2 nanoparticles widely studied for photocatalytic CO2 reduction due to wide bandgap and chemical stability.
[CONNECTION: Wang, 2021 → directly supports motivation for using SnO2 as base material]

[OWN] Preliminary results show 3x higher formate yield compared to bare SnO2 — this is the novelty claim.

[LIT: Chen, 2019] TiO2-based composites showed enhanced charge separation under visible light.
[LIT: Wang, 2021] SnO2 alone showed limited visible light absorption.
[⚠️ CONTRADICTION: Chen, 2019 vs. Wang, 2021 — Chen reports TiO2 composites outperform SnO2 for light absorption, Wang argues SnO2 stability is the critical factor. Address in Discussion.]
-->

---

## Materials & Methods

**Argumen saat ini:** [1–3 sentences: what was made/done and the key methodological choice, if any]

> *Dump here: materials used (source, purity, grade), synthesis procedure, characterization instruments, analysis methods, software.*
> *⚠️ HIGHEST PLAGIARISM RISK — always write from your own notes, never from protocol papers directly.*

<!--
EXAMPLE ENTRIES:
[OWN] SnO2 nanoparticles synthesized via hydrothermal method at 180°C for 12h.
[OWN] XRD: Bruker D8 Advance, Cu Kα radiation (λ = 1.5406 Å), 2θ range 10–80°.
[LIT: Hirano, 2011] Forced co-hydrolysis under hydrothermal conditions produces rutile-type TiO2-SnO2 nanoparticles with controlled phase composition.
[CONNECTION: Hirano, 2011 → justifies our hydrothermal synthesis conditions]
-->

---

## Results & Discussion

> *Dump here: characterization results, observed data, interpretation, comparison with literature.*
> *Organize by characterization technique. Combine Results and Discussion dumps in the same section.*
> *If your journal separates Results and Discussion, use the two separate sections below instead.*
> *Each subsection carries its own `Argumen saat ini` line.*

### XRD Analysis

**Argumen saat ini:** [1–3 sentences: the headline finding and what it establishes]

<!--
EXAMPLE ENTRIES:
[OWN] Main diffraction peaks at 2θ = 26.6°, 33.9°, 51.8° — match rutile SnO2 (JCPDS 41-1445).
[OWN] Average crystallite size = 8.3 nm from Scherrer equation (K=0.9, β from FWHM).
[LIT: Eifert, 2017] Intermediate tin-oxide phases show additional Raman peaks absent in pure SnO2.
[CONNECTION: Eifert, 2017 → supports XRD phase purity interpretation — absence of extra peaks confirms pure SnO2]
-->

### FTIR / Raman Analysis

**Argumen saat ini:** [1–3 sentences]

<!-- Add entries below -->

### SEM / TEM Analysis

**Argumen saat ini:** [1–3 sentences]

<!-- Add entries below -->

### Optical Properties (UV-Vis / DRS)

**Argumen saat ini:** [1–3 sentences]

<!-- Add entries below -->

### Photocatalytic / Electrochemical Performance

**Argumen saat ini:** [1–3 sentences]

<!-- Add entries below -->

---

## Results (Separate — use only if journal requires split sections)

**Argumen saat ini:** [1–3 sentences]

> *Dump observed findings and measurements only. No interpretation here.*

<!-- Add entries below -->

---

## Discussion (Separate — use only if journal requires split sections)

**Argumen saat ini:** [1–3 sentences]

> *Dump interpretations, literature comparisons, explanations of unexpected results.*
> *All `[⚠️ CONTRADICTION]` tags from other sections must be addressed here.*

<!-- Add entries below -->

---

## Conclusion

**Argumen saat ini:** [1–3 sentences: the takeaway and its significance, as currently understood]

> *Dump here: key takeaways, significance, future work ideas.*
> *All entries should be [OWN] — no new citations in Conclusion.*

<!-- Add entries below -->

---

## Abstract

**Argumen saat ini:** [Leave empty until the other sections have real content — this would be a summary of a summary]

> *Leave empty until all other sections are drafted.*
> *Written last. Summarize: background, objective, methods, key results, significance.*
> *No citations, figures, or undefined abbreviations.*

<!-- Add entries below -->

---

## Unassigned Literature

> *References collected but not yet placed in a section.*
> *This section must be empty before manuscript drafting begins.*
> *Move each entry to the appropriate section above as the Scratchbook develops.*
> *No `Argumen saat ini` line here — nothing in this section is arguing anything yet.*

<!--
FORMAT:
[LIT: Author, Year] — brief note on content and why it may be relevant
[CONNECTION: Author, Year → tentative relevance note]
-->

---

## Reference List

> *Claim mapping, not bibliographic detail.* Full bibliographic entries live in
> `literature\library.md` (one line per source, canonical), keyed `author-year[a|b]` (e.g.
> `kaw-2016`). This section only maps that key to where/how it's used in this Scratchbook — it
> exists so a `[LIT: Author, Year]` tag has something to resolve against without re-typing the
> full citation here.
> *Every `[LIT: Author, Year]` tag anywhere in this Scratchbook must have a matching key below, and
> that key must have a full entry in `literature\library.md`.*
> *If a key isn't in `library.md` yet, tag it `[UNVERIFIED — USER MUST CONFIRM]` here until it is.*

<!--
ENTRY TEMPLATE:
`kaw-2016` — used in: Introduction (motivation), Results/Discussion (XRD comparison)

EXAMPLE:
`hirano-2011` — used in: Materials & Methods (hydrothermal synthesis justification)
-->
