# ARTi Workflow Prompt Templates

Copy-paste prompts for driving ARTi-idea → ARTi-writing end to end. Two tracks: **Review/SLR**
and **Research Article** diverge only at Stage 4 (Research Design) — everything else is the same
skeleton. Fill in the `[bracketed]` parts; drop a stage's prompt if you're doing a Warm Start
(topic/journal already settled — see ARTi-idea's Warm Start section) and enter at Stage 4 directly.

---

## Stage 0 — Setup (once per researcher / once per new project)

> "Set up ARTi for me." *(first time only — creates `~/.arti` + Researcher Profile)*

> "Scaffold this project's memory." *(new project, profile already exists)*

---

## Stage 1 — Researcher Profile (once per researcher, update on change)

> "Build my Researcher Profile." / "Update my Researcher Profile — [what changed]."

---

## Stage 2 — Gap Map (per project, iterative)

> "Build the Gap Map from [literature source — e.g. a NotebookLM export, a folder of PDFs, a list
> of DOIs]."

> "Summarize paper [title/key] and fold it into the Gap Map." *(single-paper extraction, any time)*

> "Add [N] more papers to the Gap Map — focus on [sub-topic/gap]." *(iterative deepening)*

---

## Stage 3 — Idea Canvas (per project)

**Review/SLR:**
> "Confirm Gap [N] as the review's organizing angle. Build the Idea Canvas: generate candidate
> review framings/titles from it, score each C/M/E against my Researcher Profile, and flag whether
> Gap [M] is worth folding in as a secondary angle or should stay separate."

**Research article:**
> "Generate 3–5 candidate research ideas from Gap [N] (or the full Gap Map). Score each C/M/E
> against my Researcher Profile and ceiling, and recommend which to advance."

> "I want to add my own idea: [idea text]. Score it and compare against the generated candidates."

---

## Stage 4 — Research Design (this is where the two tracks diverge)

**Review/SLR — review methodology, not a lab experiment:**
> "Build the Research Design for the confirmed idea — lay out the review methodology: how [the
> classification/synthesis framework] gets applied across the corpus, what fulltext checks or
> additional literature are needed before the core claim can be written, the synthesis/analysis
> plan (comparison tables, cross-domain framework, etc.), and any feasibility flags."

**Research article — feasibility-checked lab/field experiment:**
> "Build the Research Design for the confirmed idea — materials/samples, synthesis or data
> collection protocol, characterization/measurement plan cross-checked against my Researcher
> Profile, controls, timeline, and feasibility flags (🔴🟡🟢)."

Both tracks, once 🔴 flags are resolved:
> "Design is confirmed — print it." *(renders `research-design.md` → `.pdf`)*

---

## Stage 5 — Journal Target Sheet (per project)

> "I'm considering these journals: [list]. Rank them on scope fit, Q-rank, and our publication
> history, then do the light analysis on the top two and confirm a target + fallback."

*(If you already know the target:)*
> "Target journal is [Journal Name], fallback [Journal Name] — record it on the Journal Target
> Sheet with the reason, and run the predatory-journal screen if it's unfamiliar."

---

## Handoff → ARTi-writing

> "Idea, design, and journal are all confirmed — write the handoff manifest."

Then, in the same or a new session:
> "Start ARTi-writing — build the full Journal Profile for [Journal Name] from 5–8 example papers,
> including the ones already read during journal targeting."

---

## ARTi-writing stages (both tracks converge here)

> "Build the Journal Profile — Blocks A, C, D." *(scope/audience, structure norms, novelty threshold)*

> "Build my Voice Profile from these sample manuscripts: [files/links]." *(once per voice, cross-project)*

> "Build the Manuscript Blueprint." *(section-by-section skeleton against the Journal Profile)*

> "Populate the Scratchbook for [section] from the Gap Map / Research Design / literature."

> "Draft [section name] from the Scratchbook, in my voice." *(repeat per section)*

> "Review this draft against the Journal Profile and Voice Profile — flag gaps."

> "Log this revision in the Iteration Log — [what changed and why]."

> "Write the cover letter for [Journal Name]." / "Draft a response to this reviewer comment: [text]."

> "We got accepted / rejected / published — log it." *(Publication Growth Log, triggers `project upsert`)*

---

## Cross-cutting, any stage

> "Do I already have research on [topic]?" *(runs `idea-bank search` + `project list` before
> answering — never a local-memory-only question)*

> "Update memory / end session." *(fires the Session End ritual: memory files, status.md,
> todo-list.md, workflow-session log, working-preferences promotion)*
