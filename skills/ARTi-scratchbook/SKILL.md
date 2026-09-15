---
name: ARTi-scratchbook
description: >
  Creating and populating a Scratchbook — the section-organized raw-material staging document
  writers fill before drafting, where findings, data interpretations, and supporting literature get
  dumped under their manuscript sections without synthesis or polish. Use this skill for: creating a
  fresh Scratchbook from the template, feeding literature or own findings into it (already in
  `arti-lit` or hand-typed), the `Argumen saat ini` discipline, the full tagging system
  (`[OWN]`/`[LIT: key]`/`[⚠️ CONTRADICTION]`/etc.), contradiction and density audits, and — for a
  large corpus (20-30+ sources) — a session-chunking plan so population doesn't collapse into one
  fat, unreliable session. Triggers include: "populate the scratchbook", "add this paper to the
  scratchbook", "dump these findings", "plan a scratchbook population session", "what's left to
  sweep into the scratchbook", or any request to extract literature/findings into a Scratchbook —
  standalone, not only when reached via `ARTi-writing`. Do NOT use this skill for: drafting
  manuscript prose from a finished Scratchbook (`ARTi-writing` Stage 4); literature CRUD, DOI
  dedup, or fulltext ingestion mechanics (`ARTi-ref`, which this skill calls into); building the
  Manuscript Blueprint that Scratchbook population reads as a precondition (`ARTi-writing` Stage 2).
---

# ARTi-scratchbook Skill

One job: create and populate a Scratchbook, from a small corpus (a handful of papers, no chunking
needed) to a large one (20-30+ sources, needs a session-chunking plan). Carved out of
`ARTi-writing` for the same reason `ARTi-ref` was carved out of both `ARTi-writing` and
`ARTi-idea` — the Scratchbook's own mechanics (tagging system, dump-not-synthesize discipline,
extraction rules) were fully self-contained inside a much larger workflow skill, referenced but not
required by any stage before it and consumed whole by only one stage after it. Keeping it inside
`ARTi-writing` meant every researcher who just wanted "help me dump this paper into my scratchbook"
had to route through journal-profile and blueprint framing that had nothing to do with the request.

## What the Scratchbook is

A section-organized working document used in the early stage of research writing, where the writer
freely dumps all raw findings, data interpretations, and supporting literature under their
respective manuscript sections — without the pressure of synthesizing, structuring, or polishing
the prose. It bridges raw research data and the final manuscript, letting material accumulate
before committing to analytical narrative.

**Key characteristics:**
- Organized by manuscript sections (e.g., Introduction, Methods, XRD Analysis, etc.)
- Each section opens with a one-to-three-sentence **`Argumen saat ini`** (current argument) line —
  the condensed state of that section's argument, sitting directly above its own raw material
- Contains unfiltered findings, observations, and literature citations tagged inline
- No expectation of flow, coherence, or formal writing style below the `Argumen saat ini` line
- Full bibliographic detail lives in `literature\library.md` (owned by `ARTi-ref`), not here — the
  Scratchbook's own `## Reference List` is a per-claim key mapping only

**When to create/update:** After the Journal Profile and Manuscript Blueprint are ready (both
`ARTi-writing` Stage 0-2 outputs — read the Blueprint first, it names which source file feeds which
row). Populate section by section as data and literature are gathered. Update freely — this
document is never "done" until the manuscript is complete.

**Structure** (fresh copy: `references/scratchbook-template.md`):
```
## [Manuscript Section] (e.g., Introduction / XRD Analysis / Methods)
**Argumen saat ini:** [1–3 sentences — the current state of this section's argument or
finding. Not a dump, not raw tags, not full citations.]

[Raw dumps — findings, observations, literature notes tagged inline]

... repeat for all manuscript sections ...

## Unassigned Literature
[References collected but not yet placed in a section]

## Reference List
[Per-claim key mapping only — full bibliographic detail lives in literature\library.md]
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
  a full entry in `literature\library.md` (call `ARTi-ref`'s `library get` to check)
- Inline tags `[LIT: Author, Year]` must match a key present in `literature\library.md`
- Tag resolution is proactive, not reactive: the moment a new `[LIT: key]` tag is written with no
  matching `sources` row yet, call `ARTi-ref`'s `library add` for that key in the same turn
  (composing the citation from what's known), instead of leaving it to be caught later as an
  unresolved `[LIT:]` tag
- References not yet assigned to a section go to `## Unassigned Literature` first, then moved to
  the appropriate section as the Scratchbook develops

