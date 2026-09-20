Set up this project's persistent memory system and the standard research-paper folder boilerplate,
project-local (not the default ~/.claude memory).

**`arti-db` invocation** — every `project upsert`/`idea-index upsert`/`idea-index archive`
command below runs as: `"~/.arti/python/python.exe" "~/.arti/tools/arti-db/cli.py" <subcommand>
...` (Mac/Linux: `~/.arti/python/bin/python3`). Each call prints one JSON object
(`{"ok": true, ...}` or `{"ok": false, "error": ...}`); see `~/.arti/tools/arti-db/README.md` for
the full subcommand surface. This is the *cross-project* aggregator only — a project's own local
`inbox/` has no index or database of its own to keep in sync; it's plain files, glob-scanned.

**`arti-lit` invocation** — every `library add`/`update`/`remove`/`refs generate` command in the
`literature/` bullet below runs as: `"~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py"
<subcommand> ... --project PATH` (Mac/Linux: `~/.arti/python/bin/python3`). Each call prints one
JSON object (`{"ok": true, ...}` or `{"ok": false, "error": ...}`); see
`~/.arti/tools/arti-lit/README.md` for the full subcommand surface. Unlike `arti-db`, this is
per-project, not a cross-project singleton. The **`ARTi-ref`** skill is this CLI's sole owner —
`ARTi-writing` and `ARTi-idea` call into it rather than documenting the mechanics themselves.

