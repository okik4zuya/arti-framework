Set up this project's persistent memory system and the standard research-paper folder boilerplate,
project-local (not the default ~/.claude memory).

0. Create the standard paper-project folder layout in the project root, alongside `memory/` and
   `CLAUDE.md`:
   - `idea/` — ARTi-idea's outputs live here: `gap-map.md`, `idea-canvas.md`,
     `experiment-blueprint.md`, `journal-target-sheet.md`, `handoff.md`
     (the short handoff manifest — decisions and pointers, not copied content). One project = one
     paper, so none of these filenames carry a topic slug.
   - `writing/` — ARTi-writing's outputs live here:
     `journal-profile_[journal-abbreviation].md` (keeps its placeholder — a rejected paper can
     acquire a second target journal, so two profiles must be able to coexist),
     `manuscript-blueprint.md`, `scratchbook.md`, `manuscript_draft[N]_[date].md` (keeps its
     placeholder — draft versioning means several coexist), `iteration-log.md`,
     `references.md` (generated — see the `literature/` layer table below),
     `completion-plan.html` (hand-maintained, created at Stage 4b — see ARTi-writing SKILL.md)
   - `literature/` — three layers, one shared key (`author-year[a|b]`, e.g. `kaw-2016`):
     - `literature\exports\` — raw downloads, **never renamed by the researcher**; Claude parses
       them and assigns the key
     - `literature\fulltext\` — PDFs and their `.md` conversions, named by key
     - `literature\search-log.md` — one row per search round: query (bare, copy-ready) · date ·
       hits · export file · target claim/paragraph · status
     - `literature\library.md` — canonical bibliography, one source per line (superset including
       screened-out sources), columns: key · full citation in the target journal's style · DOI ·
       local file path · read-status · used-in
   - `data/` — raw and processed research data
   - `figures/` — generated plots, images, and diagrams for the manuscript
   - `submission/` — the final formatted manuscript package:
     `cover-letter_[journal-abbreviation].md`, `rebuttal_[journal-abbreviation]_round[N].md`
     (both keep their placeholder for the same reason as the Journal Profile), `growth-log.md`,
     journal-formatted export, supplementary files

   Note: ARTi-writing's Voice Profile is deliberately **not** in this project's `writing/` folder
   — it's cross-project and lives in `~/.arti/voice-profiles/`, alongside the Researcher Profile and
   Idea Bank (created by this skill's Workflow A).
   Seed `literature\search-log.md` and `literature\library.md` as header-only files; create
   `literature\exports\` and `literature\fulltext\` empty. All other folders are created empty (no
   placeholder files) except where a later step in this template populates one. This layout is the
   same across every ARTi paper project — do not deviate from these six folder names.

1. Create a `memory/` folder in the project root with exactly two files:
   - `memory/MEMORY.md` — the index: pointers only, one line each (hard-capped — no line restates
     another file's content), never content itself
   - `memory/todo-list.md` — the living, checkable task list, shaped as **one overwritten "Current
     state" block at the top** (replaced in place each session, never stacked alongside older
     "Current state" / "Next session" blocks — the change log carries the fact that an old one
     existed), an **archive** section below it for anything worth keeping but no longer live, and
     the contiguous `- [ ]` / `- [x]` task list last, grouped by phase or milestone if the project
     has them. Search keywords and query lists belong in `literature\search-log.md`, not here.

   That is the whole memory scaffold for a paper project. Deliberately **not** created:
   - `goal.md` — the project's purpose already lives in the Idea Canvas's confirmed research
     question and the Experiment Blueprint's objective. A second statement of it drifts.
   - `history.md` — a cross-topic chronological log duplicates the per-file change logs. It earns
     its keep on a long-running meta-project, not on a single manuscript.

2. Create `CLAUDE.md` in the project root, kept short, that states:
   - The project's folder boilerplate: `idea/`, `writing/`, `literature/`, `data/`, `figures/`,
     `submission/` — one line each on what belongs there (see step 0 above).
   - `memory/` in this project is the single source of truth. Do not read from or write to the
     default `~/.claude/projects/.../memory/` location for this project.
   - `memory/MEMORY.md` is the index — pointers only, never content.
   - `memory/todo-list.md` is the living task list, shaped as one overwritten "Current state"
     block + archive + contiguous task list (see step 1). Read it before advising on scope or
     priority, and keep it current as items complete or new ones surface.
   - One dedicated file per topic. When a new topic or decision comes up, create its own file and
     add a one-line pointer to the index.
   - Update the existing file on a topic rather than creating a near-duplicate.
   - Read the relevant memory file before advising on that topic; details live there, not here.
   - A pointer to `~/.arti/working-preferences.md` — read it at the start of every ARTi session; it
     is short, imperative, and states what Claude must do, not what was observed.
   - **Timestamps:** get the real current time before writing any timestamp (e.g. run a date
     command) — never guess it. Set `created` in frontmatter on creation and `updated` on every
     write, and add a line to that file's `## Change log`. That is the whole ritual — a paper
     project does not maintain a separate chronological history file or a change log of the index
     itself.