**`[LIT: key]` tag regeneration** — a Scratchbook's tags are what trigger `writing\references.md`
regeneration: grep the Scratchbook for `[LIT: key]` tags (cheap, targeted) to get the key list in
appearance order, then call `ARTi-ref`'s `refs generate --keys KEY,KEY,... --order
appearance|alpha --project PATH`. `--order appearance` preserves tag order; `--order alpha` sorts by
key shape — pick per the project's Journal Profile Block B. Any key in the result's `unresolved`
list is reported as `[CITATION NEEDED]`, never silently dropped or invented. Re-run whenever new
sections add citations. (Layers 1/2 of the wider Reference System — `search-log.md` and
`library.md` — stay `ARTi-writing`'s and `ARTi-ref`'s concern respectively; this skill only owns the
tag-driven Layer-3 trigger.)

## Standard population workflow

- Help the researcher dump content into the correct section
- Suggest which section a finding or reference belongs to
- Ask probing questions to help articulate findings
- Do NOT synthesize or polish the raw dumps — preserve their raw, unfiltered nature
- Identify gaps: sections with insufficient content to draft from
- Do NOT revise or edit the manuscript at this stage — Scratchbook population and manuscript
  drafting are strictly separate (manuscript drafting is `ARTi-writing` Stage 4, not this skill)
- After any substantive Scratchbook edit, update that section's `**Argumen saat ini:**` line in the
  same turn — a short synthesis sentence or two of the section's current argument, not a copy of
  the raw dump. This is the one place synthesis is allowed at this stage; keep it brief. If an edit
  doesn't change the substance of a section's argument (e.g., a reference added to
  `## Unassigned Literature`), the line needs no matching edit.

**Default Density and Fidelity Rules (always apply unless the researcher says otherwise):**
- **Maximize extraction:** when processing provided references, extract as much relevant
  information as possible from each source. Do not summarize sparsely — err on the side of
  over-inclusion. A thicker scratchbook produces a better manuscript.
- **Preserve all numbers:** every specific numerical value in a reference (yields, efficiencies,
  potentials, concentrations, temperatures, particle sizes, band gaps, percentages, TON values,
  rate constants, etc.) must be recorded verbatim in the Scratchbook entry. Never replace a number
  with a qualitative description.
- **Duplicate across sections deliberately:** if a piece of information is relevant to more than
  one manuscript section, place it in all relevant sections — even if this creates apparent
  repetition. Duplication across sections is intentional and desirable; it ensures each section has
  the supporting material it needs when drafting begins.
- **Cross-source duplication strengthens arguments:** when multiple references report similar facts
  or values, record each source's version separately under the same section. Do not collapse them
  into one entry. Redundancy from multiple sources is evidence of consensus and should be
  preserved.

**Plagiarism Prevention:**
- Every entry must carry a source tag: `[OWN]` for the researcher's own data/observations, or
  `[LIT: Author, Year]` for literature
- If pasted text appears copied verbatim from a source, flag it immediately and ask for paraphrase
  before it enters the Scratchbook
- Entries without source tags must be flagged as `[SOURCE NEEDED]` and resolved before drafting
  begins
- Paraphrase literature at the point of entry — not at the drafting stage

**Extraction Rule (applies when Claude reads reference files directly):**
When Claude reads a source file and writes Scratchbook entries itself, it must NOT copy sentences
from the source. Every entry written this way must be:
- **Rewritten in Claude's own words** — analyze the meaning, then express it independently
- **Faithful to all details** — rewriting does not mean omitting; numbers, conditions, units, and
  specific findings must all be preserved exactly
- **Structurally distinct from the original** — do not mirror the sentence structure of the source
  even if the words differ; true paraphrasing means independent reconstruction of the idea
- The test: if an entry could be found by a plagiarism checker as matching the source text, it must
  be rewritten before it enters the Scratchbook

**Hallucination Prevention:**
- Never add citations, references, or factual claims to the Scratchbook that were not explicitly
  provided by the researcher
