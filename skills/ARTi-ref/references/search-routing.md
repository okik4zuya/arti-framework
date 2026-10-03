# Search routing: which route finds new literature

The only place that says which search route to use. Tool parameters and limits live in
`~/.arti/tools/arti-ref-search-mcp/README.md`; the openalex connector is the official OpenAlex MCP
(see `~/.arti/CAPABILITIES.md`).

**Basis:** one test on 2026-10-03, one project (Paper Metnum ECE), 22 library papers over six
topics, one rater. Recall at 50 was OpenAlex keyword 13/22, Scholar 6/22 at only 10, S2 search 5/22,
S2 bulk 6/22. Indications, not rates. Detail: the project memory `mcp-search-comparison`.

## Task to route

| Task | Route |
|---|---|
| Topic with stable terms, varied wording (calibration, programming) | openalex `find_keywords`, drop machine-learning and sensor keywords, then `keyword_search` (text OR keyword per facet, **no `types` filter**), then `search_works(oql=..., sort=cited_by_count)` |
| Same, but keywords already known | arti-ref `search_openalex_works` (`search_in` default `title_abstract`); measure width first with `count_openalex_works` |
| Methods-statistics or niche engineering-education gap | OpenAlex route above, plus 1-3 phrase queries on `search_googlescholar_papers` (10 hits, one page, no paging) |
| Filtered shortlist (field, type, minimum citations) | `search_semanticscholar_papers` with a short 4-6 word query and filters |
| Expand from a trusted paper | `trace_openalex_citations` (1-5 seeds, ranked by `link_count`); `related_openalex_works` as a weaker option |
| Check a list found elsewhere (DOIs, titles, Scholar, Elicit) | openalex `resolve_references` for free-text citations, then `resolve_external_candidates` for `in_library` and PDF availability |
| Landscape counts, trend, top sources | openalex `analyze_works` or `group_works`; arti-ref `count_openalex_works` with `group_by` |
| Full-text PDF of a chosen paper | `download_openalex_fulltext`, then `arti-lit library add` and `arti-pdf-ingest` |
| Scan very recent related work | `recommend_semanticscholar_papers`, several seeds, `pool=recent`; a scanner only, mostly uncited 2026 papers |

## Do not use routinely

- S2 `/paper/search` as the main finder: 40-90 % off topic in the top 50, long sentences return 0-3 hits. It is keyword matching, whatever `meta` says.
- S2 bulk, citation contexts, snippet search: not wrapped; bulk added nothing at 50 beyond OpenAlex.
- S2 `pool=all-cs` recommendations: old textbook-heavy results, brainstorming only.
- `search_in='semantic'` on OpenAlex: its embedding gateway failed on 2026-10-03 (HTTP 400, certificate error). Documented and supported by OpenAlex (`help.openalex.org/api/semantic-search/`: GTE Large EN, `search.semantic=`, max 2,000 characters and 50 results, 1 request/s, no `cited_by_count` filter, one search parameter per request). Run `check_search_sources` first; the fallback is a keyword rerun, not semantic.
- `search_in='all'`: adds full text, 11-39x more hits, no recall gain. Opt in deliberately.
- `search_works(oql=...)` without `sort`: no relevance without search text, so newest-first, mostly uncited 2026 records.

## Working rules

1. OpenAlex first. Run `check_search_sources` at the start of a search session.
2. Semantic Scholar: one call at a time, pause 3 s or more (HTTP 429 appeared at 1.2-1.3 s spacing; the key limit is 1 request/s).
3. Google Scholar is scraping and against its terms: a handful of queries per session, no paging, stop at the first CAPTCHA or cooldown.
4. A candidate without a DOI (Scholar snippet, truncated title) goes through `resolve_external_candidates` by title.
5. Drop results where `in_library` is true before presenting.
6. Log each round (query, route, date, hit count) in `literature/search-log.md`.
7. Candidates are never added to the library automatically. The researcher picks; a chosen one goes through `ARTi-ref` `library add` (DOI dedup) like any supplied paper. Everything stays `[UNVERIFIED - USER MUST CONFIRM]` until then.

## Systematic reviews

Only the reproducible routes count as database searches (`DB:` prefix in `search_source`): OpenAlex queries with the logged `meta.oql`, and Scopus run by the researcher. Scholar, S2 and recommendations are discovery aids; records found that way enter as `OTHER:` (see `ARTi-SLR/references/stage2-search-and-screening.md`, path B) and must pass both screening gates.
