---
name: ARTi-idea
description: >
  A structured pre-writing skill for developing publishable research ideas before any manuscript
  work begins. Use this skill whenever a researcher wants to identify a research gap, develop and
  filter research ideas, score novelty, design a feasibility-checked experiment, or select a target
  journal. Triggers include: "I want to find a research gap", "help me develop a research idea",
  "what should I research", "is my idea novel enough", "help me choose a journal before I start",
  "design an experiment for me", "I want to publish but don't know what to study", "summarize
  paper [title]", "extract this paper", or any request to plan or validate a research topic before
  writing begins, or to extract a single paper's gap-map/scratchbook-ready fields. Always use this
  skill before
  ARTi-writing when the researcher does not yet have a confirmed research idea, experiment
  design, or target journal. The skill produces six documents that feed directly into the
  ARTi-writing workflow.
---

# ARTi-idea Skill

A document-driven workflow for developing a validated, publishable research idea — before any
writing begins. The workflow is organized around a persistent setup stage, **six core documents**,
and **six sequential stages**, ending with a confirmed research topic, experiment design, and
journal target ready to hand off to the ARTi-writing skill.

---

## Core Documents

### 1. Researcher Profile
A one-time self-assessment of the researcher's actual capabilities and constraints. This document
is the reality-check filter applied to every idea and every experiment design throughout the
workflow. Built once **per researcher, not per project**; updated only when circumstances change.
Persists in the researcher's `~/.arti` folder (see Stage 0) so it survives across every future
project without being rebuilt or duplicated.

**Contents:**
- Equipment and instruments available (own lab + accessible shared facilities)
- Analytical techniques the researcher can perform independently
- Techniques requiring collaboration — and whether collaborators are available
- Budget range for consumables and analysis
- Timeline available for the project
- Domain expertise and literature familiarity (strong / moderate / limited)
- Prior publications and established methods (to avoid self-plagiarism risk)
- Language and writing support available
- **Positioning Line** — one sentence capturing the researcher's standing thematic axis;
  written automatically once the first Research Idea Bank entry exists (see Stage 3)

**When to create:** At Stage 0, before any other document — but only if it doesn't already exist
in `~/.arti/`. Claude must ask the researcher directly for each field — do not assume or infer.

**File:** `~/.arti/memory/researcher-profile.md`

---

### 2. Gap Map
A structured landscape of the research field, built from literature the researcher provides.
Maps what exists, what methods dominate, what questions remain unanswered, and where
contradictions lie. The Gap Map is the evidence base that justifies the research idea.

**Structure:**
```
## Field Overview
[Brief synthesis of the current state of the field]

## Dominant Approaches & Methods
[What techniques and study designs are standard]

## Established Findings
[What is well-established and not worth revisiting]

## Identified Gaps
### Gap 1: [Label]
- Evidence: [Which papers reveal this gap]
- Gap type: Conceptual / Methodological / Empirical
- Why it matters: [Significance if filled]

### Gap 2: [Label]
...

## Contradictions & Debates
[⚠️ CONTRADICTION: Author A vs Author B — description]

## Underexplored Areas
[Topics touched on but not studied in depth]

## Reference List
[Key mapping only — full bibliographic details live in `literature\library.md` (owned by
`ARTi-ref`, keyed `author-year[a|b]`), fetched via `library get --key KEY` rather than re-typed
here]
```

**When to create:** After the Researcher Profile is complete. Built iteratively as literature
is fed in — never all at once. Claude should identify which gap type each gap belongs to
(see Novelty Scoring below). Depth matters more than count: one gap carrying at least three
supporting references and an explicit reason it matters is enough to proceed.

**File:** `gap-map.md`

---

### Paper Extraction (on-demand, not one of the six core documents)

**Trigger:** "summarize paper [title]", "extract this paper", "give me the NotebookLM extraction
for [paper]", or any request to pull structured notes from one specific paper. Works at any stage,
even before a Gap Map exists — it is not gated on Stage 2.

The extraction mechanics themselves (template fields, NotebookLM prompt, registering the paper in
`arti-lit` and saving the extraction as its `--summary`) live in the **`ARTi-ref`** skill — see its
"Paper Extraction" section. This skill's own follow-up, specific to Gap Map building:
- If a Gap Map already exists for this project, offer to fold the extraction's `REFERENCE ENTRY`
  block and any `⚠️ CONTRADICTION` lines into it directly rather than leaving that step to the
  researcher.
- If a Scratchbook already exists, offer to fold `Citable Claims` into the relevant section(s).
- `Novelty Signals` are raw, unscored input — they feed Idea Canvas scoring later (Stage 3), never
  a C/M/E score at extraction time.

