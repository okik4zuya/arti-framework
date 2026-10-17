# ARTi-demo runbook

Twelve phases, about 60 minutes. Each phase ends with `run_log.py phase`, so an interrupted run resumes at the first
unfinished phase (`run_log.py status`). Gates that would normally ask the researcher: `gate-overrides.md`. Labels for
included records: `classification-schema.md`.

## Conventions used below

- Home folder: `~` means the user's home (`C:\Users\<user>` on Windows). `ARTI` = `~/.arti`.
- `PY` = `"ARTI/python/python.exe"` (Windows) or `ARTI/python/bin/python3` (Mac/Linux). **Never** a bare `python`.
- `SK` = `ARTI/skills/ARTi-demo` (scripts in `SK/scripts`).
- `S` = `PY "ARTI/tools/arti-search/cli.py"`; `L` = `PY "ARTI/tools/arti-lit/cli.py"`.
- `PROJ` = the working folder Claude Code was started in (the current directory, as an absolute path). Every path below is inside it unless it starts with `ARTI` or `SK`. Nothing is written to `~/ARTi-demo` or any other folder.
- Write each Boolean query to a file and pass `--query-file`; add `--out` for anything large (see `search-routing.md`).
- After a phase: `PY SK/scripts/run_log.py phase --project PROJ --n N --name "..." --status done --note "one line with the key numbers"`.
- Anything that fails: apply the fallback in the last column of the phase table, log it with
  `run_log.py problem --project PROJ --text "..."`, and go on. Do not stop, do not ask.

## Caps (do not exceed)

100 records identified, 13 full-text attempts (10 for the corpus, 3 for the journal profile), 4 numbered figures plus one
graphical abstract, 2 tables, about 4,000 words, 2 render iterations per figure.

---

## Phase 0: question, preflight, project (3 min)

1. Topic: unless the invocation already contains one, ask **one** `AskUserQuestion` (the only question of the run) with
   the topic as `header`; options: "AI and large language models for literature screening and evidence synthesis (default)",
   "Microplastics in freshwater: detection methods and ecological effects", "Machine learning for crop yield prediction",
   and the automatic "Other" for free text. Everything after this is autonomous.
2. `PROJ` = the current working directory (absolute path). No `<slug>` subfolder is created. If `PROJ` is `~/.arti` or inside it, end the run with the message "open Claude Code in a separate empty folder, not in ~/.arti". If `PROJ` already holds a demo run (`run_log.py status --project PROJ` shows phases), that is a resume, so continue it; for a different topic in a non-empty folder, tell the presenter to use another empty folder.
3. `PY SK/scripts/preflight.py`. `STATUS: FATAL` ends the run with that message (no internet, or a core tool missing);
   `WARN` continues, using the fallbacks named in the table.
4. `PY SK/scripts/seed_profiles.py` (never overwrites).
5. `PY SK/scripts/scaffold_project.py --path PROJ --name "<topic>"` (ARTi-setup Workflow B: folders, memory trio, `CLAUDE.md`, index row).
6. `PY SK/scripts/run_log.py init --project PROJ --topic "<topic>"`. Then write the three research questions into
   `idea/rq.md`: RQ1 how the topic's literature has grown and where it is published, and how open it is; RQ2 which approaches
   are used for which tasks; RQ3 what kind of evidence stands behind them and how much was read in full.

## Phase 1: idea (8 min). ARTi-idea, compressed

1. Researcher Profile is read, not asked: `~/.arti/memory/researcher-profile.md`, Section H gives the novelty ceiling.
2. Pilot search (not imported): write `data/query-pilot.txt`, then
   `S search --query-file data/query-pilot.txt --max 30 --year-from <this year - 5> --out data/pilot.json`.
   Read titles and abstracts from the file. Build `idea/gap-map.md` from the template
   (`ARTi-idea/references/gap-map-template.md`): at least one gap, at least three supporting sources, and say why it matters.
3. Idea Canvas (`idea/idea-canvas.md`): 3 candidate ideas, each scored C/M/E against the ceiling; pick by `gate-overrides.md`;
   park the others with `arti-db idea-bank add`. Research design in one paragraph (`idea/research-design.md`): a scoping
   review with a bibliometric part, PCC framing, the three RQs.
4. Cross-citation check: choose two clusters from the gap map (3-6 DOIs each), write them to `data/set-a.txt`, `data/set-b.txt`, run
   `PY ARTI/tools/citation-chase/cli.py run --set-a-file data/set-a.txt --set-b-file data/set-b.txt --out data/crosscite.jsonl`.
   State the result (overlaps or none) in the gap map's novelty line, as the ARTi-crosscite skill requires.