**`arti-pdf-ingest` invocation** — batch-converts PDFs to `literature\fulltext\` Markdown and
registers each conversion in `arti-lit` (status `fulltext`) in one pass, instead of ingesting one
PDF at a time: `"~/.arti/python/python.exe" "~/.arti/tools/arti-pdf-ingest/cli.py" ingest --project
PATH --manifest PATH` (Mac/Linux: `~/.arti/python/bin/python3`). Requires each manifest row's `key`
to already exist in `library.md` — it never creates new library rows. See
`~/.arti/tools/arti-pdf-ingest/README.md` for the manifest format.

0. Create the standard paper-project folder layout in the project root, alongside `memory/` and
   `CLAUDE.md`:
   - `idea/` — ARTi-idea's outputs live here: `gap-map.md`, `idea-canvas.md`,
     `research-design.md`/`.pdf`, `journal-target-sheet.md`, `handoff.md`
     (the short handoff manifest — decisions and pointers, not copied content). One project = one
     paper, so none of these filenames carry a topic slug.
   - `writing/` — ARTi-writing's outputs live here:
     `journal-profile_[journal-abbreviation].md` (keeps its placeholder — a rejected paper can
     acquire a second target journal, so two profiles must be able to coexist),
     `manuscript-blueprint.md`, `scratchbook.md`, `manuscript_draft[N]_[date].md` (keeps its
     placeholder — draft versioning means several coexist), `iteration-log.md`,
     `references.md` (generated — see the `literature/` layer table below),
     `completion-plan.md`/`.pdf` (hand-maintained, created at Stage 4b — see ARTi-writing SKILL.md)
   - `literature/` — three layers, one shared key (`author-year[a|b]`, e.g. `kaw-2016`):
     - `literature\exports\` — raw downloads, **never renamed by the researcher**; Claude parses
       them and assigns the key
     - `literature\fulltext\` — PDFs and their `.md` conversions, named by key; PDFs land here
       either by hand or via a batch `arti-pdf-ingest` run once a manifest exists (see invocation
       above)
     - `literature\search-log.md` — one row per search round: query (bare, copy-ready) · date ·
       hits · export file · target claim/paragraph · status
     - `literature\library.md` — **generated export**, auto-regenerated on every `library
       add`/`update`/`remove` from `literature\arti-lit.db` (the canonical store, owned by the
       `ARTi-ref` skill — see its SKILL.md for the CRUD/fulltext/retrieval mechanics) — never
       hand-edit it directly. Canonical bibliography, one source per line (superset including
       screened-out sources), columns: key · full citation in the target journal's style · DOI ·
       local file path · read-status · used-in
     - **Legacy hand-maintained citation records** (e.g. a pre-`arti-lit` project's own
       `citation-map.md`/`references-final.bib` from before this project adopted `arti-lit`): mark
       them frozen/historical in project memory the moment `arti-lit` is adopted — do not treat them
       as a live store. `literature\arti-lit.db`/`library.md` are canonical for everything looked up
       or added after adoption; do not delete the legacy files (they remain the legitimate record of
       a finalized paper's citation decisions), and do not query them for a reference named after
       adoption — that goes through `ARTi-ref` (`library get`/`search`) instead.
   - `data/` — raw and processed research data
   - `figures/` — generated plots, images, and diagrams for the manuscript, plus
     `figures/figure-register.md` (one row per figure/table; seeded from `ARTi-figure/references/
     figure-register-template.md` the first time `ARTi-figure` is invoked in this project, not
     created empty at scaffold time — there's nothing to register yet)
   - `submission/` — the final formatted manuscript package:
     `cover-letter_[journal-abbreviation].md`, `rebuttal_[journal-abbreviation]_round[N].md`
     (both keep their placeholder for the same reason as the Journal Profile), `growth-log.md`,
     journal-formatted export, supplementary files
   - `inbox/` — (named "wdyt" — "what do you think?" — before 2026-09-09) raw-idea inbox: pure
     drop-and-forget capture, no structural expectation on content, no index, no rename, no
     archiving — for anything the researcher thinks might improve the project but that doesn't
     obviously belong to any existing document yet. `inbox/` is the one folder in a scaffolded
     project meant for the researcher to create and edit files in directly — everything else is
     Claude-managed.
     **Discovery:** presence in the folder *is* the "still open" signal — session start globs
     `inbox/*.md` and surfaces whatever is there. No separate index file to keep in sync.
     **Reviewing a file** ends one of three ways, decided in conversation, no ceremony: (a) worth
     keeping — fold it into the right place (a `memories/` topic file, an `idea-bank add` entry if
     it's a research idea, or `~/.arti/inbox/` if it's about the ARTi framework/skills themselves
     rather than this paper) and delete the raw file; (b) not worth keeping — delete it; (c) still
     undecided — leave it in place.
     **Verbatim researcher prose that *is* the content** (ebook narrative, landing-page copy,
     workshop material — as opposed to a note *about* something to decide) is never summarized,
     rewritten, or condensed, and isn't deleted once used. Record where it's been used with one
     `<!-- used-in: ... -->` comment at the top of the file itself.
     A capture worth cross-project tracking can be added to `~/.arti/inbox/idea-index.md` via
     `idea-index upsert` — an available action for something genuinely worth tracking across
     projects, not a step every file goes through.

   Note: ARTi-writing's Voice Profile is deliberately **not** in this project's `writing/` folder
   — it's cross-project and lives in `~/.arti/voice-profiles/`, alongside the Researcher Profile and
   Research Idea Bank (created by this skill's Workflow A).
   Seed `literature\search-log.md` as a header-only file; create `literature\exports\` and
   `literature\fulltext\` empty. Do not hand-seed `literature\library.md` — run `arti-lit init
   --project PATH` (or let it lazily run on first `library add`) to create the empty `library.md`
   export itself, backed by `literature\arti-lit.db`. `data/` holds raw and processed research
   data — data-collection instruments, pretest/posttest packets, and scoring keys belong in
   `data/instruments/`, not `writing/`, even though they're referenced from the Methods section:
   placement follows what a file *is* (a data-collection artifact), not who cites it. All other
   folders are created empty (no placeholder files) except where a later step in this template
   populates one. This layout is the same across every ARTi paper project — do not deviate from
   these seven folder names.

1. Create a `memory/` folder in the project root with exactly three files flat at its top level —
   the T0 set, read every session:
   - `memory/MEMORY.md` — the index: pointers only, one line each (hard-capped — no line restates
     another file's content), never content itself
   - `memory/todo-list.md` — **checklist only**: the contiguous `- [ ]` / `- [x]` task list, one
     line per item, grouped by phase or milestone if the project has them. No narrative, no session
     write-ups, no multi-line continuation under an item — if a line isn't a checkbox item (or a
     short blocking-condition note), it belongs in a `memories/` topic file, linked with
     `[[slug]]`. No `## Change log` section — git history covers edits to this file. A phase's
     checked items get deleted once it's closed and captured in a topic file; this file tracks
     outstanding work, not history. Search keywords and query lists belong in
     `literature\search-log.md`, not here.
   - `memory/status.md` — the living narrative, but only as a pointer: **one overwritten "Current
     state" block at the top** (replaced in place each session, never stacked alongside older
     "Current state" / "Next session" blocks), 2-4 sentences naming what changed and a
     `[[topic-file]]` link for every detail — the topic file carries the actual report (what was
     verified, what was decided), not this block. No Archive section and no `## Change log` section
     here either — the linked topic file's own change log and git history already cover it.
     `todo-list.md` stays pure checklist so its name keeps meaning what it says.

   Every other memory file — one per topic, T1, read on demand — goes in `memory/memories/`, not
   flat in `memory/`. Don't create `memories/` empty at scaffold time; create it the first time a
   topic file would actually land in `memory/` (a paper project may run its whole life on just the
   three T0 files above plus what's already tracked in `idea/`/`writing/`/`literature/`). This is
   the T0/T1 tiering rule made physical instead of just documented — applied identically to a
   long-running meta-project's own `memory/` (see that project's own scaffold, not this template,
   for its one deliberate addition).

   That is the whole memory scaffold for a paper project. Deliberately **not** created, on any ARTi
   project this template scaffolds — paper project or meta-project alike:
   - `goal.md` — a paper project's purpose already lives in the Idea Canvas's confirmed research
     question and the Research Design's objective; a meta-project's purpose is a short "Project
     goal" section folded directly into `MEMORY.md` instead of a separate file. Either way, a
     second free-standing statement of purpose drifts out of sync with the first.
   - `history.md` — a cross-topic chronological log duplicates the per-file change logs already
     living in `memory/memories/` topic files; it earns its keep nowhere in this convention,
     meta-project included.

2. Create `CLAUDE.md` in the project root by copying
   `references/project-claude-template.md` and substituting `{{PROJECT_NAME}}`. That template is
   the single source of truth for a project `CLAUDE.md` — the dashboard scaffolder
   (`~/.arti/dashboard/server/server.py`) renders the same file, so describing the required
   sections a second time here would only give the two copies somewhere to drift apart.
   Everything below the `<!-- arti: local additions below -->` fence is project-owned and is
   preserved on regeneration; everything above it is canonical and machine-owned.

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
     `status.md`, `CLAUDE.md`) — hard budget **~20 KB total**. T1 = read on demand, in
     `memory/memories/`, no budget, but the rule/evidence split below is required. T2 = archive,
     never auto-read. A T0 file that exceeds its budget gets compacted at the next wrap-up ritual,
     not left to grow.
   - **Tables for any repeated-structure list** — session pointers, findings, references, search
     rounds. Prose enumeration of parallel items is the largest source of bulk in practice.
   - **Change log = one line per date, ≤120 chars, naming *what changed*** — never re-summarizing
     the file's own content. Keep ~10 entries; collapse older ones to one "created and iterated
     through `<date>`" line. Exception: `status.md` and `todo-list.md` carry no `## Change log`
     section at all — git history covers edits to the tracker itself, and the substantive record
     already lives in the `memories/` topic file each entry links to.
   - **Rule/evidence split for behavioral files.** Imperative one-line rules at the top; narrative
     evidence below or in a T2 archive — never the reverse.
   - **One-sentence index lines, hard-capped.** Detail lives in the linked file, not in the index.
   - **No cross-file restatement.** A sentence summarizing another file's content becomes a
     `[[slug]]` link instead.
   - **Living state is overwritten, not appended.** One current block; superseded blocks are
     deleted, and the change log carries the fact that they existed.
   - **Cut meta-narration.** Record the decision and its date; drop commentary on why it was
     recorded.
   - **Avoid closing-sentence restatement.** A paragraph's last sentence should add information,
     not re-say what its first sentence already established.
   - **Lossless-compaction rule.** A compaction pass may remove prose bulk only. It must preserve,
     verifiably, every: decision · date · open `- [ ]` item ·
     `[UNVERIFIED]`/`[DATA NEEDED]`/`[SOURCE NEEDED]` flag · file path · `[[link]]`. Before/after
     sets of those items must be identical.

4. Link related memory files with `[[slug]]` references rather than duplicating content across
   files. This convention also extends across projects when genuinely needed: a relative-path form,
   e.g. `[[../Paper Metnum ECE/memory/memories/gap-map]]`, lets one project's memory point at
   another's without copying content. Use this only for a real, specific cross-reference — not as a
   substitute for a shared cross-project store like `research-idea-bank.md` or `figure-style.md`.

5. If this conversation already contains project context worth persisting (decisions made,
   constraints established, background explained), create the first topic file(s) now and populate
   the index — don't leave it empty. Otherwise leave the index scaffolded and empty, ready for the
   first real memory. The same applies to `todo-list.md` and `status.md`: if there is enough
   context to draft real tasks or a real Current-state block, draft them rather than leaving empty
   scaffolding.

6. Run `project upsert --stage "Not started" --status "Scaffolded"` for this project — this ties
   the new project into the researcher's cross-project dashboard. After this, the index is updated
   at **phase boundaries only**: idea complete, writing started, submitted.

7. **Session-end wrap-up ritual.** Any phrasing that means "we're done for now" — not only the
   exact words "update memory" — fires this fixed checklist: update the relevant project memory
   file(s) · **only if the session moved outstanding work or produced a state change worth
   recording**, overwrite `status.md`'s "Current state" pointer and/or check off/add any
   `todo-list.md` items — a session that was pure discussion, research, or Q&A with no checklist or
   state change skips both files entirely, there is nothing to overwrite · **check whether a phase
   boundary (idea complete / writing started / submitted / published) was crossed this session and,
   if so, run `project upsert` for this project's row** — this is what keeps the cross-project
   dashboard current; a session that changes stage/status but skips this leaves the dashboard
   showing stale data even though every project file is up to date · write any correction on *how*
   to work straight into `~/.arti/memory/working-preferences.md`, the same turn it's given, never
   deferred to session end · check whether a recurring loop should be logged or updated in
   `~/.arti/memory/memories/ebook-notes.md`'s
   micro-flow catalog (once a loop repeats a second time, write it up). Skipping the ritual because
   the trigger phrase wasn't the exact one used before is the failure mode this step exists to
   close.

8. **Surface standing asks at session start.** If any memory file records an open question Claude
   was supposed to ask the researcher (e.g. "ask whether an Iteration Log entry is wanted"), ask it
   near the start of the session rather than merely re-recording that it's still open. Same
   pattern for `inbox/`: glob it and surface any file sitting there.

Confirm the folder and file layout once done.
