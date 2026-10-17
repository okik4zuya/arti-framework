---
name: ARTi-demo
description: >
  Runs the ARTi Framework showcase end to end, unattended: from one topic to a finished Word manuscript with Zotero
  citation fields, in about an hour. Literature search across OpenAlex, Semantic Scholar and Google Scholar, DOI dedup,
  PRISMA-ScR screening, open-access full-text download with an abstract-level fallback, classification and data
  aggregation, figures (PRISMA flow, landscape, classification, graphical abstract), tables, journal selection,
  scratchbook, draft, reference verification, and a scoreboard of what was done. Use when the researcher says "run the
  ARTi demo", "jalankan demo ARTi", "demo ARTi", "show what ARTi can do", or wants a client demonstration of the whole
  framework. Asks exactly one question (the topic), then works without stopping. Do NOT use for a real paper: this skill
  installs a demo researcher profile and a demo voice profile only when none exist, and labels the manuscript a demo output.
---

# ARTi-demo

A scripted tour of ARTi for a client or a first-time user. One command, one question, one finished manuscript.

## The one question

Before any tool call, unless the request already names a topic ("jalankan demo ARTi, topik X"): ask **one**
`AskUserQuestion` with the topic only. Options: the default (AI and large language models for literature screening and
evidence synthesis), two broad examples from other fields, and the automatic "Other" for free text. After the answer there
is **no second question** for any reason. What would normally need the researcher follows
`references/gate-overrides.md`. If the run cannot continue at all (no internet, a core tool missing), end it with a clear
message instead of asking.

## What to do

1. Read `references/runbook.md` and follow it phase by phase (0 to 11). It names every command, file and cap.
2. Read `references/gate-overrides.md` once before phase 1, and `references/classification-schema.md` before phase 3.
3. Log every phase with `scripts/run_log.py phase` (the scoreboard is built from that log), every autonomous decision
   with `run_log.py decision`, every fallback with `run_log.py problem`.
4. Finish with `scripts/scoreboard.py` and the final message described at the end of the runbook.

## Rules that never bend

- Always the vendored interpreter by full path (`~/.arti/python/python.exe`, or `~/.arti/python/bin/python3`). A bare
  `python` has nothing to resolve to on a client machine.
- Numbers come from files the tools wrote; citations only when the DOI resolved; no invented value or reference.
- The title page carries "ARTi demo output: generated unattended, not peer reviewed".
- Stay inside the caps (100 records, 13 full-text attempts, 4 numbered figures plus a graphical abstract, 2 tables, about
  4,000 words). A step that fails uses its fallback and the run goes on.
- Figures are not monotonous: before phase 7 read `references/figure-variety.md` and look at the reference images in `templates/`;
  every figure gets a different form, and the reference images are never copied.
- The manuscript `.docx` is always built from `~/.arti/tools/arti-docx/assets/default-academic-template-zotero.docx`
  (the template that ships with the `arti-docx` tool, passed explicitly with `--template`). No copy of it lives in this
  skill, and no other template is used.
- Never overwrite a real researcher profile or voice profile (`seed_profiles.py` only fills gaps).
- Nothing here changes how the other skills behave outside this skill.

## Presenter checklist (read this to the researcher only if asked, or if preflight shows a problem)

- Permission mode that does not stop for every file edit (accept edits or bypass), because the run writes hundreds of files.
- Open Claude Code in an empty folder of your choice (the run writes everything there: `data/`, `figures/`, `writing/`,
  `submission/`, `demo-scoreboard.md`), **not** in `~/.arti` (that folder loads the framework's own maintenance rules). One folder, one demo run.
- Internet access. Optional keys in the dashboard under Settings > APIs (OpenAlex, Semantic Scholar): without them the run
  uses the anonymous pools and open-access links, with fewer Semantic Scholar results. With an OpenAlex key, full texts
  come from OpenAlex's cache at $0.01 per file (at most 13 files, so $0.13 for the run).
- Microsoft Word with the Zotero plugin on the presenting machine, to show Refresh restyling the citations.
- An interrupted run resumes: say "jalankan demo ARTi" again with the same topic and it continues after the last logged phase
  (`scripts/run_log.py status --project <PROJ>`).

## Files

| File | What |
|---|---|
| `references/runbook.md` | The twelve phases, commands, caps, fallbacks |
| `references/gate-overrides.md` | Autonomous rule for each researcher-confirmation gate in the other skills |
| `references/classification-schema.md` | The four labels each included record gets |
| `references/demo-researcher-profile.md`, `references/demo-voice-profile.md` | Placeholders installed only if the real ones are missing |
| `references/scoreboard-template.md` | Layout of `demo-scoreboard.md` |
| `references/figure-variety.md` | Rules for varied figure forms, with the four reference images in `templates/` (`Fig_1_materials`, `Fig_3_trend`, `Fig_4_band_edges`, `graphical-abstract`) |
| `templates/prisma-flow.html` | PRISMA-ScR flow for `arti-compose` |
| `scripts/` | preflight, seed_profiles, scaffold_project, screen, aggregate, build_fig_*, verify_refs, check_docx, run_log, scoreboard |

Tests: `tests/demo/test_pipeline.py` (synthetic data; `ARTI_TEST_LIVE=1` adds the Zotero round trip).