5. Journal: `PY ARTI/tools/arti-jfinder/cli.py journal categories` to find the closest category text, then
   `journal search --category "<text>" --quartile Q1 --limit 15` (and `--keyword`); shortlist 3-5; per `gate-overrides.md`
   pick one and a fallback. Aims and scope: `scope get`; if empty, WebFetch the journal's site and `scope set`. Write
   `idea/journal-target-sheet.md` (template in ARTi-idea). Note the journal's ISSN for phase 5.
6. Close the phase with the chosen journal and idea in the `--note`. `arti-db project upsert --stage "Idea complete"`.

Fallbacks: no `arti-jfinder.db` content -> choose from general knowledge and mark "unchecked" in the sheet; WebFetch not available ->
use the Scimago categories only; citation-chase error -> record "not checked" and do not claim a gap of "never cross-cited".

## Phase 2: search (6 min). arti-search, arti-lit

1. `S sources`: note which routes are live.
2. Main query: `data/query-main.txt` (2-3 facets, quoted phrases, `OR` inside a facet, `AND` between). Landscape counts (whole
   OpenAlex, same query and year range):
   `S count --query-file data/query-main.txt --year-from Y --group-by publication_year --out data/openalex-year.json`, and the same
   with `--group-by open_access.oa_status --out data/openalex-oa.json` and
   `--group-by primary_location.source.id --out data/openalex-source.json`. Use `--year-from` = this year minus 10.
3. Records: `S search --query-file data/query-main.txt --max 70 --year-from Y --ris literature/exports/openalex.ris --snapshot data/snapshot-openalex.json --out data/search-openalex.json`.
   Semantic Scholar if the key is set: `S s2-search --query "<4-6 words>" --max 20 --ris literature/exports/s2.ris --out data/search-s2.json`.
   Google Scholar, at most two queries, stop at the first refusal: `S scholar --query "<phrase>" --max 10 --ris literature/exports/scholar.ris --out data/search-scholar.json`.
   The `ris.records` number in each summary is that source's "identified" count.
4. One import for all files (DOI dedup works across them): `L library import-ris --files literature/exports/openalex.ris,literature/exports/s2.ris,literature/exports/scholar.ris --project PROJ`
   (list only the files that exist). `duplicates removed` = records in the files minus `imported`. If more than 100 were imported, that is
   fine only up to the cap: otherwise drop the surplus with `library remove`.
5. `literature/search-log.md`: one row per query: bare query, date, hits, export file, target "RQ1-RQ3", status `DEMO-AUTO`.
6. Keep three numbers for phase 3: identified per source, duplicates removed.

Fallbacks: OpenAlex only is enough; skip Scholar and S2 when `sources` says cooldown or no key; zero imported -> widen the query once, then end the run with that message.

## Phase 3: screening (6 min). PRISMA-ScR

1. `data/screening-criteria.md`: inclusion (addresses the topic; primary study, review or tool description; has an abstract that
   states a method or a result; 2015 or later; English) and exclusion codes E1 off topic, E2 no method or result stated,
   E3 not a research output (editorial, erratum, dataset), E4 duplicate of an included record, E5 other.
2. Vocabulary for the labels: `classification-schema.md`, from the first 20 abstracts. Save `data/classification-vocabulary.md`.
3. Loop until nothing is unscreened: `PY SK/scripts/screen.py dump --project PROJ --out data/screening-batch-N.md --limit 50`, read it,
   write `data/decisions-N.csv` (columns `key,stage,reason,search_source,task,method,field,evidence`; stage is `included`,
   `excluded_title_abstract` or `excluded_eligibility`; labels only for included rows; `search_source` such as `DB:openalex` or `OTHER:s2`),
   then `PY SK/scripts/screen.py apply --project PROJ --decisions data/decisions-N.csv`. Fix any `unknown_keys` or `bad_stage` it reports.
   Both gates are applied in this one pass: title/abstract first, then eligibility at abstract level (full texts only for a subset, phase 4).
4. `PY SK/scripts/screen.py counts --project PROJ --out data/prisma-counts.json --identified openalex=N --identified s2=N --identified scholar=N --dups D`.
   `unfinished_rows` must be 0.

## Phase 4: full text ladder (6 min)

1. `screen.py dois --project PROJ`, then `S resolve --items-file data/included-dois.txt --project PROJ --out data/resolve-included.json`.
2. `screen.py fulltext-items --project PROJ --resolved data/resolve-included.json --max 10 --out data/fulltext-items.json`.
3. `S fulltext --project PROJ --items-file data/fulltext-items.json --max-files 10 --out data/fulltext-result.json`
   With an OpenAlex key the `auto` source uses OpenAlex's cached PDFs, which cost $0.01 per file (at most $0.13 for the run); `--source oa_location`
   uses publisher and repository links only, free, with fewer hits. Without a key `auto` falls back to `oa_location` by itself.
