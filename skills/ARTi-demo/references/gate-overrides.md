# Gate overrides: what replaces "ask the researcher" in an unattended demo run

The ARTi skills stop at several points to ask the researcher. In this run the researcher gave one answer (the topic) and
nothing else, so each gate has a fixed autonomous rule. Apply the rule, then record it with
`run_log.py decision --project P --text "..."` (one line: what was decided and why). Never leave a gate open and never
ask a question to get past one. An override applies only inside `ARTi-demo`; it changes nothing for normal use of the skills.

| Skill and stage | The normal gate | Rule in the demo |
|---|---|---|
| ARTi-setup Workflow A | Interview for the Researcher Profile | `seed_profiles.py` installs the demo profile only if none exists. A real profile is never touched |
| ARTi-idea Stage 3 | "Rank the viable ideas and ask the researcher to select one" | Take the idea with the highest composite novelty score that is within the profile's Section H ceiling. Ties: the one whose claim can be answered from OpenAlex data alone. Park the others with `idea-bank add` as the skill already does |
| ARTi-idea Stage 5 | "Researcher nominates journals and confirms the top two" | Nominate 3-5 from `arti-jfinder` (Q1 or Q2, open to review or scoping-review articles, scope fits). Take the first that passes the predatory screen, scope fit and the novelty threshold. Record the runner-up as the fallback |
| ARTi-idea Stage 5, predatory screen | Auto-pass only for a journal the researcher has published in | Run the short screen: Scimago-listed (so Scopus-indexed) and Q1 or Q2 is the indexing cross-check; log the verdict. A journal that fails is dropped, not discussed |
| ARTi-idea Stage 5, example papers | "Papers provided by the researcher" | Take them from the target journal itself: open-access articles, newest first, with `arti-search search --source-issn ISSN --oa-only --has-content-pdf` (see runbook phase 5) |
| ARTi-ref and `search-routing.md` rule 7 | "Candidates are never added to the library automatically; the researcher picks" | Add records up to the cap (100). Log each search round in `literature/search-log.md` with status `DEMO-AUTO`, and set `search_source` on every record |
| ARTi-SLR style screening | The researcher confirms judgment calls | Decide each record; borderline cases are included only if the abstract states a method or a result about the topic, and are listed in `data/decisions-*.csv` with the reason `judgment call` |
| ARTi-scratchbook | `[UNVERIFIED - USER MUST CONFIRM]` on any suggested reference | A reference may carry no such tag only after `arti-search resolve` found its DOI in OpenAlex. A reference that does not resolve is not cited |
| ARTi-writing Stage 0 | "Ask which Voice Profile is in effect" when several exist | `demo-generic`; write it into Journal Profile Block B |
| ARTi-writing Stage 1 | 5-8 example papers read | A "light" profile from 3 papers of the target journal, marked `light (3 papers)` at the top of the file. If fewer than 3 have open-access full text, read abstracts and mark them abstract-level |
| ARTi-writing Stage 5 | Iteration Log entry only when the researcher asks | One entry, requested by this skill (phase 9) |
| Any skill | Ask before running a long or costly step | Do not ask; stay inside the caps in the runbook |

## Things that are never overridden

- Numbers in the manuscript come from files in `data/` or counts the tools printed. No invented values.
- A citation enters the manuscript only if its DOI resolved in OpenAlex. No invented references.
- Image-integrity and no-explanatory-text rules for graphical abstracts (`ARTi-figure`).
- The title page says the manuscript is a demo output, generated unattended, not peer reviewed.
- Paraphrase literature in your own words (ARTi-scratchbook extraction rule); no copied sentences.
