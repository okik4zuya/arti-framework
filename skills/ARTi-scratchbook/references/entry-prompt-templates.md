# Scratchbook Population — Reusable Entry-Prompt Templates (A-J)

> Copy-paste templates for the standard population workflow's iteration loop. Each fills one gap
> the generic protocol leaves to be reconstructed by hand each time — a specific Blueprint row,
> this project's specific source files, this project's tag vocabulary. Not a new document type;
> all output still lands in the project's `writing/scratchbook.md` under this skill's own structure
> and rules.
>
> Placeholders in `[brackets]` are filled from the calling project's own "Project parameters"
> block — see the pacing-plan-template's companion project file, or wherever this project records
> its Blueprint row names, source-of-truth file paths, and tag vocabulary. This file itself stays
> the single copy of the template text; don't duplicate it per project.

---

## How to pick a template

| Situation | Use |
|---|---|
| A new paper's findings to add (already in `arti-lit`) | [A](#a--literature-entry-already-in-library) |
| A new paper's findings to add (not yet in `arti-lit`) | [B](#b--literature-entry-not-yet-in-library) |
| Your own reasoning, interpretation, or a synthesis claim to record | [C](#c--own-finding--interpretation) |
| Pull a Blueprint row's material from project docs already on disk | [D](#d--populate-a-blueprint-row-from-existing-project-documents) |
| Check a new entry against what's already in a section | [E](#e--contradiction--consistency-check) |
| A section feels thin — is it draft-ready? | [F](#f--section-density--gap-audit) |
| A section changed and `Argumen saat ini` needs refreshing | [G](#g--refresh-argumen-saat-ini) |
| Wire a figure/table into its Results row | [H](#h--figuretable-integration) |
| Extract everything from one already-ingested fulltext `.md` in one pass | [I](#i--bulk-extraction-from-one-fulltext-file) |
| Sweep the whole remaining fulltext-registered corpus into the Scratchbook | [J](#j--batch-sweep-of-the-fulltext-registered-corpus) |

---

## A — Literature entry (already in library)

Use when the paper is already registered in `arti-lit` (check with `library get --key KEY` if
unsure — naming a reference is a retrieval trigger, never answer from memory of the paper).

```
Add [KEY] to the Scratchbook.

Target section(s): [Blueprint row name — or "let Claude decide" if unsure]

Focus (optional — omit to extract broadly):
- [specific finding / number / mechanism claim to prioritize]

Note any contradiction against what's already in the target section(s).
```

Claude then: runs `library get --key KEY`, places extracted points under the named section(s)
tagged `[LIT: KEY]`, adds `[CONNECTION: KEY → note]`, checks for `[⚠️ CONTRADICTION]`, updates
`Argumen saat ini`, reports back per the Literature Feed Protocol's step 8.

---

## B — Literature entry (not yet in library)

Use for a paper not yet ingested. Paste the Standard Literature Input Format, filled in — minimum
viable: Authors, Year, Journal, DOI + bullet notes.

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
- [Specific numbers, peaks, efficiencies, conditions — preserve every number verbatim]

My Interpretation / Why This is Relevant:
- [Optional]

Suggested Section: [Blueprint row name, or leave blank]
---
```

Claude then: calls `library add` for the key in the same turn (proactive tag resolution), places
the entry, and follows the same steps as Template A.

---

## C — Own finding / interpretation

Use for your own reasoning that isn't tied to a single cited paper — a synthesis judgment, a
framing decision, a note on what a figure shows.

```
[OWN] entry for the Scratchbook.

Target section: [Blueprint row name]

Finding / interpretation:
[Write freely — no polish needed, this is raw scratch material]

Source basis (if drawing on project data, name it so Claude can verify before writing):
[e.g. a project data table, a figure spec, or "my own judgment"]
```

Claude tags it `[OWN]`, places it, updates `Argumen saat ini` if the section's argument shifts.

---

## D — Populate a Blueprint row from existing project documents

Use when a Blueprint row's evidence already lives in a project document (a data table, gap map,
research design file) rather than in fresh literature Claude hasn't seen. Pulls the row's material
directly rather than re-describing it from scratch.

```
Populate the Scratchbook section for Blueprint row: [row name]

Pull from: [name the source file(s) — e.g. a project's classification table, gap map section,
research design item]

Rewrite rule: extract every number/finding verbatim, but express the synthesis in your own words —
do not mirror the source document's own sentence structure (same plagiarism-prevention rule as for
external literature, applied to your own prior-session outputs this time).

Tag: [OWN] where the source is the project's own analysis, [LIT: KEY] where the underlying claim
traces to a specific paper.
```

Reach for this template first when starting a new Results & Discussion row — the Manuscript
Blueprint already names which source file feeds which row (its per-row Notes column).

---

## E — Contradiction / consistency check

Use before adding a new entry when it might conflict with something already in the Scratchbook, or
periodically to audit a section that's grown large.

```
Check [KEY or "OWN" description] against everything currently in Scratchbook section
[section name] for contradictions.

If found, add the [⚠️ CONTRADICTION: A, Year vs. B, Year — note] tag inline near both entries —
don't resolve it, just flag it for Discussion synthesis.
```

---

## F — Section density / gap audit

Run before drafting a section, or whenever a Blueprint row's paragraph count looks ambitious
relative to what's actually in the Scratchbook.

```
Audit Scratchbook section [section name] against its Manuscript Blueprint row.

Report:
- Blueprint's planned paragraph count vs. what the current raw material could actually support
- Which specific sub-claims from the Blueprint's Notes column have no [LIT:] or [OWN] entry yet
  (flag each as [SOURCE NEEDED] in the Scratchbook, don't just report it here)
- Whether Journal Profile Block C flags a technique/analysis type typical for this row that's
  still missing (see "Technical Gaps to Watch")
```

---

## G — Refresh `Argumen saat ini`

Use after a batch of edits to one section when the summary line needs full re-synthesis rather
than incremental patching (required after every substantive edit; a full re-synthesis after
several small edits catches drift a single-edit patch wouldn't).

```
Re-synthesize the "Argumen saat ini" line for Scratchbook section [section name] from its current
full raw content — 1-3 sentences, not a list of what was added.
```

---

## H — Figure/table integration

Use to wire an existing figure or table into its Results & Discussion row with the right framing
language, or to note where a still-unbuilt figure needs to be referenced as forthcoming.

```
Integrate [figure/table ID] into Scratchbook section [target Blueprint row].

Pull the figure's actual content from [source spec file] — don't describe it generically; name the
specific cells/rows/values it shows.

State explicitly what claim this figure is evidence FOR (per Manuscript Blueprint's "Novelty
carrier?" column) so the eventual drafted paragraph doesn't just describe the figure but uses it.
```

---

## I — Bulk extraction from one fulltext file

Use for a paper already registered `fulltext` status in `arti-lit`, whose full text sits at
`literature/fulltext/<key-lowercase>.md`. Reads the whole paper once and distributes findings
across every Blueprint row it's relevant to — not one paste-by-paste entry per point. This is the
"Claude reads a source file directly" extraction path (stricter plagiarism rule than Template A/B,
since there's no researcher-authored summary standing between Claude and the source prose).

```
Extract [KEY] into the Scratchbook from its fulltext.

Source: literature/fulltext/[key-lowercase].md

Read once. Distribute findings across every Blueprint row this paper is relevant to (check against
the Manuscript Blueprint's per-row source notes and this paper's cluster membership). Duplication
across sections is intentional, not redundant — each section needs its own supporting material.

Extraction Rule (mandatory): rewrite every claim in your own words, structurally distinct from the
source's own sentences — do not mirror phrasing or sentence structure even where the words differ.
Preserve every specific number verbatim (yields, efficiencies, concentrations, rate constants,
particle sizes, etc.) — never replace a number with a qualitative description.

Also extract, if present, this paper's own classification/tagging scheme relevant to this project —
cross-check it against the project's own classification record and flag any mismatch rather than
silently trusting either source.

For each section touched:
- Tag [LIT: KEY]
- Add [CONNECTION: KEY → note] explaining relevance to that specific section's argument
- Flag [⚠️ CONTRADICTION] against existing entries if found
- Update that section's Argumen saat ini

Report back: which sections were touched, any contradictions found, and whether the extracted
classification matches the project's own record.
```

**Direct quote check:** if anything in the draft output could be found by a plagiarism checker as
matching the fulltext source, it must be rewritten before it enters the Scratchbook — this test
applies to project-sourced fulltext exactly as it does to external literature.

---

## J — Batch sweep of the fulltext-registered corpus

Use once, or periodically, to sweep every fulltext-registered paper not yet reflected in the
Scratchbook — faster than issuing Template I once per key by hand.

```
Sweep the fulltext-registered corpus into the Scratchbook.

Registered keys: [see this project's fulltext-corpus-status record] — skip any key already
reflected in the Scratchbook (check its Reference List first).

For each unswept key, apply Template I's extraction rule (read once, distribute across all
relevant Blueprint rows, rewrite in original prose, preserve numbers verbatim, tag [LIT: KEY] +
[CONNECTION] + [⚠️ CONTRADICTION] as found).

Process in [this project's pacing-plan order] so background/narrative sections build up in the
same logical order the manuscript will eventually read in.

[Name any export-only/scavenger-citation keys out of scope for this sweep] — those get Template B
instead, sourced from the library abstract.

After the sweep: run Template F (density/gap audit) on every section touched, since a batch sweep
is exactly when it's easiest to lose track of which Blueprint rows are still thin.
```

**Cost note:** a full sweep can mean reading 20+ full papers in one pass — expect a long single
turn. Splitting it by cluster (as separate invocations of this same template with the key list
narrowed, per the project's own pacing plan) is the default, not the exception, once the corpus is
large — see this skill's large-corpus session-chunking guidance.

---

## Notes on reuse

- These templates assume the Scratchbook already exists (created fresh from
  `scratchbook-template.md` if this is the first population session).
- Every template still routes through this skill's own rules: source tags are mandatory, Claude
  never fabricates a citation, direct quotes get flagged for paraphrase, and `[LIT: key]` tags
  resolve to a real `arti-lit` row in the same turn they're written.
- If a template stops fitting the Manuscript Blueprint's actual shape (e.g., a row gets split into
  two subsections during drafting), update the Blueprint's Revision Notes first, then treat any
  project-side parameters as needing a refresh — don't let a project's own parameters drift out of
  sync with the Blueprint they're keyed to.

## Change log
- 2026-09-15 — created, generalizing a working project's `writing/scratchbook-prompts.md` (10
  templates, A-J) into project-agnostic form; project-specific values (Blueprint row names, source
  file paths, corpus/cluster names) now come from the calling project's own "Project parameters"
  block instead of being hardcoded here.