4. `screen.py manifest --result data/fulltext-result.json --out literature/fulltext/manifest.csv`, then
   `PY ARTI/tools/arti-convert/cli.py ingest --project PROJ --manifest literature/fulltext/manifest.csv --source-dir literature/fulltext --keep-source-pdf`.
5. Everything not downloaded stays at read status `abstract`. That ratio is a result of the review, not a failure: state it as such.
6. Read the converted full texts selectively (sections on methods and results) and keep short notes for phase 8.

Fallbacks: no PDF available at all -> continue; the manuscript then says every source was assessed from the abstract only.
PDF without a text layer and no OCR (`bin/` missing) -> treat as not downloaded.

## Phase 5: light Journal Profile and Blueprint (5 min). ARTi-writing stages 1-2

1. Three open-access articles of the target journal: `S search --source-issn <ISSN> --oa-only --has-content-pdf --work-type article --year-from <this year - 3> --sort citations --max 6 --ris literature/exports/journal-sample.ris --out data/journal-sample.json`; take the first three that
   resemble a review or a bibliometric study if there are any, otherwise the first three. Import with `import-ris`, then a decisions CSV
   with `stage=outside_flow` and `search_source=OTHER:journal-profile` through `screen.py apply`, then `S fulltext` and `arti-convert ingest` for these three (counts toward the 13).
2. `writing/journal-profile_<abbr>.md` from `ARTi-writing/references/journal-profile-template.md`: first line `light (3 papers)`; Block A from the
   aims-and-scope and author guidelines (WebFetch; if unavailable from the Scimago row and common defaults, flagged), Block B pointing to `~/.arti/voice-profiles/demo-generic.md`, Blocks C and D from the three papers in one pass.
3. `writing/manuscript-blueprint.md`: paragraph-level outline for the sections in phase 8, journal-specific where the three papers show a pattern.
4. `arti-db project upsert --stage "Writing started" --target-journal "<journal>"`.

Fallbacks: fewer than three open-access articles -> use abstracts and say `abstract-level` in Block C; no author guidelines -> default Block A (abstract 250 words, 5 keywords, Fig/Table captions, numbered references) and flag it.

## Phase 6: classification and aggregation (6 min)

1. Re-read the vocabulary; merge values used by fewer than two sources into `other` (edit `data/classified.csv` by re-applying a corrected decisions file).
2. `PY SK/scripts/aggregate.py --project PROJ`. It refreshes access (full text or abstract), journal and year from arti-lit and writes every CSV and
   `figures/Table 1.json`, `figures/Table 2.json`.

## Phase 7: figures and tables (8 min). ARTi-figure

Run `screen.py counts` again first (the full-text numbers changed in phase 4), then:

| Output | Command | Then |
|---|---|---|
| Fig. 1 PRISMA-ScR flow | `PY SK/scripts/build_fig_prisma.py --project PROJ` | read the compose lines, look at `figures/Fig_1.png` |
| Fig. 2 landscape (3 panels) | `PY SK/scripts/build_fig_landscape.py --project PROJ` | same, `figures/Fig_2.png` |
| Fig. 3 and Fig. 4 | `PY SK/scripts/build_fig_classification.py --project PROJ` | look at both PNGs |
| Graphical abstract | `PY ARTI/tools/arti-compose/compose.py --new graphical-abstract --src figures/src/graphical-abstract.html`, edit, then `--src figures/src/graphical-abstract.html --out-dir figures` | view `figures/graphical-abstract.png` |
| Table 1, Table 2 | `PY ARTI/tools/arti-table/render.py --spec "figures/Table 1.json" --out-dir figures` (and Table 2) | read the Markdown |

Before building, read `figure-variety.md` and look at the four images in `templates/`: the figures must differ in form (no two
the same chart type or layout), one multi-panel figure mixes two chart types, and the default build scripts are only a starting point.

Graphical abstract: not the same strip every run; choose a cycle, hub-and-spoke, central overlap, funnel with branches or timeline
arc per `figure-variety.md`. The default layout, if no other fits, is three zones left to right. Input: a funnel or stack icon with the number of records identified. Process: four small
tags for the four labels (task, approach, field, evidence). Result: two or three numbers that matter (sources included; share read in full; the most
common approach). Colours from `figure-style.md`. Obey the ARTi-figure rule: no sentences, only a title, one- or two-word labels, numbers and units,
at least 24 px text. Numbers come from `data/prisma-counts.json` and `data/*.csv`.

