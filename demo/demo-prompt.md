# ARTi one-prompt demo

Paste everything below the line into a fresh Claude Code session opened in `~/.arti` (or any folder, with
the ARTi skills linked). Change `{TOPIK}` first if you want a different subject; leave the rest.
Default: `AI and large language models for literature screening and evidence synthesis`.

---

Run the ARTi showcase end to end, autonomously (yolo): do not ask me questions, make sensible
decisions, log each decision in one line, and finish with a manuscript `.docx`. The topic is:
**{TOPIK}**. Paper type: scoping review plus bibliometric analysis, English, generic journal style,
about 4,000 words. Total time target: 30 minutes, so respect the caps below.

## Hard rules
- Every number in the manuscript comes from data you fetched or computed in this run. Never invent a
  value, a citation, or a DOI. A reference enters the paper only if it resolved in OpenAlex or Crossref.
- Mark the manuscript title page with "ARTi demo output: generated unattended, not peer reviewed".
- Always call Python by full path (`"~/.arti/python/python.exe"`), never bare `python`.
- If a step fails, try the fallback named for it, record what happened in `demo-run-log.md`, and move on.
  Never stop the whole run for one failed step.
- Caps: 100 candidate records, 10 full-text attempts, 5 figures, 2 tables.

## Steps
0. **Researcher profile.** If `~/.arti/memory/researcher-profile.md` exists, leave it untouched. If it is
   missing, copy `~/.arti/demo/demo-researcher-profile.md` to that path (the first line marks it as a demo
   profile). Do not run the interview.
1. **Pre-flight.** Confirm the vendored Python runs, `~/.arti/bin` has poppler and tesseract, and run
   `check_search_sources`. Note which search routes are live; use only those.
2. **Project.** Scaffold a paper project at `~/ARTi-demo/<slug>` with ARTi-setup Workflow B.
3. **Idea (ARTi-idea, short form).** Build a compact gap map from a first search, score novelty (C/M/E)
   against the profile's ceiling, run one ARTi-crosscite check on the two largest literature clusters, and
   pick a target journal with `arti-jfinder` (Scimago Q1 or Q2, open to scoping reviews). Save the Idea
   Canvas and Journal Target Sheet.
4. **Search (ARTi-ref).** Query OpenAlex, Semantic Scholar and Google Scholar through
   `arti-ref-search-mcp`; resolve candidates, dedupe by DOI, add up to 100 records to `arti-lit.db` with
   `arti-lit`. Save the raw result snapshot to `data/search-snapshot.json` so the run can be replayed offline.
5. **Full text ladder.** For the 10 most relevant open-access records, try `download_openalex_fulltext`,
   convert with `arti-convert ingest`, and set status `fulltext`. Any record without open-access full text
   stays at status `abstract`, and the manuscript must say so. Report the full-text versus abstract-only
   ratio as a result.
6. **Data.** Classify every record from its abstract (task, method family, field, evidence type) into
   `data/classified.csv`. Aggregate publications per year, country and journal from OpenAlex into CSV files
   under `data/`. All plots are built from these CSVs, with the aggregated file saved next to each plot.
7. **Figures and tables (ARTi-figure).** Make: a PRISMA-ScR flow diagram (`arti-render`, `.drawio`); a
   publication-trend plot and a method-by-year plot (matplotlib PNG, plot lane); a synthesis table and a
   full-text-coverage table (`arti-table`); and a graphical abstract (`arti-compose`, vector PDF plus PNG,
   all checks passing).
8. **Write (ARTi-scratchbook, ARTi-writing).** Create the Scratchbook, fill it from the records and data
   with proper `[LIT: key]` and `[OWN]` tags, build the Blueprint, then draft Abstract, Introduction,
   Methods, Results, Discussion and Conclusion. Cite abstract-only records for what their abstracts state,
   never for details only a full text would give.
9. **Verify.** Run openalex `resolve_references` on every cited DOI, drop or fix any that fail, and note
   retractions. Check that each number in Results matches a CSV.
10. **Export.** Build `submission/manuscript.docx` with `arti-docx` (figures embedded, references list
    included) and a PDF copy with `arti-convert pdf`.
11. **Scoreboard.** Write `demo-scoreboard.md` in the project root: one row per ARTi capability used, with
    the file or count that proves it (records found per source, full-text versus abstract-only, figures,
    tables, references verified, word count, total minutes), plus a short list of anything that failed.

When done, reply with the scoreboard and the path to the `.docx`. Then say, in one sentence, that the
researcher profile used was a demo placeholder and offer to run the real ARTi-setup interview.