**File written to:** none of its own — the extraction lives in the `arti-lit` summary field; only
the pieces the researcher confirms get folded into `gap-map.md` / `scratchbook.md`.

---

### 3. Idea Canvas
The working document where raw ideas are generated, evaluated, filtered, and developed into
a focused research topic and title. Each candidate idea is scored and compared. The final
surviving idea becomes the confirmed research direction.

**Structure per idea entry:**
```
## Idea [N]: [Short label]
**Research question:** [One sentence]
**Gap addressed:** [Which gap from Gap Map]
**Novelty Score:** C[1-5] / M[1-5] / E[1-5] → Composite: [label]
**Novelty Ceiling Check:** ✅ Within ceiling / ⚠️ Exceeds ceiling on [dimension]
**Feasibility Assessment:** [Brief — what's needed vs. what's available]
**Decision:** ✅ Advance / ⚠️ Redesign → [reason] / ❌ Reject → [reason]
**Redesign Notes:** [If applicable — how to adjust scope or approach]
```

**When to create:** Once the Gap Map has at least one well-evidenced gap. Claude generates
initial ideas from the gaps, then the researcher filters and adds their own. Every idea must
go through Novelty Scoring before a decision is made.

**File:** `idea-canvas.md`

---

### 4. Research Design
A feasibility-checked experiment design for the confirmed research idea. See
`references/stage4-research-design-protocol.md` for the full procedure (purpose, when to create,
and the closing print step) — this is schema only.

**Structure:**
```
## Research Objective
[One sentence — the confirmed research question]

## Hypotheses
[H1, H2, ... — testable predictions]

## Experimental Design
### Materials & Samples
### Synthesis / Preparation Protocol
### Characterization Plan
| Technique | Purpose | Available? | If not — alternative or collaborator needed |
|---|---|---|---|

### Analysis Plan
[Statistical or computational analysis required]

### Controls
[Positive and negative controls]

### Timeline
[Realistic milestone plan given researcher's time constraints]

## Feasibility Flags
🔴 [Technique or resource not available — must resolve before proceeding]
🟡 [Technique available but requires training or collaboration — plan needed]
🟢 [Fully feasible within current resources]

## Novelty-Experiment Alignment
[Confirm that the experiment as designed actually delivers the novelty claimed in the Idea Canvas]
```

**File:** `research-design.md`

---

### 5. Journal Target Sheet
A decision record naming the target journal and its fallback, built by ranking candidates cheap
(free signals) and reading narrow (top two only). Full process, decision rules, and schema live in
`references/stage5-journal-target-protocol.md` and `references/journal-target-sheet-template.md`.

**File:** `journal-target-sheet.md`

---

### 6. Research Idea Bank
A persistent, cross-project backlog of research/paper-topic ideas that cleared novelty scoring but
didn't become the confirmed idea for their originating project. Lives in the researcher's `~/.arti`
folder (see Stage 0), not any single project folder, so it accumulates across every future topic.
Scoped to research ideas only — for framework/skill ideas or general cross-project raw ideas, see
`~/.arti/inbox/idea-index.md` instead.

**Structure per entry:**
```
## Entry [N]: [Short label]
**Idea text:** [The research question as scored]
**Novelty score:** C[n] / M[n] / E[n] → [Composite label]
**Date parked:** [YYYY-MM-DD]
**Source project/topic:** [Which Idea Canvas this came from]
**Reason parked:** Lost Stage 3 selection / Explicitly deferred by researcher
```

**When an entry is added:** Automatically, whenever an idea clears Meaningful-or-above on the
Idea Canvas (Stage 3) but is not the one selected to advance. Never discarded silently.

**When it's read:** At the start of every new Gap Map (Stage 2), Claude checks the Research Idea
Bank first and surfaces any parked ideas relevant to the new topic before generating fresh ones.

**File:** `~/.arti/memory/research-idea-bank.md`

---

## Novelty Scoring System

Every research idea on the Idea Canvas must be scored before a decision is made.
Novelty is scored across three independent dimensions.

### Three Dimensions

**C — Conceptual Novelty**
How new is the research question or hypothesis?
- 1: Replication or minor variation of existing work
- 2: Modest extension (new condition, new sample, same framework)
- 3: Fills a real gap — asks a question not previously addressed
- 4: Reframes understanding of the topic or proposes a new mechanism
- 5: Paradigm-shifting — fundamentally challenges accepted knowledge

**M — Methodological Novelty**
How new is the approach, technique, or study design?
- 1: Standard methods, well-established protocols
- 2: Slight adaptation of existing method
- 3: Applies an established method from another field or in a new context
- 4: Significant modification or combination of methods producing new capability
- 5: Invents a new technique or measurement approach