For every figure: read the compose WARN/FAIL lines, view the PNG, fix at most twice, and register it in `figures/figure-register.md`.
A figure that still fails after two tries stays out of the manuscript and goes in the log as a problem. Image integrity rules apply (no retouching).

Fallbacks: no Edge or Chrome -> Fig. 3 and 4 (matplotlib) still render; skip Fig. 1, Fig. 2 and the graphical abstract, say so, and build the PRISMA numbers into Table 1's caption instead.

## Phase 8: scratchbook and manuscript (10 min). ARTi-scratchbook, ARTi-writing

1. `writing/scratchbook.md` from `ARTi-scratchbook/references/scratchbook-template.md`, sections as in the Blueprint. `[OWN]` for every computed number, with the data
   file in brackets (for example `[OWN: data/coverage.csv]`); `[LIT: key]` for literature, rewritten in your own words (no copied sentences). Cite abstract-only sources only for
   what their abstract states. At least twelve literature entries across the sections, drawn from the included records, at least four of them from full-text sources.
2. Manuscript `writing/manuscript_draft1_<yyyy-mm-dd>.md`, in the demo-generic voice and the journal profile's section order: title; one line
   "ARTi demo output: generated unattended, not peer reviewed"; Abstract; Keywords; 1 Introduction (four paragraphs, ending with RQ1-RQ3); 2 Methods (the exact query strings from `data/query-*.txt`, sources,
   dates, screening criteria, classification, abstract-level limitation); 3 Results (3.1 landscape and Fig. 2, 3.2 flow and Fig. 1, 3.3 approaches with Fig. 3, Fig. 4 and Table 1, 3.4 evidence coverage with Table 2);
   4 Discussion; 5 Conclusion; `## References` left empty.
3. Figures: `![Fig. 1 short description](../figures/Fig_1.png)` on its own line, then `**Fig. 1.** caption` on the next. Tables: paste `figures/Table N.md` (its first line is already `**Table N.** caption`). Cite each figure and table in the text before it appears.
4. Citations only as `[LIT: key]` (several as `[LIT: k1, k2]`, separated by commas, never semicolons: `verify_refs.py` reports a semicolon as an unknown key). No hand-made reference list. About 4,000 words, within the journal profile's limit.
5. Every number in Results comes from a file in `data/`. Claims about what the literature lacks are limited to "in the records screened here".

## Phase 9: verification (3 min)

1. `PY SK/scripts/verify_refs.py --project PROJ --draft writing/manuscript_draft1_<date>.md`. For every key it reports under `unknown_keys`, `no_doi`, `unresolved` or `retracted`, delete that citation (or
   replace it with a verified source) and run the script again until exit 0.
2. `writing/verification.md`: a table of each number stated in Results and Abstract with the file and row it came from; fix any that do not match.
3. `writing/iteration-log.md`: one entry (ARTi-writing Stage 5) with compliance against Block A, style against the voice profile, technical depth against Block C, and novelty fit (Block D). Fix 🔴 Critical items.

## Phase 10: export (3 min)

1. `L library enrich --keys $(contents of data/cited-keys.txt) --project PROJ`. `no_doi` or `failed` keys: fix the metadata if it is known, otherwise remove the citation and re-run `verify_refs.py`.
2. `PY ARTI/tools/arti-docx/render.py --md writing/manuscript_draft1_<date>.md --out submission/manuscript.docx --cite zotero --template ARTI/tools/arti-docx/assets/default-academic-template-zotero.docx --project PROJ`.
3. `PY SK/scripts/check_docx.py submission/manuscript.docx --expect-zotero` must exit 0; it also confirms the .docx was built from `default-academic-template-zotero.docx` (`"zotero_template": true`). The numbers it prints go into the final message.
4. The text inside each citation field is an author-year placeholder until the researcher opens the file in Word with Zotero and presses Refresh.
   Figures are embedded as PNG; each figure also exists as a vector PDF (`figures/Fig_1.pdf`, `Fig_2.pdf`, `graphical-abstract.pdf`).

Fallback: `enrich` fails for everything (no Crossref access) -> build once without `--cite zotero` and say so; the scoreboard then shows 0 Zotero fields honestly.

## Phase 11: scoreboard and final message (1 min)

`PY SK/scripts/run_log.py phase --project PROJ --n 11 --name "Scoreboard" ...`, then `PY SK/scripts/scoreboard.py --project PROJ`. Final reply: the scoreboard's
"Result at a glance" table, the path to the `.docx`, the problems list, and two sentences: the profile used was a demo placeholder (offer ARTi-setup for the real one), and Zotero Refresh restyles all citations.
