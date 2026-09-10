---
name: ARTi-writing
description: >
  A structured workflow skill for writing and iterating academic research articles, from journal-profile analysis through submission, review response, and post-acceptance follow-up. Use whenever the user wants to write, draft, improve, or revise a research manuscript. Triggers: writing a journal article, drafting a section, planning a manuscript outline, preparing for submission, writing a cover letter, responding to reviewer comments, analyzing a target journal, matching a writing voice, populating a scratchbook, reviewing a draft, logging revisions, evaluating a manuscript, or logging what happened after acceptance. Manages a document set — Journal Profile (Blocks A, C, D), Voice Profile, Manuscript Blueprint, Scratchbook, Manuscript, Iteration Log, Cover Letter, Rebuttal, Publication Growth Log — guiding Claude from pre-writing through publication and back into the next idea. Block D of the Journal Profile contains novelty scoring (C/M/E) verifying the manuscript's novelty matches the target journal — checked at profile creation and every Iteration Log entry. Below-threshold novelty is flagged 🔴 Critical. Always use this skill for any stage of research writing, even if phrased casually. If the researcher has not confirmed a research idea or journal, direct them to ARTi-idea first.
---

# ARTi-writing Skill

A document-driven, iterative workflow for writing academic research manuscripts, carrying the loop
through submission and into what comes after. The workflow is organized around a set of **core
documents** and a **structured iteration loop**.

---

## Core Documents

### 1. Journal Profile
A reference document capturing everything needed to align the manuscript with the target journal.
Contains three blocks: Administrative Requirements, Technical Depth Profile, and Novelty Profile.
The style dimension that used to be Block D's neighbor now lives outside the Journal Profile
entirely, as its own reusable **Voice Profile** document (below) — a journal doesn't have a
writing style, the papers published in it do, and a researcher's own voice is worth keeping
across journals, not re-derived per project.

**Block D — Novelty Profile** is the addition that answers the critical pre-writing question:
*does this manuscript's novelty level actually match what this journal publishes?* It is populated
during Journal Profile creation (novelty threshold from example papers) and updated at every
Iteration Log entry (novelty fit of the current draft). A manuscript whose novelty falls below
the journal threshold receives a 🔴 Critical flag — this is a desk-rejection risk that must be
resolved before submission.

**Block A — Administrative Requirements:**
- Journal name, publisher, scope, and aim
- Target audience and discipline
- Indexing and ranking (Scopus, WoS, Q-rank, Impact Factor)
- Accepted article types (research article, communication, review, etc.)
- Manuscript structure requirements (e.g., combined vs. separate Results & Discussion)
- Word/page limits per section
- Abstract format and word limit
- Keywords requirements
- Figure, table, and graphic formatting rules
- Reference/citation style

**Block B — pointer only:** Block B no longer holds writing-style content directly. It records
which Voice Profile file is in effect for this project (`~/.arti/voice-profiles/<slug>.md`) and any
journal-specific style deltas observed in the example articles that the chosen Voice Profile
doesn't already cover (e.g., this journal's citation format differs from the researcher's usual
one even though their sentence-level voice doesn't change).

**Block C — Technical Depth Profile:**
Extracted from analysis of example articles provided by the user. Captures:
- Characterization panel: which techniques are typically used and in what combination
- Data reporting standards: whether error bars, standard deviations, reproducibility data are expected
- Analysis depth benchmark: descriptive vs. interpretive vs. mechanistic Discussion norm
- Whether computational/theoretical support (DFT, modeling, kinetics) is common
- Claim strength norms: how boldly novelty is stated, whether state-of-the-art benchmarking is expected
- Figure construction norms: single vs. composite panels, typical figure count

**When to create/update:** At the start of the project. Block A filled from journal guidelines.
Blocks C and D filled by analyzing example articles the user provides — in a **single pass per
paper**, not three passes (see Stage 1). Revisit whenever the target journal changes.

---

### 2. Voice Profile
A reusable record of how one researcher (or one persona) actually writes, extracted once from
their own prior first-author papers and applied across every subsequent project — not
re-extracted per journal. This is the generalized form of what used to be Journal Profile Block B.

**Why it moved out of the Journal Profile:** the writing-style patterns in Block B were being
extracted from *example articles by other authors published in the target journal* — useful for
matching journal convention, but a different thing entirely from *the researcher's own voice*.
Collapsing them into one block meant re-deriving the researcher's style from scratch on every new
journal, and meant a researcher with an established voice (e.g. `gtmk-voice`) had no way to just
apply it. Splitting them lets a Voice Profile persist across a career while the journal-specific
delta stays a lightweight note in Journal Profile Block B.

**Contents (same fields Block B extracted before, now scoped to one voice rather than one
journal):**
- Title patterns, abstract structure and quantification habits
- Voice and tone: passive vs. active ratio, hedging language, claim qualification style
- Section-level patterns: Introduction funnel depth, how figures are introduced, how literature
  comparison is framed, Conclusion length and structure
- Vocabulary and terminology preferences
- In-text citation habits: narrative vs. parenthetical, references per claim