- If asked to suggest supporting literature, Claude may search the web but must clearly label any
  suggested reference as `[UNVERIFIED — USER MUST CONFIRM]` and instruct the researcher to verify
  the actual source before accepting it

**Literature Feed Protocol:**
Literature can enter two ways: already ingested into `literature\library.md` (call `ARTi-ref`'s
`library get --key KEY` to fetch the row, no re-typing — bare `[LIT: Author, Year]` tags stay
valid), or hand-typed in the standard input format below (for a one-off note that hasn't gone
through the library yet). Either way:

1. **Receive** the literature entry — from a `library.md` row, or in the standard input format
2. **Identify** which Scratchbook section(s) the entry is relevant to
3. **Place** the relevant points under each identified section, tagged `[LIT: Author, Year]`
   - If relevant to multiple sections, place in all of them
   - If this tag's key has no matching `sources` row yet, call `ARTi-ref`'s `library add` for that
     key in the same turn (composing the citation from what's known) rather than leaving it to be
     caught later as an unresolved tag
4. **Check** for contradictions with existing Scratchbook entries in those sections by re-reading
   them
   - If found, add `[⚠️ CONTRADICTION: Author, Year vs. Author, Year — brief description]` inline,
     immediately below both conflicting entries
5. **Add** a `[CONNECTION: Author, Year → note]` tag inline, near the placed entry, explaining how
   this reference connects to the research
6. **Add** the full bibliographic details to `## Reference List` if not already present
7. **Update** the `**Argumen saat ini:**` line of each affected section if this entry changes that
   section's current argument or finding
8. **Report** back: which sections were updated, any contradictions found, and any fields missing
   from the input

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

**Minimum viable input:** Authors, Year, Journal, DOI + bullet point notes. Entries missing full
bibliographic details get `export-only` or `abstract` read-status in `literature\library.md` until
completed — that column is the tracker now, not a free-text tag.

Reusable copy-paste versions of the above, keyed to a specific project's Blueprint sections and
source files, live in `references/entry-prompt-templates.md` (Templates A-J) — read that file
before starting a population session rather than reconstructing each prompt shape from scratch.

## Large-corpus session-chunking

For a small corpus, the workflow above runs directly, session by session, with no separate plan
needed. For a large corpus (as a rule of thumb, dense enough that one sweep would mean reading
15-20+ full papers in a single turn), chunk into multiple sessions instead — a fat session degrades
the two things population depends on most:
- **Cross-entry contradiction-checking** gets less reliable the more material is already in a
  section when a new entry is checked against it — easier to catch a conflict between 6 entries
  than between 30.
- **`Argumen saat ini` fidelity** — the line is supposed to be re-synthesized from the section's
  *current* full content after every substantive edit; batching many edits into one pass makes this
  an end-of-batch afterthought instead of the tight per-edit discipline above requires.

**Chunking axes** (apply as many as the corpus structure supports):
1. **By source cost** — structural/project-doc population (cheap, no fulltext reading) before
   fulltext extraction (expensive, one full paper per entry)
2. **By corpus cluster** (however the project's own gap/theme map divides sources) — sources within
   one cluster are more likely to contradict/corroborate *each other* than sources in a different
   cluster, so scoping a session's contradiction-checking to one cluster is both cheaper and more
   accurate
3. **By sub-camp within a cluster**, if the project's own analysis already identifies factions
   likely to conflict — these benefit most from being read close together within a session

**Default batch-size ceiling: 5 fulltext papers per session.** A "sweep everything" instruction is
a checklist to page through at this ceiling, not a single invocation.

**Session-boundary checklist** — end every fulltext-processing session with:
1. A density audit (below), scoped to just the section(s) touched this session
2. Update the project's progress tracker (below) — mark each processed key's status, note any
   contradiction flagged, note which sections its content touched
3. A one-line note of exactly which cluster/keys remain, so the next session's cold start knows
   where to resume without re-reading this session's transcript

**Ordering rule:** structural/cheap population first, expensive fulltext reads by cluster next, a
dedicated targeted cross-cluster contradiction re-check as a late pass (once cross-cluster overlaps
are known — e.g. from a citation-chase or the project's own corpus map), and synthesis sections
(Future Work, Conclusion) written last, since they summarize across the whole corpus and would need
rewriting anyway if drafted before the sweep finishes.

**Audits, run on demand or at session boundaries:**
- **Density/gap audit** — for a given section, report the planned paragraph count vs. what current
  raw material could actually support, which sub-claims have no `[LIT:]`/`[OWN]` entry yet (flag
  each `[SOURCE NEEDED]` in the Scratchbook itself, not just in the report), and whether the
  project's Technical Depth Profile flags a technique typical for this row that's still missing.
- **Contradiction/consistency check** — check a specific entry against everything currently in a
  section, adding `[⚠️ CONTRADICTION]` inline near both entries if found, without resolving it (that
  stays for Discussion synthesis).

**Per-source progress tracker (single source of truth):** a large-corpus population plan needs a
tracker so "which source has and hasn't been populated" never requires re-reading the Scratchbook
itself to answer. Blank column structure: `references/progress-tracker-template.md`; a filled
instance is project-specific (e.g. `memory/memories/scratchbook-population-progress.md` in a
project using this project's memory convention).

- **Before extracting any source, check its tracker row first.** If already marked swept, stop and
  tell the researcher rather than silently re-extracting — this avoids duplicate entries and wasted
  reading.
- **The tracker update happens in the same turn as the extraction, never deferred to session-end** —
  one key swept = one tracker-row edit, immediately, the same discipline `Argumen saat ini` already
  requires. A session-boundary checklist is a batch-level audit *on top of* this, not a substitute.
- **Status vocabulary is explicit and exhaustive per row:** ⬜ not started / ✅ swept / ⚠️ swept with
  contradiction flagged / ❌ export-only or scavenger-citation only (abstract-only source, never
  gets a full extraction pass). No source may sit in an ambiguous state.
- **When asked "what's left" or "what's done," answer from the tracker file directly** (it's
  designed to be read standalone), not by re-deriving status from the Scratchbook's raw content.

## Not this skill

- **Drafting manuscript prose** — that's `ARTi-writing` Stage 4, which reads the finished
  Scratchbook but doesn't populate it. Once every section this skill touches has real content, hand
  off back to `ARTi-writing`.
- **Literature library CRUD, DOI dedup, or fulltext ingestion mechanics** — `ARTi-ref` owns
  `arti-lit` CRUD and `arti-pdf-ingest`; this skill calls into it (`library get`/`add`, `refs
  generate`) exactly as described above, never reimplementing the mechanics.
- **Building the Manuscript Blueprint** — `ARTi-writing` Stage 2, a precondition read at the start
  of Scratchbook population, not rebuilt here.
- **Search-log logging (Reference System Layer 1) or the canonical library (Layer 2)** — both stay
  `ARTi-writing`'s (Layer 1) and `ARTi-ref`'s (Layer 2) concern; this skill's only Reference-System
  responsibility is the tag-driven Layer-3 (`references.md`) regeneration trigger above.

## Reference Files

- `references/scratchbook-template.md` — ready-to-use blank Scratchbook template (including the
  `Argumen saat ini` line per section)
- `references/pacing-plan-template.md` — blank session-chunking table + session-boundary checklist,
  for a large-corpus population plan
- `references/progress-tracker-template.md` — blank per-source progress-tracker column structure
- `references/entry-prompt-templates.md` — reusable copy-paste prompt templates (A-J) for every
  population scenario (literature entry in/not-in library, own finding, populate-from-project-docs,
  contradiction check, density audit, `Argumen saat ini` refresh, figure/table integration,
  single-file fulltext bulk extraction, batch-corpus sweep)

## Handoff back to ARTi-writing

Once every Scratchbook section this population effort targeted has real, `Argumen saat ini`-backed
content and `## Unassigned Literature` is empty (or deliberately parked), population for that scope
is done. Manuscript drafting itself — synthesizing this raw material into formal prose — is
`ARTi-writing` Stage 4; that skill picks up from here.

## Change log
- 2026-09-15 — created, extracting Core Document #4 and Stage 3 out of `ARTi-writing` (which had
  them fully self-contained, referenced but not required by any earlier stage), plus new
  large-corpus session-chunking guidance generalized from a working project's own workflow/tracker
  files. Mirrors `ARTi-ref`'s extraction precedent.
