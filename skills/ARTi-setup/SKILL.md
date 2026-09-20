---
name: ARTi-setup
description: >
  One-time cross-project setup and per-new-project scaffolding for the ARTi research workflow.
  Use this skill when: onboarding a new researcher to ARTi for the first time (creating the
  persistent ~/.arti data folder and Researcher Profile), starting a brand-new research project
  and wanting its local memory system scaffolded, or when ARTi-idea/ARTi-writing reports that
  ~/.arti or the Researcher Profile doesn't exist yet. Triggers include: "set up
  ARTi", "new research project", "onboard me to ARTi", "create the ~/.arti folder", "set up my
  researcher profile", "scaffold this project's memory". Run this before ARTi-idea if
  `~/.arti/memory/researcher-profile.md` doesn't exist yet.
---

# ARTi-setup Skill

Owns two workflows: one-time cross-project setup for a researcher, and per-new-project
scaffolding. Both used to live as Stage 0/1 inside `ARTi-idea`; they're pulled out here so a
researcher can be onboarded or a project scaffolded without starting an idea-development session.

---

## Workflow A — One-Time Cross-Project Setup

Runs once per researcher, not once per project. Produces the persistent `~/.arti` data folder and
the Researcher Profile.

**Fixed location, no longer a researcher decision.** `~/.arti` (`C:\Users\<user>\.arti\` on
Windows, `~/.arti` on Mac/Linux) is the single cross-project home for everything that isn't a
specific paper project — both ARTi tooling (vendored Python, `tools/`, `skills/`, installed via
the separate `install.ps1`/`install.sh` in the `arti` repo) and researcher content
(`researcher-profile.md`, `voice-profiles/`, `inbox/`, etc.). It mirrors where Claude
Code itself keeps `~/.claude`. Unlike the old Drive-based `_ARTi` folder, this path is never asked
about or confirmed with the researcher — it's the same on every machine. What *is* still the
researcher's free-form choice, entirely separate from `~/.arti`, is where each individual paper
project lives (Drive, Dropbox, a bare local folder) — see Workflow B.

**Steps:**
1. Check whether `~/.arti` already exists and has `researcher-profile.md`. If so, load and reuse
   it (step 4 below) rather than re-running setup. `~/.arti` itself (the `python/`, `tools/`,
   `skills/` parts) is created by running `install.ps1` (Windows) or `install.sh` (Mac) from the
   `arti` tooling repo, not by this skill — if those are missing, tell the researcher to run the
   installer first, since this skill only manages researcher-content subfolders.

   **Every Python-backed command below (`arti-db`, `arti-lit`, …) must run through the vendored
   interpreter, never a bare `python`/`python3`/`py`** — nothing on the researcher's machine puts
   it on `PATH` (deliberate, to avoid clashing with any system Python), so a bare invocation has
   nothing to resolve to on a clean install. Use the full path:
   `"~/.arti/python/python.exe" <script>.py ...` (Windows) or
   `~/.arti/python/bin/python3 <script>.py ...` (Mac/Linux) — or the shorter top-level wrapper the
   installer also creates, `~/.arti/python.cmd` / `~/.arti/python3`, if the subpath is forgotten.
2. Run `arti-db init` (see Reference Files for the invocation) — it creates `~/.arti/memory/arti.db`
   and, if the legacy `research-idea-bank.md`/`project-index.md`/`inbox/idea-index.md` files exist
   already, one-time migrates them; either way it also (re)generates all three `.md` files from the
   database, so this single command replaces the old by-hand "create these markdown files" step.
   Also create empty `journal-library\` and `voice-profiles\` folders. `voice-profiles\` holds ARTi-writing's
   per-researcher Voice Profile files (Stage 0 of that skill) — created empty here, populated the
   first time ARTi-writing needs one.
   Also create `inbox\`, empty — the cross-project raw-idea inbox, pure drop-and-forget capture
   for the **ARTi framework/skills themselves** (new skill ideas, workflow friction, tooling gaps),
   distinct from `research-idea-bank.md` (research ideas for future papers). No index, no rename,
   no archiving — same convention as a per-project `inbox/` (see
   `references/project-scaffold-template.md`): presence in the folder is the "still open" signal.
   A per-project `inbox/` file that turns out to be about the framework rather than that paper
   moves here instead. A capture worth cross-project tracking can be added to
   `inbox\idea-index.md` via `idea-index upsert` — an available action, not a mandatory step.
   Also seed two files if missing:
   - `working-preferences.md` (flat in `memory/`, a cross-project singleton) — normally already
     seeded by `install.ps1`/`install.sh` (missing-only copy of `references/
     working-preferences-default.md`, same pattern as `figure-style.md`'s install-time seed); if
     it's somehow still missing when this skill runs (an install predating this seeding step),
     copy `references/working-preferences-default.md` here rather than starting from a blank
     header — the framework-level rules in that default (e.g. cross-project discovery) must ship
     by default, not depend on a researcher correction happening first. One rule per line from
     there on, `- **<rule as an instruction>** — (since YYYY-MM-DD, session N)`, grouped by output
     mechanics / interaction style / file and naming conventions / session-end ritual. Read at the
     start of every ARTi session. Written to in the same turn a researcher corrects Claude on *how*
     to do something — never deferred to session end.
   - `memory/memories/ebook-notes.md` (T1, occasional-read) — two sections: a low-ceremony
     chapter/topic idea dump, and a micro-flow catalog (name · trigger · steps as performed ·
     friction points · time cost · tooling opportunity). Once a recurring loop repeats a second
     time, write it up here.
3. If `~/.arti/memory/researcher-profile.md` doesn't exist, run the interview: ask the researcher directly
   for every field in `references/researcher-profile-template.md` (Sections A–G) — never infer,
   flag vague answers and probe further. Derive Section H (Novelty Ceiling for C/M/E) immediately
   after, following the ceiling-derivation logic described in that template. Section I
   (Positioning Line) is left blank — ARTi-idea writes it later, on first Research Idea Bank entry.
   If it already exists, load and reuse it — skip re-asking, only confirm nothing has changed.
   **Maintenance trigger for Sections A–G and `Last Updated`:** revisit them (not just Section H)
   when the researcher reports new instrument capability, a new collaborator, or deeper literature
   familiarity — the same circumstances already named for Section H. Nothing else updates these
   sections after creation, so without this trigger the profile goes stale silently.

   **Section H is derived here and only here.** Every downstream stage — ARTi-idea's novelty
   scoring and ceiling checks, ARTi-writing's Block D — *reads* the ceiling from Section H and
   must not re-derive it. Re-deriving it produces a second, divergent ceiling for the same
   researcher. Revise Section H only when the researcher's circumstances actually change
   (new equipment, new collaborator, deeper literature familiarity) — and revise it here.

---

## Workflow B — New Project Scaffolding

- Confirm `~/.arti` setup exists (`researcher-profile.md` present); if not, run Workflow A
  first — one coherent onboarding flow, not two disconnected features.
- Follow `references/project-scaffold-template.md` to create the new project's standard folder
  boilerplate — `idea/`, `writing/`, `literature/`, `data/`, `figures/`, `submission/`, `inbox/` —
  plus a `memory/` folder holding `MEMORY.md`, `todo-list.md` (checklist only), and `status.md`
  (a short overwritten Current-state pointer, no archive) flat, with any topic files under `memory/memories/`
  (see the template's tiering rule), and a root `CLAUDE.md`.
  This layout is identical across every ARTi paper project — don't invent a different one.
- **Keep the paper-project memory scaffold light.** No `goal.md` (the Idea Canvas and Experiment
  Blueprint already state the goal) and no `history.md` (per-file change logs already carry the
  chronology). The generated `CLAUDE.md` must not impose the five-step timestamp ritual used by
  the ARTi meta-project — on a single manuscript it is overhead, not discipline. Frontmatter
  `created`/`updated` plus a per-file `## Change log` line is the whole rule.
- The root `CLAUDE.md` comes from `references/project-claude-template.md` with
  `{{PROJECT_NAME}}` substituted — the single source of truth the dashboard scaffolder renders
  too. Regeneration preserves everything below the `<!-- arti: local additions below -->`
  fence; anything project-specific belongs there, not above it.
- Run `project upsert --stage "Not started" --status "Scaffolded"` for this project's row. After
  that, the index is updated at phase boundaries only — idea complete, writing started, submitted.
- Also pass `--summary` (a keyword-style listing of the project's actual memory sub-topics, not
  just its headline research question — this is what makes cross-project topic lookup via
  `project list` work). Refresh it whenever stage/status changes meaningfully, the same way
  `status` itself is kept current — not a one-time-at-scaffold field.
- Confirm the folder/file layout once done (same closing instruction as
  `references/project-scaffold-template.md`).

---

## Cross-cutting session convention — project-index upsert

Applies regardless of which skill is active: at the end of any session that changed a child paper
project's stage or status (idea complete, writing started, submitted, published, or similar), run
`project upsert` for that project's row before ending the session. This is a generic catch-all —
`ARTi-idea` and `ARTi-writing` also carry their own stage-specific reminders to upsert earlier,
during the work itself; this one exists so the dashboard stays current even if a skill's own
reminder is missing or gets skipped. When stage/status changes meaningfully, also consider whether
`--summary` needs refreshing to reflect what the project's memory now covers.

---

## Reference Files

- `references/researcher-profile-template.md` — blank Researcher Profile with all fields,
  including the Positioning Line
- `references/project-scaffold-template.md` — the project memory-scaffolding procedure (`memory/`
  folder + root `CLAUDE.md`)

**`arti-db` invocation** — every `arti-db init`/`project upsert` command above runs as:
`"~/.arti/python/python.exe" "~/.arti/tools/arti-db/cli.py" <subcommand> ...` (Mac/Linux:
`~/.arti/python/bin/python3`). Each call prints one JSON object (`{"ok": true, ...}` or
`{"ok": false, "error": ...}`); see `~/.arti/tools/arti-db/README.md` for the full subcommand
surface. Never hand-edit `project-index.md`, `research-idea-bank.md`, or `idea-index.md`
directly — all three are generated exports, overwritten on every write.

Read the relevant reference file before starting either workflow.