3. Each memory file uses this frontmatter:
   ---
   name: kebab-case-slug
   description: one-line summary, specific enough to judge relevance later
   metadata:
     type: project | user | feedback | reference
     tier: T0 | T1 | T2
     created: yyyy-mm-dd HH:mm
     updated: yyyy-mm-dd HH:mm
   ---
   followed by content, then a `## Change log` section at the bottom.

   **House style (compact by construction, not by later cleanup):**
   - **Tiering with byte budgets.** T0 = auto-loaded every session (`MEMORY.md`, `todo-list.md`,
     `CLAUDE.md`) — hard budget **~20 KB total**. T1 = read on demand, no budget, but the
     rule/evidence split below is required. T2 = archive, never auto-read. A T0 file that exceeds
     its budget gets compacted at the next wrap-up ritual, not left to grow.
   - **Tables for any repeated-structure list** — session pointers, findings, references, search
     rounds. Prose enumeration of parallel items is the largest source of bulk in practice.
   - **Change log = one line per date, ≤120 chars, naming *what changed*** — never re-summarizing
     the file's own content. Keep ~10 entries; collapse older ones to one "created and iterated
     through `<date>`" line.
   - **Rule/evidence split for behavioral files.** Imperative one-line rules at the top; narrative
     evidence below or in a T2 archive — never the reverse.
   - **One-sentence index lines, hard-capped.** Detail lives in the linked file, not in the index.
   - **No cross-file restatement.** A sentence summarizing another file's content becomes a
     `[[slug]]` link instead.
   - **Living state is overwritten, not appended.** One current block; superseded blocks are
     deleted, and the change log carries the fact that they existed.
   - **Cut meta-narration.** Record the decision and its date; drop commentary on why it was
     recorded.
   - **Lossless-compaction rule.** A compaction pass may remove prose bulk only. It must preserve,
     verifiably, every: decision · date · open `- [ ]` item ·
     `[UNVERIFIED]`/`[DATA NEEDED]`/`[SOURCE NEEDED]` flag · file path · `[[link]]`. Before/after
     sets of those items must be identical.

4. Link related memory files with `[[slug]]` references rather than duplicating content across
   files.

5. If this conversation already contains project context worth persisting (decisions made,
   constraints established, background explained), create the first topic file(s) now and populate
   the index — don't leave it empty. Otherwise leave the index scaffolded and empty, ready for the
   first real memory. The same applies to `todo-list.md`: if there is enough context to draft real
   tasks, draft them rather than leaving empty scaffolding.

6. Add a new row for this project to `~/.arti/progress-index.md` (stage: "Not started", status:
   "Scaffolded"), per `references/progress-index-template.md` in the `ARTi-idea` skill's reference
   folder — this ties the new project into the researcher's cross-project dashboard. After this,
   the index is updated at **phase boundaries only**: idea complete, writing started, submitted.

7. **Session-end wrap-up ritual.** Any phrasing that means "we're done for now" — not only the
   exact words "update memory" — fires this fixed checklist: update the relevant project memory
   file(s) · overwrite `todo-list.md`'s "Current state" block · append to the cross-project
   workflow-session log (`~/.arti/workflow-sessions/`) · check whether anything said this session
   should be promoted to `~/.arti/working-preferences.md` (a correction on *how* to do something) ·
   check whether a recurring loop should be logged or updated in `~/.arti/ebook-notes.md`'s
   micro-flow catalog (once a loop repeats a second time, write it up). Skipping the ritual because
   the trigger phrase wasn't the exact one used before is the failure mode this step exists to
   close.

8. **Surface standing asks at session start.** If any memory file records an open question Claude
   was supposed to ask the researcher (e.g. "ask whether an Iteration Log entry is wanted"), ask it
   near the start of the session rather than merely re-recording that it's still open.

Confirm the folder and file layout once done.
