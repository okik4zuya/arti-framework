# Search routing: which route finds new literature

The only place that says which search route to use. Parameters and limits live in
`~/.arti/tools/arti-search/README.md`; the openalex connector is the official OpenAlex MCP (see
`~/.arti/CAPABILITIES.md`), optional and never required.

**Calling the tool.** Every route is a subcommand of one CLI, run with the vendored interpreter:
`"~/.arti/python/python.exe" "~/.arti/tools/arti-search/cli.py" <subcommand> ...` (Mac/Linux:
`~/.arti/python/bin/python3`). Below it is written `arti-search <subcommand>`. Three habits keep it reliable:

- Put a Boolean query in a file and pass `--query-file q.txt`: quotes and parentheses survive Windows shells that way.
- Add `--out PATH` for anything bigger than a handful of records. The full result goes to the file and only a
  summary (count, returned, `oql`, cost) is printed, so 100 records and their abstracts never fill the conversation.
- `--ris PATH` writes the records as RIS for `arti-lit library import-ris`; `--snapshot PATH` keeps the raw JSON.

**Basis:** one test on 2026-10-03, one project (Paper Metnum ECE), 22 library papers over six
topics, one rater. Recall at 50 was OpenAlex keyword 13/22, Scholar 6/22 at only 10, S2 search 5/22,
S2 bulk 6/22. Indications, not rates. Detail: the project memory `mcp-search-comparison`.

## Task to route

| Task | Route |
|---|---|
| Topic with stable terms, varied wording (calibration, programming) | openalex `find_keywords`, drop machine-learning and sensor keywords, then `keyword_search` (text OR keyword per facet, **no `types` filter**), then `search_works(oql=..., sort=cited_by_count)` |
| Same, but keywords already known | `arti-search search --query-file q.txt` (`--search-in` default `title_abstract`); measure width first with `arti-search count` |
| Methods-statistics or niche engineering-education gap | OpenAlex route above, plus 1-3 phrase queries with `arti-search scholar` (10 hits, one page, no paging) |
| Filtered shortlist (field, type, minimum citations) | `arti-search s2-search` with a short 4-6 word query and filters |
| Expand from a trusted paper | `arti-search trace --seeds W...,W...` (1-5 seeds, ranked by `link_count`); `arti-search related W...` as a weaker option |
| Check a list found elsewhere (DOIs, titles, Scholar, Elicit) | `arti-search resolve --items-file list.txt --project PATH` (matches to OpenAlex, flags `in_library` and PDF availability); openalex `resolve_references` is an optional second opinion |
| Landscape counts, trend, top sources | `arti-search count --group-by publication_year` (also `type`, `open_access.oa_status`, `primary_location.source.id`, `primary_topic.id`, `language`); openalex `analyze_works` or `group_works` when the connector is signed in (the only route for counts per country or institution) |
| Full-text PDF of a chosen paper | `arti-search fulltext --project PATH --item DOI=KEY`, then `arti-lit library add` and `arti-convert ingest` |
| Scan very recent related work | `arti-search s2-recommend --positive DOI,DOI --pool recent`; a scanner only, mostly uncited 2026 papers |

## Do not use routinely

- S2 `/paper/search` as the main finder: 40-90 % off topic in the top 50, long sentences return 0-3 hits. It is keyword matching, whatever `meta` says.
- S2 bulk, citation contexts, snippet search: not wrapped; bulk added nothing at 50 beyond OpenAlex.
- S2 `--pool all-cs` recommendations: old textbook-heavy results, brainstorming only.
- `--search-in semantic` on OpenAlex: its embedding gateway failed on 2026-10-03 (HTTP 400, certificate error). Documented and supported by OpenAlex (`help.openalex.org/api/semantic-search/`: GTE Large EN, `search.semantic=`, max 2,000 characters and 50 results, 1 request/s, no `cited_by_count` filter, one search parameter per request). Run `arti-search sources` first; the fallback is a keyword rerun, not semantic.
- `--search-in all`: adds full text, 11-39x more hits, no recall gain. Opt in deliberately.
- openalex `search_works(oql=...)` without `sort`: no relevance without search text, so newest-first, mostly uncited 2026 records.

## Working rules

1. OpenAlex first. Run `arti-search sources` at the start of a search session.
2. Semantic Scholar: one call at a time; the CLI spaces calls itself (the last-call time is kept in `~/.arti/.cache/search-state.json`), and the key limit is 1 request/s. Without a key `s2-search` returns HTTP 429; `s2-recommend` works without one.
3. Google Scholar is scraping and against its terms: a handful of queries per session, no paging, stop at the first CAPTCHA or cooldown. The cooldown is kept in the same state file, so it holds across separate calls: a refusal that says "cooling down" means wait, not retry.
4. A candidate without a DOI (Scholar snippet, truncated title) goes through `arti-search resolve` by title.
5. Drop results where `in_library` is true before presenting.
6. Log each round (query, route, date, hit count) in `literature/search-log.md`.
7. Candidates are never added to the library automatically. The researcher picks; a chosen one goes through `ARTi-ref` `library add` (DOI dedup) like any supplied paper. Everything stays `[UNVERIFIED - USER MUST CONFIRM]` until then. (An explicitly autonomous run, such as the `ARTi-demo` skill, may add candidates up to its cap and must log each one `DEMO-AUTO`.)
8. Keys (OpenAlex, Semantic Scholar) are optional: without them the CLI uses the anonymous pools and OA locations. Set them in the dashboard under Settings > APIs.

## Systematic reviews

Only the reproducible routes count as database searches (`DB:` prefix in `search_source`): OpenAlex queries with the logged `meta.oql` (the `--out` summary prints it), and Scopus run by the researcher. Scholar, S2 and recommendations are discovery aids; records found that way enter as `OTHER:` (see `ARTi-SLR/references/stage2-search-and-screening.md`, path B) and must pass both screening gates.