**E — Empirical Novelty**
How new are the data, findings, or observations produced?
- 1: Confirms known results in a new sample
- 2: Produces incremental data extending an existing dataset
- 3: Generates first-reported data for a meaningful condition or system
- 4: Produces findings that substantially revise quantitative understanding
- 5: Produces findings that contradict or overturn established results

### Composite Label
After scoring all three dimensions, assign a composite label:

| Composite condition | Label |
|---|---|
| All three ≤ 2 | **Incremental** — too low; reject or redesign |
| At least one ≥ 3, others ≥ 2 | **Meaningful** — minimum viable novelty |
| At least one ≥ 4, others ≥ 2 | **Significant** — strong candidate |
| Any dimension = 5 | **Paradigm-shifting** — high risk; check ceiling first |

### Novelty Ceiling
Before scoring, **read** the researcher's Novelty Ceiling from Section H of the Researcher
Profile (`~/.arti/memory/researcher-profile.md`). `ARTi-setup` derives it once, at profile creation —
downstream stages read it and must not re-derive it. What Section H records:

- **C ceiling:** Limited by domain expertise and literature depth. A researcher with
  shallow literature knowledge cannot reliably identify a C4–5 gap.
- **M ceiling:** Limited by available equipment and techniques. A researcher without
  access to advanced instrumentation cannot execute an M4–5 study.
- **E ceiling:** Limited by the experiment design's capacity to produce truly new data.
  Constrained by sample access, measurement precision, and statistical power.

Claude must flag any idea where the required novelty exceeds the researcher's ceiling
on that dimension. Do not reject — instead propose a redesign that brings the idea
within ceiling while preserving as much novelty as possible.

### Sweet Spot Rule
The target zone for most researchers:
- At least one dimension at 3–4
- No dimension below 2
- No dimension exceeding the researcher's ceiling

Score-5 ideas are only advanced if the Researcher Profile explicitly supports them.

---

## Workflow Stages

```
[Stage 0: Persistent ~/.arti Folder] → [Researcher Profile] → [Gap Map] → [Idea Canvas + Novelty Scoring]
                                                                                ↓
                                                                   [Research Design]
                                                                                ↓
                                                                   [Journal Target Sheet]
                                                                                ↓
                                                            → [Handoff Manifest] →
                                                                  → to ARTi-writing →
```

---