**Two ways a Voice Profile gets built:**
1. **Extracted from the researcher's own papers.** Feed 3–5 of the researcher's own first-author
   papers (any journal); Claude runs the style-extraction pass described in Stage 0 below, scoped
   to "how does this person write" rather than "what does this journal expect," and saves the
   result as a new Voice Profile file. Do this once; update only when the researcher's own style
   has visibly shifted (new field, more experience, a co-author's habits rubbing off).
2. **Supplied ready-made**, e.g. an existing style skill like `gtmk-voice`. Treat it as a Voice
   Profile instance already extracted elsewhere — record a thin pointer file rather than
   re-deriving it, and confirm with the researcher that it still matches their current writing
   before relying on it for a new project.

**When to create/update:** Once per researcher (or per persona, if a researcher deliberately
writes differently across sub-fields), before or during Stage 1 of the first project that needs
one. Reused unchanged across every later project unless the researcher's style has genuinely
shifted.

**File:** `~/.arti/voice-profiles/<voice-slug>.md` — same cross-project persistent-folder pattern
`ARTi-setup` established for the Researcher Profile and Idea Bank; do not invent a new storage
location for it.

---

### 3. Manuscript Blueprint
A paragraph-level outline of the manuscript, produced before Scratchbook population begins, so
drafting has a target shape to fill rather than discovering structure only at Stage 4. Not a
generic IMRaD template — it is derived from this specific journal's actual paragraph-count and
placement patterns.

**What it extracts, from Journal Profile Blocks C and the Voice Profile's section-level patterns:**
- Introduction: paragraph count before the gap statement is introduced, and where the objective
  sentence typically sits (its own paragraph vs. folded into the gap paragraph)
- Results/Discussion: characterization-technique count and typical ordering, how many paragraphs
  per technique, where quantitative comparison to prior work is placed
- Conclusion: paragraph count, whether future work gets its own paragraph

**What it wires in from ARTi-idea (when available):**
- The confirmed C/M/E contribution score from the Idea Canvas, so the blueprint marks *where* the
  novelty claim needs to land (which paragraph carries the conceptual framing, which result
  section needs to carry the empirical claim) rather than leaving it to be discovered during
  drafting.

**Output format:** a paragraph-level outline per manuscript section — "Paragraph 1: gap statement
grounded in [X]; Paragraph 2: objective sentence + contribution preview" — not prose, not a
generic five-section skeleton. Journal-specific: two journals with different Introduction funnel
depths get visibly different blueprints.

**When to create/update:** Once, after the Journal Profile (Blocks A, C, D) and Voice Profile are
both in place and before Scratchbook population starts. Revisit only if the target journal
changes or the Scratchbook reveals the manuscript needs a structurally different shape than
planned (e.g., a technique turned out to need two subsections, not one).

**File:** `writing\manuscript-blueprint.md`

---

### 4. Scratchbook
A section-organized working document used in the early stage of research writing, where the writer freely dumps all raw findings, data interpretations, and supporting literature under their respective manuscript sections — without the pressure of synthesizing, structuring, or polishing the prose. It serves as a thinking space that bridges raw research data and the final manuscript, allowing the writer to accumulate material before committing to analytical narrative.

**Key characteristics:**
- Organized by manuscript sections (e.g., Introduction, Methods, XRD Analysis, etc.)
- Each section opens with a one-to-three-sentence **`Argumen saat ini`** (current argument) line —
  the condensed state of that section's argument, sitting directly above its own raw material
- Contains unfiltered findings, observations, and literature citations tagged inline
- No expectation of flow, coherence, or formal writing style below the `Argumen saat ini` line
- Acts as the raw material source for drafting the manuscript
- Full bibliographic detail lives in `literature\library.md`, not here — the Scratchbook's own
  `## Reference List` is a per-claim key mapping only (see Reference System, below)

**When to create/update:** After the Journal Profile is ready. Populate section by section as data and literature are gathered. Update freely — this document is never "done" until the manuscript is complete.

**Scratchbook Structure:**
```
## [Manuscript Section] (e.g., Introduction / XRD Analysis / Methods)
**Argumen saat ini:** [1–3 sentences — the current state of this section's argument or
finding. Not a dump, not raw tags, not full citations.]

[Raw dumps — findings, observations, literature notes tagged inline]

... repeat for all manuscript sections ...

## Unassigned Literature
[References collected but not yet placed in a section]

## Reference List
[Master bibliography — full bibliographic details of all cited literature]
```

The `Argumen saat ini` line exists so that anyone — researcher or Claude — can get oriented on
where the paper currently stands without reading every raw dump. Because it lives inside the
section it summarizes, it is updated in the same edit as the material beneath it and cannot drift
out of sync.

**Tagging System — Complete Reference:**

| Tag | Meaning |
|---|---|
| `[OWN]` | User's own data, observation, or finding |
| `[LIT: Author, Year]` | Claim sourced from a specific literature entry |
| `[SOURCE NEEDED]` | Claim without a source — must resolve before drafting |
| `[CONNECTION: Author, Year → note]` | How a reference connects to the research — placed inline near the relevant dump |
| `[⚠️ CONTRADICTION: A, Year vs. B, Year — note]` | Conflicting findings between two sources — flag for synthesis in Discussion |
| `[UNVERIFIED — USER MUST CONFIRM]` | Claude-suggested reference not yet verified by user |
| `[CITATION NEEDED]` | Manuscript draft claim with no source in Scratchbook |
| `[DATA NEEDED]` | Missing numerical value or experimental result needed for drafting |

**Bibliography Rules:**
- Every reference used anywhere in the Scratchbook must resolve, via its `author-year[a|b]` key, to
  a full entry in `literature\library.md` — the canonical bibliography (see Reference System below)
- Inline tags `[LIT: Author, Year]` must match a key present in `literature\library.md`
- No claim may be tagged `[LIT:]` without a corresponding `library.md` entry
- References not yet assigned to a section go to `## Unassigned Literature` first, then moved to the appropriate section as the Scratchbook develops

---

## Reference System

Three layers, one shared key: `author-year[a|b]` (e.g. `kaw-2016`, `pintrich-1991`) links the
library row, the fulltext filename, the Scratchbook's per-claim mapping, and the in-text citation.

| Layer | File | Role | Written by |
|---|---|---|---|
| 1 | `literature\search-log.md` | one row per search round | Claude, from raw exports |
| 2 | `literature\library.md` | **canonical** bibliography, one source per line, superset incl. screened-out | Claude |
| 3 | `writing\references.md` | **generated** — filtered to citations present in the current draft | Claude, regenerated on demand |

**Layer 1 — `search-log.md`.** Columns: `ID | query (bare, copy-ready) | date | hits | export file
| target claim/paragraph | status`. Status vocabulary: `pending` / `screened — N used` /
`screened — none relevant`.
- The researcher never renames raw exports — they land in `literature\exports\` as-downloaded;
  Claude parses each one, assigns the ID, and fills the row.
- If an unrenamed export arrives with no way to tell which query produced it, ask which query it
  was rather than guessing from the filename.
- Format-agnostic parsing: RIS, BibTeX, CSV, or plain text, whatever the database emits.
- DOI-based dedup across overlapping queries before screening.
- Keywords are presented bare and copy-ready — no `TITLE-ABS-KEY(...)` wrapper.
  `TITLE(...)`/`SRCTITLE(...)` stay wrapped since they aren't reachable from the basic search box.
- **Known Scopus RIS defect:** some records carry un-substituted i18n keys in place of type codes
  (`label.ris.referenceType.BOOK_CHAPTER`, `label.ris.referenceType.CONFERENCE_REVIEW.p`).
  Normalize these to `CHAP` and `JOUR` on ingest.

**Layer 2 — `library.md` (canonical, generated).** One reference = one line. Columns: `key | full
citation in the target journal's style | DOI | local file path | read-status | used-in`.
Read-status vocabulary: `export-only` / `abstract` / `fulltext` / `read`. Being a superset that
includes screened-out sources is what stops a query from being re-run. **`library.md` is a
generated export — never hand-edit it**, but it stays plain, always-current Markdown, so a browsing
read (e.g. "what have I collected so far", "what's still export-only") can just read the file
directly — no CLI call needed for that. The CLI is required for anything that *changes* the data,
and useful for a targeted dedupe check before adding:
```
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library add --key KEY --citation TEXT [--doi TEXT] [--local-file TEXT] [--status export-only|abstract|fulltext|read] [--used-in TEXT] --project PATH
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" library update --key KEY [--status TEXT] [--used-in TEXT] ... --project PATH
```
`library add` rejects a duplicate DOI on a different key instead of inserting a near-duplicate row
— run `library search KEYWORDS...` first when in doubt. See `tools/arti-lit/README.md` for the
full subcommand reference.

When a batch of PDFs already has `library.md` rows (`local file: —`, status `export-only` or
`abstract`) and needs bulk conversion to fulltext Markdown, use `tools/arti-pdf-ingest` instead of
ingesting one-by-one:
```
"~/.arti/python/python.exe" "~/.arti/tools/arti-pdf-ingest/cli.py" ingest --project PATH --manifest PATH
```
It requires the `key` to already exist in `library.md` — screening/`library add` still happens
first, this tool never creates new library rows — and it registers the result itself via
`arti-lit library update --status fulltext`, so no separate registration step follows. See
`tools/arti-pdf-ingest/README.md` for the manifest format.

**Layer 3 — `references.md` (generated).** Regeneration routine: Grep the Scratchbook for
`[LIT: key]` tags (cheap, targeted — not a full draft/Scratchbook/library regex pass) to get the
key list in appearance order, then:
```
"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" refs generate --keys KEY,KEY,... --order appearance|alpha --project PATH
```
`--order appearance` preserves the order the Scratchbook tags were found in; `--order alpha` sorts
by the key's `author-year[ab]` shape — pick per Journal Profile Block B. Any key in the result's
`unresolved` list is reported as `[CITATION NEEDED]`, never silently dropped or invented. Re-run
whenever new sections add citations.

---

### 5. Manuscript
The evolving manuscript file where scratchbook content is synthesized, structured, and written into formal academic prose — formatted and iterated according to the Journal Profile, shaped by the Manuscript Blueprint, and iterated until submission-ready.

**Key characteristics:**
- Follows the structure and formatting defined in the Journal Profile, and the paragraph-level shape set by the Manuscript Blueprint
- Built from Scratchbook content through synthesis and analytical writing
- Mirrors the Voice Profile and matches the technical depth set by Journal Profile Block C
- Goes through multiple named iterations (Draft 1, Draft 2, etc.)
- Each iteration should be meaningfully improved over the last

**When to create/update:** Once the Scratchbook has sufficient content for a section. Iterate repeatedly based on Iteration Log findings.

---

### 6. Iteration Log
A single structured record per draft iteration that holds **both** the evaluation of the draft and
what was actually done about it. Each entry assesses the manuscript across compliance, style
alignment, technical depth, and novelty fit — all benchmarked against the Journal Profile and
Voice Profile — then records the resolution of every priority action it raised.

**Structure of each entry:**
- Draft number and date
- **Sumber feedback / Feedback source:** self-review / previous Iteration Log entry / supervisor /
  co-author / peer reviewer / **Reviewer Simulation** (see below)
- Section 1: Compliance Evaluation — objective pass/fail per journal requirement (Block A)
- Section 2: Style Alignment Assessment — qualitative comparison against the Voice Profile (plus
  any journal-specific delta noted in Journal Profile Block B)
- Section 3: Technical Depth Evaluation — judgment-based comparison against Block C
- Section 3b: Novelty Fit Evaluation — C/M/E scoring against the Block D threshold
- Section 4: Priority Action List — ranked list of what must be fixed before the next draft
- Section 5: Actions Taken / Deliberately Deferred — how each Priority Action was resolved, what
  was deferred and why, and what carries forward to the next iteration
- Section 6: Readiness Summary — honest assessment of whether the draft is ready to advance

Section 5 is filled after the revision work happens, in the same entry — not in a separate file.
This is what makes "did I ever fix that?" answerable by reading one entry.

**When to create/update:** One entry per draft iteration, created only when the user asks for it
(see the Stage 5 trigger rule). Section 5 is appended to that same entry as the revisions are made.

**Reviewer Simulation — optional extension:**
A mock peer-review pass Claude runs against a draft that already clears its own Iteration Log
entry, using the same four-category taxonomy the Rebuttal document uses (Technical /
Methodological / Conceptual / Strategic). Its target is different from the Iteration Log's own
evaluation sections: those check the manuscript against the Journal Profile's own recorded
requirements, while Reviewer Simulation asks what an outside reviewer who has *not* read the
Journal Profile would push back on — catching Strategic-category weaknesses (positioning,
framing, why-this-journal, why-now) that a compliance/style/depth/novelty checklist structurally
can't see because nothing in the Journal Profile encodes "does this feel important."

- **Trigger:** run only once the draft already has a passing Iteration Log entry — never as a
  substitute for Sections 1–3b, and never automatically (same ask-first rule as the Iteration Log
  itself).
- **Output:** 3–6 simulated reviewer comments, each tagged with one of the four categories, each
  written the way a real reviewer would phrase it (a criticism, not a checklist item) — appended
  to the current Iteration Log entry's Section 4 as its own subsection, not a new document.
- **What to watch for:** at least one Strategic-category comment should be attempted per pass —
  if every simulated comment lands as Technical or Methodological, the pass hasn't actually
  stepped outside the Journal Profile's own frame.

---

### 7. Cover Letter
The letter accompanying manuscript submission, asserting *fit* with the target journal — not
summarizing the abstract a second time. Editors reject on fit signals (scope match, why this
journal specifically, why the timing) as much as on content.

**Pulled from:**
- Journal Profile Block A — editor name if known, journal scope statement to address directly
- Journal Profile Block D — the novelty threshold this manuscript clears, stated as a fit claim
  ("this work reports first-quantified X, consistent with [Journal]'s emphasis on empirical
  novelty") rather than restated as a number
- The Idea Canvas's contribution statement (via the handoff manifest, if ARTi-idea was used) —
  the one-sentence claim of what this paper contributes, reused here rather than re-derived

**Verification rule:** before finalizing, check that the letter argues fit — it should be possible
to point to a specific sentence that connects this manuscript to something this journal
specifically publishes or has stated it wants, not just a sentence that restates what the paper is
about. A cover letter that would be equally valid for any journal in the field has failed its
one job.

**When to create/update:** Once, when the manuscript is submission-ready (after the final
Iteration Log entry shows no 🔴 Critical items outstanding). Revise only if resubmitting to a
different journal.

**File:** `submission\cover-letter_[journal-abbreviation].md`

---

### 8. Rebuttal / Response to Reviewers
One entry per reviewer comment received after peer review, tracking how each was addressed and
tying the resolution back to the specific manuscript change that resolved it.

**Structure:**
- One entry per individual reviewer comment (not per reviewer, not per review round as a whole —
  each distinct point gets its own entry so nothing is answered by proxy)
- Each entry tagged with exactly one category: **Technical** (a specific methodological or data
  error), **Methodological** (the approach itself is questioned), **Conceptual** (the framing or
  interpretation is questioned), or **Strategic** (positioning, significance, or fit is
  questioned) — the same four-category taxonomy Reviewer Simulation uses
- Each entry cross-links to the Iteration Log entry that made the resolving change, so "did we
  actually fix what the reviewer asked" is answerable by following one link rather than
  re-reading the whole revised manuscript

**When to create/update:** One document per review round, opened when reviewer comments arrive.
Each comment gets an entry as it's addressed; entries accumulate across rounds if the journal
requires more than one revision cycle.

**File:** `submission\rebuttal_[journal-abbreviation]_round[N].md`

---

### 9. Publication Growth Log
A light-touch, post-acceptance document that closes the loop back into the next idea — the one
document in this skill written after the paper is done, not before or during.

**Contents:**
- Post-acceptance visibility checklist: DOI registered, ORCID linked, institutional/subject
  repository archiving done (green OA where the publisher allows it)
- **"What did this paper's Limitations section leave on the table?"** — a direct prompt Claude
  asks the researcher once acceptance is confirmed, reviewing the Manuscript's own Limitations
  paragraph (and any Reviewer Simulation or real-reviewer Strategic-category comments that were
  deferred rather than resolved) for concrete follow-up directions
- The answer is not just recorded here — it seeds a new **Research Idea Bank** entry via
  `idea-bank add` (ARTi-idea's persistent cross-project store, `~/.arti/memory/research-idea-bank.md`),
  so the leftover thread surfaces automatically the next time a Gap Map is started rather than
  being re-discovered from memory

**When to create/update:** Once, triggered by the researcher confirming acceptance — never
speculatively before that. The Research Idea Bank write is a single entry, done at the same time.

**File:** `submission\growth-log.md`

---

## Workflow Overview

```
[Voice Profile] ─────────┐
(once per researcher,    │
 reused across projects) │
                          ↓
[Journal Profile] → [Manuscript Blueprint] → [Scratchbook] → [Manuscript Draft 1]
        ↑                                                              ↓
  [Example Articles]                                       [Iteration Log Entry 1]
  (single-pass C + D                                        (evaluation + resolution,
   extraction)                                             + optional Reviewer Simulation)
                                                                        ↓
                                                             [Manuscript Draft 2] → ... → [Manuscript Draft N]
                                                                                                    ↓
                                                                                          [Cover Letter] → [Submitted]
                                                                                                    ↓
                                                                            [Rebuttal] ←── [Reviewer Comments]
                                                                                    ↓
                                                                              [Accepted]
                                                                                    ↓
                                                                     [Publication Growth Log]
                                                                                    ↓
                                                              [new Idea Bank entry — back into ARTi-idea]
```

The **core iteration loop** runs between:
Manuscript Draft → Iteration Log → Next Draft

The **outer loop** — the one that makes ARTi a loop rather than a pipeline — runs between:
Publication Growth Log → Idea Bank → next Gap Map (ARTi-idea)

---

## Claude's Role at Each Stage

### Stage 0: Voice Profile (once per researcher, reused across projects)

Run this stage only if the researcher has no Voice Profile yet in `~/.arti/voice-profiles/`, or if
they explicitly say their writing style has shifted. Otherwise skip straight to Stage 1 — read the
existing Voice Profile file, don't re-derive it.

**Selection step — run before choosing a path or reusing a profile.** Read (or create, if missing)
`~/.arti/voice-profiles/00-INDEX.md`, the flat catalog of every existing profile. If it lists more
than one profile, ask the researcher which one is in effect for this project before proceeding —
do not guess or default to the most recent. Record the choice in this project's Journal Profile
Block B pointer line, alongside the existing "which Voice Profile file is in effect" note. If the
catalog lists none yet, proceed to build one (Path A, B, or C below) and add its row to the catalog
once written.

**Path A — extracted from the researcher's own papers:**

Ask for 3–5 of the researcher's own first-author papers (any journal — this is about how *they*
write, not what one journal expects). For each paper, extract, in one reading pass:

*Title analysis:*
- Word count and structural pattern (record the formula, e.g., "[Material]-enabled [Property] for [Application]")
- Whether the key finding or novelty is stated explicitly in the title or implied
- Use of punctuation, colons, or subtitles

*Abstract analysis:*
- Sentence count per component (background, objective, methods, results, conclusion)
- Dominant tense per component
- Active vs. passive voice preference
- How key results are quantified (specific numbers vs. qualitative statements)
- Total word count

*Voice and tone:*
- Overall register (formal vs. semi-formal)
- Passive vs. active voice ratio across sections
- Hedging language patterns — list the specific phrases used (e.g., "suggests," "indicates," "demonstrates," "was found to," "it is proposed that")
- How claims are qualified or strengthened

*Section-level patterns:*
- Introduction: paragraph count, how the research gap is stated, how the objective is introduced
- Methods: level of procedural detail, how instruments are cited, tense consistency
- Results/Discussion: how figures are introduced, how literature comparisons are framed, how contradictory results are handled
- Conclusion: paragraph count, whether future work is included, how contribution is stated

*Vocabulary and terminology:*
- Field-specific preferred terms
- How chemical names, formulas, and units are written
- When abbreviations are introduced and how frequently used

*In-text citation style:*
- Narrative vs. parenthetical citation preference
- Typical number of references per claim
- Whether recent or seminal papers are favored

Then run one synthesis pass across all papers into a single consensus Voice Profile: note
dimensions where the researcher is consistent vs. variable, flag any pattern that appears in only
one paper as a possible one-off rather than a true habit, and write the result to
`~/.arti/voice-profiles/<voice-slug>.md`.

**Path B — supplied ready-made (e.g. `gtmk-voice`):**
Record a thin pointer file at the same location instead of re-extracting: which existing style
skill or profile this points to, and the date the researcher last confirmed it still matches their
writing. Do not run Path A's extraction over papers that skill was already built from.

**Path C — generalized multi-file corpus, built from a single example article:**
Use this path when the researcher wants a rich, `gtmk-voice`-style reference corpus — not a single
flat template file, and not a pointer to somebody else's style skill — built from their own writing
in whatever field they're in, from just one example article (rather than Path A's 3–5). Modeled
directly on the `gtmk-voice` skill's own decomposition, generalized so it transfers to any field:

1. Ask the researcher for one example article (their own, or one they want to emulate) and a
   **descriptive slug** for the resulting profile — prompt for this explicitly; never default to a
   placeholder like "writing-style-1". The slug becomes the folder name.
2. From that single article, extract the same registers `gtmk-voice` documents, generalized rather
   than left field-specific: verb/noun/adjective/adverb registers with a preferred-vs-avoided list
   (no domain-noun lexicon section, since one article can't establish a stable domain vocabulary —
   flag this gap explicitly rather than inventing one); verbatim phrase banks by rhetorical
   function; the commitment/hedging ladder; paragraph-flow move-sequences per section; title/
   abstract formulas; the non-native-English or other signature fingerprint, if present; and a
   condensed copy-paste prompt block distilling all of the above.
3. Write the result to `~/.arti/voice-profiles/<slug>/`, as a folder (not a flat file — the folder
   structure is the point of "same structure but generalized"), containing:
   `00-INDEX.md`, `01-lexicon.md`, `02-phrases.md`, `03-hedging.md`, `04-paragraph-flow.md`,
   `05-abstract-title.md`, `06-signature-notes.md`, `07-PROMPT-BLOCK.md`.
4. Because this is built from one source article rather than 3–5, `00-INDEX.md` must state the
   single-source provenance explicitly and flag the whole extraction as **provisional** until
   reconfirmed against a second sample — do not present it with the same confidence as a Path A or
   an established Path C profile built from more than one source.
5. Add a row for the new profile to `~/.arti/voice-profiles/00-INDEX.md` (the catalog read by the
   selection step above).

**File:** `~/.arti/voice-profiles/<voice-slug>.md` (Path A/B) or `~/.arti/voice-profiles/<slug>/` (Path C)

---

### Stage 1: Journal Profile

**Block A — Administrative Requirements:**
- Help the user identify and fill in all journal requirement fields
- Search for or analyze provided journal guidelines
- Flag any unusual requirements that will affect manuscript structure

**Block B — pointer only:**
Record which Voice Profile file is in effect for this project. While reading the journal's example
articles for Blocks C and D (below), note only the deltas that actually differ from that Voice
Profile — e.g., this journal's citation format, or a section-length norm the researcher's own
papers don't share. Do not re-extract the full style profile here; that work now lives in Stage 0.

**Blocks C, D — Single-Pass Extraction Protocol:**

Example papers are read **once each**. For every paper, Claude extracts technical depth and
novelty in the same reading pass, then runs **one synthesis pass** across all papers to produce
Blocks C and D. Do not run separate protocols over the same paper set — the output is identical
and the reading cost is doubled.

**How many papers:** 5–8, **inclusive of the 2–3 already read in ARTi-idea Stage 5**. Those papers
count toward the total; do not re-read them from scratch — extend what was already extracted.

#### Pass 1 — Per paper (one reading, two profiles)

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

#### Pass 2 — Synthesis across all papers

Run once, after every paper has been through Pass 1:

*For Block C:*
1. Synthesize a consensus Technical Depth Profile across all articles
2. Note where papers vary in technical rigor
3. Flag any technique or analysis type appearing in most papers that the user has not yet addressed
4. Produce a completed Block C ready to paste into the Journal Profile

*For Block D:*
1. Complete the Novelty Scores of Example Articles table
2. Derive the Journal Novelty Threshold: record the range and typical minimum for each dimension,
   identify which dimension(s) the journal weights most heavily, state the minimum composite label
   the journal accepts, and note whether any dimension can be low if compensated by another
3. Note which novelty dimension is most critical for this journal
4. Produce a completed Block D (threshold section only) ready to paste into the Journal Profile

*Manuscript novelty fit (filled per draft, not at creation):*
When producing an Iteration Log entry, Claude must also update Block D's
"Your Manuscript's Novelty Fit" section by scoring the current draft's C/M/E
against the journal's threshold. If any dimension falls below the threshold,
flag it as 🔴 Critical in the Iteration Log Priority Action List.

**If ARTi-idea was used:**
- The Stage 5 light novelty threshold for this journal is **extended, not re-derived from zero**.
  Start from the recorded light threshold and deepen it with the additional papers.
- The 2–3 papers already read in Stage 5 **count toward the 5–8**. Only the remaining papers need
  a fresh Pass 1.
- Import the confirmed C/M/E scores from the Idea Canvas directly into Block D's
  "Your Manuscript's Novelty Fit" table. Use these as the starting scores for Draft 1.
  Update the scores if the manuscript content changes the novelty profile during drafting.

---

### Stage 2: Manuscript Blueprint

Run once Journal Profile Blocks A, C, D and the Voice Profile are all in place, before Scratchbook
population starts.

- From Journal Profile Block C and the Voice Profile's section-level patterns, derive a
  paragraph-level outline: how many paragraphs before the Introduction's gap statement, where the
  objective sentence sits, how many paragraphs per characterization technique in
  Results/Discussion, whether Conclusion future-work gets its own paragraph
- If ARTi-idea was used, pull the confirmed C/M/E contribution score from the Idea Canvas (via the
  handoff manifest) and mark which paragraph is responsible for carrying the novelty claim — the
  Introduction paragraph that frames the conceptual contribution, the Results/Discussion
  subsection that carries the empirical claim
- Output a paragraph-level outline per section — not prose, not a generic IMRaD skeleton. Write it
  to `writing\manuscript-blueprint.md`
- Revisit only if the target journal changes, or if Scratchbook population reveals the manuscript
  needs a structurally different shape than planned

---

### Stage 3: Scratchbook Population
- Help the user dump content into the correct section
- Suggest which section a finding or reference belongs to
- Ask probing questions to help the user articulate findings
- Do NOT synthesize or polish the raw dumps — preserve their raw, unfiltered nature
- Identify gaps: sections with insufficient content to draft from
- Do NOT revise or edit the manuscript at this stage — scratchbook population and manuscript drafting are strictly separate stages
- After any substantive Scratchbook edit, update that section's `**Argumen saat ini:**` line in the
  same turn — a short synthesis sentence or two of the section's current argument, not a copy of
  the raw dump. This is the one place synthesis is allowed at this stage; keep it brief. If an edit
  doesn't change the substance of a section's argument (e.g., a reference added to
  `## Unassigned Literature`), the line needs no matching edit.

**Default Density and Fidelity Rules (always apply unless user says otherwise):**
- **Maximize extraction:** When processing provided references, extract as much relevant information as possible from each source. Do not summarize sparsely — err on the side of over-inclusion. A thicker scratchbook produces a better manuscript.
- **Preserve all numbers:** Every specific numerical value in a reference (yields, efficiencies, potentials, concentrations, temperatures, particle sizes, band gaps, percentages, TON values, rate constants, etc.) must be recorded verbatim in the Scratchbook entry. Never replace a number with a qualitative description.
- **Duplicate across sections deliberately:** If a piece of information is relevant to more than one manuscript section, place it in all relevant sections — even if this creates apparent repetition. Duplication across sections is intentional and desirable; it ensures each section has the supporting material it needs when drafting begins.
- **Cross-source duplication strengthens arguments:** When multiple references report similar facts or values, record each source's version separately under the same section. Do not collapse them into one entry. Redundancy from multiple sources is evidence of consensus and should be preserved.

**Plagiarism Prevention at this stage:**
- Every entry must carry a source tag: `[OWN]` for the user's own data/observations, or `[LIT: Author, Year]` for literature
- If the user pastes text that appears copied verbatim from a source, flag it immediately and ask them to paraphrase it before it enters the Scratchbook
- Entries without source tags must be flagged as `[SOURCE NEEDED]` and resolved before drafting begins
- Remind the user: paraphrase literature at the point of entry — not at the drafting stage

**Claude's Own Extraction Rule (applies when Claude reads reference files directly):**
When Claude reads a source file and writes Scratchbook entries itself, it must NOT copy sentences from the source. Every Scratchbook entry written by Claude must be:
- **Rewritten in Claude's own words** — analyze the meaning, then express it independently
- **Faithful to all details** — rewriting does not mean omitting; numbers, conditions, units, and specific findings must all be preserved exactly
- **Structurally distinct from the original** — do not mirror the sentence structure of the source even if the words differ; true paraphrasing means independent reconstruction of the idea
- The test: if a Scratchbook entry could be found by a plagiarism checker as matching the source text, it must be rewritten before it enters the Scratchbook

**Hallucination Prevention at this stage:**
- Claude must never add citations, references, or factual claims to the Scratchbook that were not explicitly provided by the user
- If the user asks Claude to suggest supporting literature, Claude may search the web but must clearly label any suggested reference as `[UNVERIFIED — USER MUST CONFIRM]` and instruct the user to verify the actual source before accepting it

**Literature Feed Protocol:**
Literature can enter two ways: already ingested into `literature\library.md` (the normal path once
the Reference System above is in use — Claude runs `arti-lit library get --key KEY` to fetch the
row, no re-typing), or hand-typed in the standard input format below (the fallback, for a one-off
note that hasn't gone through the library yet). Either way:

1. **Receive** the literature entry — from a `library.md` row, or in the standard input format (see below)
2. **Identify** which Scratchbook section(s) the entry is relevant to
3. **Place** the relevant points under each identified section, tagged `[LIT: Author, Year]`
   - If relevant to multiple sections, place in all of them
4. **Check** for contradictions with existing Scratchbook entries in those sections
   - If a contradiction is found, add `[⚠️ CONTRADICTION: Author, Year vs. Author, Year — brief description]` inline, immediately below both conflicting entries
5. **Add** a `[CONNECTION: Author, Year → note]` tag inline, near the placed entry, explaining how this reference connects to the research
6. **Add** the full bibliographic details to `## Reference List` if not already present
7. **Update** the `**Argumen saat ini:**` line of each affected section if this entry changes that section's current argument or finding
8. **Report** to the user: which sections were updated, any contradictions found, and any fields missing from the input

**Standard Literature Input Format:**
```
---
LITERATURE ENTRY

Title: [Full paper title]
Authors: [Last name, First initial. et al. if many]
Journal: [Journal name]
Year: [YYYY]
DOI: [if available]

Key Findings:
- [Summary of finding 1]
- [Summary of finding 2]

Methods Used:
- [Relevant methods, materials, conditions]

Relevant Data/Values:
- [Specific numbers, peaks, efficiencies, conditions]

My Interpretation / Why This is Relevant:
- [Optional — your own thought on how this connects to your work]

Suggested Section: [Optional — your guess of where this belongs]
---
```

**Minimum viable input:** Authors, Year, Journal, DOI + bullet point notes.
Entries missing full bibliographic details get `export-only` or `abstract` read-status in
`literature\library.md` until completed — that column is the tracker now, not a free-text tag.

---

### Stage 4: Manuscript Drafting

**Project index cadence:** the first time this stage produces "Draft 1" content (not on later
revisions of the same draft), run `project upsert --stage "Drafting" --status "writing started"`
for this project's row. This is the phase boundary ARTi-idea's handoff row left open; skipping it
is why the dashboard can show a project stuck at "Handed off" indefinitely. Consider whether
`--summary` needs updating too (e.g. a voice-implementation pass or new section added).

- Skim the `**Argumen saat ini:**` lines first for a quick orientation on each section's current
  argument, then go to the full dumps beneath them for the supporting material
- Transform Scratchbook content into formal academic prose, following the Manuscript Blueprint's
  paragraph-level shape for this journal
- Strictly follow Journal Profile Block A (structure and formatting)
- Mirror the project's Voice Profile, adjusted for any journal-specific delta noted in Journal
  Profile Block B
- Match technical depth consistent with Journal Profile Block C (Technical Depth Profile)
- Flag any content in the Scratchbook that is unclear or insufficient
- Label each output clearly as "Draft N"
- Before drafting, scan all `[⚠️ CONTRADICTION]` tags in the relevant section — note them for the Discussion
- Before drafting, check Block C — flag any characterization technique or analysis type that typical journal papers include but the Scratchbook does not yet address

**Concision is the default register, not a special pass.** Draft every section, and revise every
existing one, as dense and literature/evidence-rich as it can be while remaining correct: trim
elaboration, meta-commentary, and content already restated by an adjacent table or figure; never
touch citations or evidence. Concretely, on both a first draft and any later revision:
- Cut signposting sentences that only announce what a paragraph is about to do or just did
  ("Note that…", "It is worth noting…", "Firstly / secondly / thirdly" scaffolding, "This
  demonstrates that…" restated after the demonstration already reads that way).
- Cut parenthetical glosses and restrictive clauses that repeat a claim already made in the
  sentence, or that a cited source's name alone already implies.
- When a table or figure states something in full (a mapping, a list of properties, a set of
  values), do not also restate it prose-form nearby — point to the display item instead.
- **Don't elaborate without strong support (literature or evidence).** A claim, interpretation, or
  aside earns extra sentences only if it is carrying a citation, a statistic, or data from the
  Scratchbook — not because it sounds plausible or adds color. If a sentence would need to be
  written from general reasoning rather than a sourced claim, it is a candidate to cut, not expand;
  when the point genuinely needs saying and has no source, flag it (`[SOURCE NEEDED]` or
  `[CITATION NEEDED]`) rather than writing it up unsupported at length.
- Never cut a citation, a statistic, a `[DATA NEEDED]`/`[CITATION NEEDED]`/`[SOURCE NEEDED]` flag,
  or a substantive claim (a distinct piece of evidence, reasoning, or a stated limitation/trade-off)
  purely to shorten. If a sentence carries a citation or a number, treat everything in it as load-
  bearing by default and cut around it, not through it.
- After any concision pass, verify nothing evidentiary was lost: diff the citation set (author-year
  keys) between the before and after text and confirm it is unchanged, the way
  `references/review-checklist.md` Section J already requires for citation integrity generally.
- This is the default weighting for every draft and revision, independent of whether the user asks
  for a "compression pass" by name — write tight the first time rather than padding now and cutting
  later. **The one override:** if the user explicitly asks for elaboration, more detail, or a longer
  treatment of something, honor that request for the scope asked — it does not reopen the default
  elsewhere in the same draft.

**Plagiarism Prevention at this stage:**
- Write exclusively from the Scratchbook — never draft by rephrasing the original source text directly
- All literature from the Scratchbook must be fully paraphrased into original prose; do not reproduce sentence structures from the original paper even if the words differ
- Direct quotes are not acceptable in scientific manuscripts — if a Scratchbook entry contains a direct quote, rewrite it before including it in the draft
- Cite as you write — every claim derived from literature must carry its citation inline; never plan to add citations later
- Flag any Methods section content that appears reused from a prior paper — self-plagiarism is a violation
- Add a note at the end of each drafted section: *"Please review this section for unintended similarity to source texts before proceeding."*

**Hallucination Prevention at this stage:**
- Only cite references explicitly listed in the Scratchbook `## Reference List` — never generate or infer citations from memory
- If a claim requires a citation but no source is in the Scratchbook, insert `[CITATION NEEDED]` and notify the user
- Never invent numerical data, experimental results, or author names — flag missing values as `[DATA NEEDED — VERIFY FROM SOURCE]`
- Do not expand on a reference's content beyond what the user has provided in the Scratchbook

---

### Stage 4b: Submission Completion Plan

Fired when the researcher confirms study design is frozen — typically once Introduction and
Methods are drafted and everything downstream is execution rather than re-planning.

- **Precondition — confirm the Blueprint is complete, not just frozen.** Read the Manuscript
  Blueprint end-to-end. Every top-level section (Introduction, Materials & Methods, Results &
  Discussion, Conclusion) must carry an explicit figure/table decision — a specific display item
  or an explicit "no display items needed" call, never silence. If any section's decision is
  missing, **stop** and ask the researcher to decide it in the Blueprint's Revision Notes first; do
  not compile a Figures & Tables Inventory around a silent gap.
- Read `references/completion-plan-template.md` for the required Markdown structure.
- Compile once from `idea\research-design.md`, the Manuscript Blueprint, Journal Profile
  Blocks A/B, and the open `- [ ]` items in `memory\todo-list.md`.
- Content: data-collection schedule · analysis plan per hypothesis · full figure/table inventory
  (create / redraw / verify) · remaining manuscript sections · pre-submission checks (journal
  allowances, reference verification, IRB) · submission-package items.
- Write to `writing\completion-plan.md`, then render to `writing\completion-plan.pdf` via the
  shared Markdown→A4-PDF pipeline in `~/.arti/tools/arti-pdf/README.md` (no self-contained-HTML step —
  that pipeline already handles the print CSS).
- **Hand-maintained after creation, not regenerated.** It states the frozen full scope to
  submission-ready; `memory\todo-list.md` + `memory\status.md` remain the living session-to-session
  state (checklist and narrative respectively). Update the `.md` and re-render the `.pdf` only when
  scope genuinely changes — not every session.

---

### Stage 5: Iteration Log

**Trigger rule — IMPORTANT:**
Claude must NEVER create an Iteration Log entry automatically.
- Claude creates an Iteration Log entry ONLY when the user explicitly requests it (e.g., "evaluate my draft", "create an iteration log entry", "run an evaluation")
- At the end of each drafting or revision session, Claude must ask: *"Would you like me to create an Iteration Log entry for this draft?"*
- If the user says no, proceed without creating one
- Never assume an evaluation is wanted — always ask first

When an entry is requested, Claude must read `iteration-log-template.md` for the full report
structure and scoring guidance, then produce a structured entry.

**Feedback source (recorded at the top of every entry):**
State where the input for this iteration came from: self-review, the previous Iteration Log entry,
supervisor, co-author, peer reviewer, or Reviewer Simulation. External feedback enters the loop
through this field — an entry can be opened to record a supervisor's, reviewer's, or simulated
review's comments even when no fresh evaluation was run.

**Section 1 — Compliance Evaluation (objective):**
Check every field from Journal Profile Block A:
- Status: ✅ Met / ⚠️ Partial / ❌ Not Met
- Add a specific note for any non-Met item
- Report overall compliance score: X of Y requirements met

**Section 2 — Style Alignment Assessment (qualitative):**
Compare the manuscript against every dimension in the project's Voice Profile, plus any
journal-specific delta noted in Journal Profile Block B:
- Rating: ✅ Aligned / ⚠️ Partial / ❌ Misaligned
- Provide specific examples from the manuscript text to support each rating
- Note which style dimensions need the most attention

**Section 3 — Technical Depth Evaluation (judgmental):**
Compare the manuscript against every dimension in Journal Profile Block C:
- Rating: ✅ Sufficient / ⚠️ Needs strengthening / ❌ Missing
- For each gap, specify what is missing and why it matters for this journal
- Flag overclaimed results — claims not sufficiently supported by the data presented
- Flag underutilized data — results collected but not fully discussed or interpreted

**Section 3b — Novelty Fit Evaluation (against Block D):**
Compare the manuscript's actual novelty against the journal's threshold from Block D:
- Score the current draft on C, M, and E using the same rubric applied to example papers
- Compare each score against the journal's minimum threshold
- Rating per dimension: ✅ Meets threshold / ⚠️ Borderline / ❌ Below threshold
- If any dimension is ❌ Below threshold: this is automatically a 🔴 Critical item
- If borderline (⚠️): specify exactly how the framing or scope could be strengthened
  within the existing data — do not recommend collecting new data unless unavoidable
- Update Block D's "Your Manuscript's Novelty Fit" section with the scores from this evaluation

**Section 4 — Priority Action List:**
Synthesize all findings into a ranked action list:
- 🔴 Critical — must fix before advancing to next draft
- 🟡 Important — should fix before co-author review
- 🟢 Minor — polish before submission

**Section 5 — Actions Taken / Deliberately Deferred:**
Filled as the revision work happens, in this same entry:
- Record which Priority Actions were addressed and how
- Record which were deliberately deferred, and why
- Summarize what changed between this draft and the next
- Carry forward unresolved items to the next iteration's Priority Action List

**Section 6 — Readiness Summary:**
Honest one-paragraph assessment of the draft's current state and whether it is ready to advance to the next stage.

Evaluation still precedes revision: Sections 1–4 are completed before any revision begins, and
Section 5 is only filled once the revisions are actually made. Merging the two logs into one entry
does not merge the two acts.

**Reviewer Simulation (optional, run only after a passing Iteration Log entry):**
- Only after the current draft's Iteration Log entry shows no 🔴 Critical items, ask whether the
  researcher wants a Reviewer Simulation pass
- Produce 3–6 simulated reviewer comments, each tagged Technical / Methodological / Conceptual /
  Strategic, written as a reviewer would phrase a criticism — not as a checklist restatement of
  Sections 1–3b
- Deliberately look for at least one Strategic-category comment (positioning, significance, fit) —
  the category a Journal-Profile-benchmarked evaluation cannot generate on its own
- Append the result as a subsection of the current entry's Section 4, tagged with feedback source
  "Reviewer Simulation"

---

### Stage 6: Cover Letter

Run once the manuscript is submission-ready — the latest Iteration Log entry shows no 🔴 Critical
items outstanding.

- Pull Journal Profile Block A (editor name if known, scope statement to address) and Block D (the
  novelty threshold this manuscript clears, stated as a fit claim, not restated as a C/M/E number)
- If ARTi-idea was used, pull the Idea Canvas's contribution statement via the handoff manifest
  rather than re-deriving a summary of the abstract
- Verify the letter argues fit, not summary: check that a specific sentence connects this
  manuscript to something this journal specifically publishes or has stated it wants
- Write to `submission\cover-letter_[journal-abbreviation].md`

**Project index cadence:** once the researcher confirms the package was actually submitted to the
journal (not merely that the cover letter draft is done), run
`project upsert --stage "Submitted" --status "Under review"` (or the journal name if not already
set) for this project's row. Consider whether `--summary` needs updating too.

---

### Stage 7: Rebuttal / Response to Reviewers

Triggered when reviewer comments arrive after peer review — never speculatively before that.

- Open one entry per individual reviewer comment, not per reviewer and not per round as a whole
- Tag each entry with exactly one category: Technical / Methodological / Conceptual / Strategic
- As each comment is addressed, cross-link the entry to the Iteration Log entry that made the
  resolving manuscript change
- If a subsequent review round arrives, append new entries to the same document rather than
  starting a new one for the same journal submission
- Write to `submission\rebuttal_[journal-abbreviation]_round[N].md`

---

### Stage 8: Publication Growth Log

Triggered by the researcher confirming acceptance — never speculatively before that. This is the
only stage that runs after the paper is done, and the one that closes the loop back to ARTi-idea.

- Walk the post-acceptance visibility checklist: DOI registered, ORCID linked, repository archiving
  done where the publisher allows it
- Ask directly: *"What did this paper's Limitations section leave on the table?"* — review the
  Manuscript's own Limitations paragraph, plus any Strategic-category comments from Reviewer
  Simulation or real reviewers that were deliberately deferred rather than resolved, for concrete
  follow-up directions
- Record the answer in `submission\growth-log.md`, and in the same turn run `idea-bank add` so it
  surfaces automatically the next time a Gap Map is started

---

## File Naming Convention

All documents live in the project's `writing/` or `submission/` folder (the standard ARTi
paper-project boilerplate — see the `ARTi-setup` skill), except the Voice Profile, which is
cross-project and lives in `~/.arti/`.

| Document | Suggested Filename |
|---|---|
| Journal Profile | `writing\journal-profile_[journal-abbreviation].md` |
| Voice Profile | `~/.arti/voice-profiles/<voice-slug>.md` (Path A/B) or `~/.arti/voice-profiles/<slug>/` (Path C) |
| Voice Profile Catalog | `~/.arti/voice-profiles/00-INDEX.md` |
| Manuscript Blueprint | `writing\manuscript-blueprint.md` |
| Scratchbook | `writing\scratchbook.md` |
| Manuscript | `writing\manuscript_draft[N]_[date].md` |
| Iteration Log | `writing\iteration-log.md` |
| Cover Letter | `submission\cover-letter_[journal-abbreviation].md` |
| Rebuttal | `submission\rebuttal_[journal-abbreviation]_round[N].md` |
| Publication Growth Log | `submission\growth-log.md` |

---

## Key Principles

1. **Journal Profile first** — never start writing without knowing the target journal's requirements.
2. **Scratchbook before drafting** — gather and dump before synthesizing.
3. **Evaluate before revising, and record both in one place** — every draft is evaluated before the next revision begins, and every action taken on that evaluation is written back into the same Iteration Log entry that raised it. One event, one record.
4. **Iterate deliberately** — each draft must address specific, prioritized findings from the Iteration Log.
5. **Separate thinking from writing** — the Scratchbook is for thinking; the Manuscript is for writing.
6. **Source everything** — every claim in the Scratchbook and Manuscript must be traceable to a real, user-provided source.
7. **Paraphrase always** — direct quotes from literature are not acceptable in scientific writing. All literature must be rewritten in original prose.
8. **Never fabricate** — Claude must never generate citations, data, or claims from memory. Only what the user has explicitly provided in the Scratchbook is valid source material.
9. **Tags carry context** — every tag in the Scratchbook is persistent context for future sessions. Tags must never be removed unless the issue is resolved.
10. **Contradictions are assets** — flagged contradictions between sources are material for Discussion synthesis, not problems to hide.
11. **Technical gaps are early warnings** — if the Scratchbook lacks data that the Technical Depth Profile shows is expected, flag it before drafting — not after.
12. **Read each example paper once** — technical depth and novelty come out of the same reading pass. Separate passes over one paper produce the same profile at double the cost.
13. **Novelty below threshold is a desk-rejection risk** — if the manuscript's C/M/E score on any dimension falls below the journal's threshold (Block D), flag it as 🔴 Critical immediately. A well-written paper with insufficient novelty will be rejected before peer review. Novelty fit must be verified at Journal Profile creation and at every Iteration Log entry.
14. **Novelty fit problems are often framing problems** — before concluding that the research itself is insufficiently novel, check whether the Introduction and Discussion are framing the contribution strongly enough. A C3 finding written as a C2 contribution is a writing problem, not a research problem.
15. **Voice is the researcher's, style delta is the journal's** — a Voice Profile is built once per researcher and reused; only the journal-specific delta gets re-derived per project. Do not re-run full style extraction on a researcher who already has a Voice Profile.
16. **Blueprint before dumping** — the Manuscript Blueprint's paragraph-level shape exists so Scratchbook population has a target to fill, not so drafting invents structure from a blank page.
17. **A cover letter argues fit, not summary** — if it would be equally valid sent to any journal in the field, it has failed its one job.
18. **The loop doesn't end at acceptance** — the Publication Growth Log's job is to make sure what a paper's Limitations section left on the table doesn't just get forgotten; it becomes the next Research Idea Bank entry.
19. **Concise and evidence-dense is the default register, not an on-request pass** — trim elaboration, meta-commentary, and content already restated by an adjacent table or figure; never touch citations or evidence to shorten a section. Don't elaborate without strong support (literature or evidence) — extra sentences are earned by a citation, statistic, or Scratchbook data, not by sounding plausible. Apply this to every draft and every revision by default; elaborate only when the user explicitly asks, and only for the scope asked.

---

## Reference Files

- `section-guide.md` — Writing guidance for each manuscript section
- `review-checklist.md` — Self-review checklist for manuscript drafts
- `voice-profile-template.md` — Ready-to-use blank Voice Profile template
- `manuscript-blueprint-template.md` — Ready-to-use blank Manuscript Blueprint template
- `scratchbook-template.md` — Ready-to-use blank Scratchbook template (including the
  `Argumen saat ini` line per section)
- `journal-profile-template.md` — Ready-to-use blank Journal Profile template (Blocks A, C, D)
- `iteration-log-template.md` — Iteration Log entry template with scoring and resolution guidance,
  including the optional Reviewer Simulation subsection
- `completion-plan-template.md` — Stage 4b's `writing\completion-plan.md` Markdown structure and
  Blueprint-completeness precondition
- `cover-letter-template.md` — Ready-to-use blank Cover Letter template
- `rebuttal-template.md` — Ready-to-use blank Rebuttal / Response to Reviewers template
- `publication-growth-log-template.md` — Ready-to-use blank Publication Growth Log template

Read the relevant reference file before starting any stage.

**`arti-db` invocation** — every `project upsert`/`idea-bank add` command above runs as:
`"~/.arti/python/python.exe" "~/.arti/tools/arti-db/cli.py" <subcommand> ...` (Mac/Linux:
`~/.arti/python/bin/python3`). Each call prints one JSON object (`{"ok": true, ...}` or
`{"ok": false, "error": ...}`); see `~/.arti/tools/arti-db/README.md` for the full subcommand
surface. Never hand-edit `project-index.md` or `research-idea-bank.md` directly — both are
generated exports, overwritten on every write.

**Integration with ARTi-idea:**
If the researcher completed the ARTi-idea workflow before starting here, read the handoff manifest
(`idea\handoff.md`) first for the confirmed decisions — research question, working title,
C/M/E score, target journal, any open 🔴 flags — then read the source documents in `idea/`
directly for their content. There is no bundle to ingest; the manifest names which file feeds
which stage:

- `idea-canvas.md` → confirmed C/M/E scores into Block D "Your Manuscript's Novelty Fit"
  and into the Manuscript Blueprint's novelty-paragraph markers; final title and gap statement into
  the Manuscript's Title, Abstract framing, and Introduction; contribution statement into the
  Cover Letter
- `journal-target-sheet.md` → confirmed journal begins Block A; its light novelty
  threshold is the starting point Block D **extends** (not re-derives), and the 2–3 papers already
  read there count toward the 5–8
- `gap-map.md` → seeds the Scratchbook Introduction section
- `research-design.md` → seeds the Scratchbook Methods and Results sections
- `~/.arti/memory/researcher-profile.md` → context for writing support and technical gap flags
- `~/.arti/voice-profiles/<voice-slug>.md` (or `<slug>/` for a Path C multi-file corpus) → Stage 0 Voice Profile, if the researcher already has one
- `~/.arti/voice-profiles/00-INDEX.md` → catalog of every existing Voice Profile, read by Stage 0's selection step when more than one exists
- `~/.arti/memory/research-idea-bank.md` → destination for the Publication Growth Log's closing entry, at Stage 8