### Stage 0: Persistent Folder Setup
Runs once per researcher, not once per project. The persistent ARTi data folder is the fixed path
`~/.arti` (`C:\Users\<user>\.arti\` on Windows, `~/.arti` on Mac/Linux) — same on every machine,
never asked about or confirmed with the researcher (this used to be a per-researcher Drive-folder
question; it isn't anymore). If `~/.arti/memory/researcher-profile.md` doesn't exist yet, run the
`ARTi-setup` skill's Workflow A instead of duplicating that logic here.

- If `~/.arti/memory/researcher-profile.md` already exists, load and reuse it — skip re-asking all
  Stage 1 fields, only confirm nothing has changed.
- `~/.arti` also holds: `research-idea-bank.md`, `journal-library\<journal-slug>.md` per journal, and
  `project-index.md` — all described under their relevant document/stage below.

---

### Stage 1: Researcher Profile
**Trigger:** Stage 0 complete, no existing profile to reuse. **Output:**
`~/.arti/memory/researcher-profile.md`, including a derived Novelty Ceiling for C/M/E. See
`references/stage1-researcher-profile-protocol.md` for the full procedure and output format.

---

### Stage 2: Gap Map Construction
**Trigger:** Researcher Profile complete, literature being fed in. **Output:** `gap-map.md`,
built iteratively, never all at once. See `references/stage2-gap-map-protocol.md` for the full
procedure and the minimum-viable-Gap-Map bar.

---

### Stage 3: Idea Generation & Novelty Scoring
**Trigger:** Gap Map has at least one well-evidenced gap. **Output:** `idea-canvas.md`, plus two
possible side effects: an auto-parked Research Idea Bank entry (`~/.arti/memory/research-idea-bank.md`)
for every viable-but-unselected idea, and — only on the very first such entry ever, for this
researcher — a Positioning Line written into Stage 1's `researcher-profile.md`. See
`references/stage3-idea-novelty-protocol.md` for the full procedure, decision rules, and both side
effects' mechanics.

---

### Stage 4: Research Design
**Trigger:** One idea confirmed on the Idea Canvas. **Output:** `research-design.md`, printed to
`research-design.pdf` once feasibility flags are resolved. See
`references/stage4-research-design-protocol.md` for the full procedure.

---

### Stage 5: Journal Target Sheet — rank cheap, read narrow
**Trigger:** Research Design stable. **Output:** `journal-target-sheet.md`. Rank on free signals
(3-5 candidates), light-analyze the top two only, stop as soon as #1 clears. See
`references/stage5-journal-target-protocol.md` for the full 3-step procedure, the conditional
Predatory Journal Screen, and light-extraction fields.

---

## Handoff to ARTi-writing

When Stage 5 is complete, Claude writes a short `idea\handoff.md` — the **Handoff
Manifest**. It is roughly fifteen lines: the confirmed decisions, plus pointers naming which
existing file feeds which downstream stage. It does **not** transcribe the content of the five
source documents.

Why: those five documents sit in the same project folder and are read directly by ARTi-writing.
A transcribed copy goes stale the moment any source is edited, and then two versions of the same
decision exist. **Copy the decisions, point at the content.**

```
# Handoff — [topic]
**Date:** [YYYY-MM-DD]

**Confirmed research question:** [one sentence]
**Working title:** [draft title]
**Novelty score:** C[n] / M[n] / E[n] → [composite label]
**Target journal:** [name] (fallback: [name])
**Journal novelty threshold (light):** C[n–n] / M[n–n] / E[n–n] — extend, do not re-derive
**Example papers already read:** [n] — they count toward ARTi-writing's 5–8
**Open 🔴 flags:** [any unresolved feasibility or novelty flag, or "none"]

## Where the content lives
| Source file | Feeds |
|---|---|
| `idea\gap-map.md` | Scratchbook — Introduction section |
| `idea\research-design.md` | Scratchbook — Methods + Results structure |
| `idea\journal-target-sheet.md` | Journal Profile Block A + Block D threshold |
| `idea\idea-canvas.md` | Title, Abstract framing, Introduction gap statement; Block D |
| `~/.arti/memory/researcher-profile.md` | Writing support context and technical gap flags |
```

**Project index cadence:** run `project upsert` for this project's row here, at the phase
boundary — status "idea complete / handed off". The index is updated at phase boundaries only
(idea complete → writing started → submitted), not once per stage. Consider whether `--summary`
needs updating too — a new major topic (e.g. an instrument-design sub-study) emerging during
idea development is worth reflecting there.

Claude must explicitly tell the researcher when the handoff is ready:
*"Your research idea is confirmed, your experiment is designed, and your target journal is
selected. `handoff.md` is ready — you are ready to begin the ARTi-writing workflow.
Start by building the full Journal Profile from 5–8 example papers from [Journal Name],
including the [n] you already read here."*

---

## Warm Start — arriving with topic and journal already settled

Many researchers arrive with a mature topic and a shortlist they have held for months. Marching
them through a Gap Map, five ideas, and five journals only to land where they started is the
fastest way to get this workflow abandoned.

If the idea and the journal are already settled:
- Enter at **Stage 4 (Research Design)** here, and at the **Journal Profile** in ARTi-writing
- Build the Gap Map **retroactively**, as the Scratchbook's Introduction section — which is where
  it was always headed anyway
- Skip Stages 2, 3's idea generation, and 5's ranking; record the already-chosen journal directly
  on the Journal Target Sheet with the reason it was chosen

**Two prerequisites are not skippable:**
1. The **Researcher Profile** (`~/.arti/memory/researcher-profile.md`), including its Section H Novelty
   Ceiling — without it there is no basis for any feasibility judgment
2. The **C/M/E score** for the settled idea — without it there is no basis for journal fit

Without those two the workflow has no footing, however mature the topic is. Score the settled
idea on the Idea Canvas even when there are no competitors to compare it against.

---

## Key Principles

1. **Profile before everything** — never score an idea or evaluate feasibility without
   a completed Researcher Profile.
2. **Gaps before ideas** — never generate ideas without a Gap Map. One gap with at least three
   supporting references and a stated reason it matters is enough; depth beats count.
3. **Score before deciding** — every idea must have a C/M/E score and ceiling check
   before a decision is made.
4. **Ceiling is a redesign trigger, not a rejection** — when an idea exceeds the ceiling,
   propose a redesign rather than discarding the idea.
5. **Feasibility is non-negotiable** — a 🔴 flag in the Research Design must be
   resolved before the workflow advances.
6. **Light journal analysis here, deep analysis in writing** — do not perform full
   Block B/C extraction at this stage. Save that effort for the committed journal.
   Rank on free signals; read papers only for the top two; stop as soon as #1 clears.
7. **Never fabricate** — gaps, ideas, and scores must be traceable to the Gap Map and
   Researcher Profile. Claude must not invent gaps or suggest techniques not grounded
   in the researcher's actual resources.
8. **Novelty type matters** — a C3/M1/E1 idea and a C1/M1/E3 idea have the same
   composite but target completely different journals. Always interpret the profile, not
   just the number.
9. **Copy decisions, point at content** — the handoff manifest records what was decided and
   where each document lives. It never transcribes those documents; a copy goes stale the
   moment its source is edited.
10. **The Novelty Ceiling is read, not re-derived** — `ARTi-setup` writes Section H of the
    Researcher Profile once. Every stage here reads it, and no stage recomputes it.

---

## Reference Files

**`arti-db` invocation** — every `idea-bank`/`project` command below runs as:
`"~/.arti/python/python.exe" "~/.arti/tools/arti-db/cli.py" <subcommand> ...` (Mac/Linux:
`~/.arti/python/bin/python3`). Each call prints one JSON object (`{"ok": true, ...}` or
`{"ok": false, "error": ...}`); see `~/.arti/tools/arti-db/README.md` for the full subcommand
surface. Never hand-edit `research-idea-bank.md` or `project-index.md` directly — both are
generated exports, overwritten on every write.

**`arti-jfinder` invocation** — every `journal`/`scope` command in Stage 5 below runs as:
`"~/.arti/python/python.exe" "~/.arti/tools/arti-jfinder/cli.py" <subcommand> ...` (Mac/Linux:
`~/.arti/python/bin/python3`; no `--project` flag — it is a cross-project singleton like
`arti-db`). Each call prints one JSON object (`{"ok": true, ...}` or `{"ok": false, "error": ...}`);
see `~/.arti/tools/arti-jfinder/README.md` for the full subcommand surface. Backed by a
researcher-downloaded Scimago snapshot — if `journal search`/`get` returns `{"ok": false}` because
the database is empty or missing, tell the researcher to download the current-year export from
Scimago and run `ingest --file PATH --year YYYY`, then fall back to general knowledge for that
session rather than blocking Stage 5 on it.

- `../ARTi-setup/references/researcher-profile-template.md` — blank Researcher Profile with all
  fields, including the Positioning Line (owned by `ARTi-setup`, which creates this document —
  read from there rather than expecting a duplicate in this skill's own `references/`)
- `references/stage1-researcher-profile-protocol.md` — Stage 1 procedure and Novelty Ceiling
  output format
- `references/gap-map-template.md` — blank Gap Map structure
- `references/stage2-gap-map-protocol.md` — Stage 2 procedure and minimum-viable bar
- `../ARTi-ref/references/paper-extraction-template.md` and
  `../ARTi-ref/references/notebooklm-extraction-prompt.md` — Paper Extraction's field shapes,
  owned by `ARTi-ref` (see Paper Extraction above)
- `references/idea-canvas-template.md` — blank Idea Canvas with scoring table
- `references/stage3-idea-novelty-protocol.md` — Stage 3 procedure, decision rules, Research Idea
  Bank auto-park, and Positioning Line trigger
- `references/novelty-scoring-guide.md` — detailed scoring rubric with examples
- `references/stage4-research-design-protocol.md` — Stage 4 procedure and closing print step
- `references/stage5-journal-target-protocol.md` — Stage 5 procedure: 3-step ranking flow,
  conditional Predatory Journal Screen, light-extraction fields
- `references/journal-target-sheet-template.md` — blank Journal Target Sheet (target +
  fallback decision record, including the two-row Journal Comparison Table)
- `references/research-idea-bank-template.md` — blank Research Idea Bank entry shape (`~/.arti/memory/research-idea-bank.md`)
- `references/predatory-journal-screen.md` — conditional screen: full checklist for unfamiliar
  journals, recorded auto-pass for Scopus Q1–Q2 journals the group already publishes in
- `references/journal-library-template.md` — cached per-journal entry shape
  (`~/.arti/journal-library/<journal-slug>.md`)
- `references/project-index-template.md` — cross-project dashboard row shape
  (`~/.arti/memory/project-index.md`)

Read the relevant reference file before starting any stage.

## Change log
- 2026-09-17 — Split Stages 1–5's procedural bodies (and the schema-blended process sentences in
  Core Documents #4/#5) out of this dispatcher into five new `references/stage<N>-*-protocol.md`
  files, per `skill-modularization.md`'s framing (same skill, same stages — only where the prose
  for an existing stage lives on disk changed). Stage 0, the Handoff, and Warm Start stay inline
  unchanged.
