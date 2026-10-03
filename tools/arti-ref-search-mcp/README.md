# arti-ref-search-mcp

In-house, multi-source-ready MCP server for live literature-discovery search. Replaces the
third-party `openags/paper-search-mcp` pip package (see `CLAUDE.md`'s `.mcp.json` bullet for why).
Discovery only — never writes to a project's `arti-lit.db` directly; a chosen candidate goes
through `ARTi-ref`'s own dedup path like any researcher-supplied paper.

## Invocation

Registered in `.mcp.json` (project scope, `~/.arti` only) and at Claude Code's user scope (every
paper project) — not meant to be run by hand. For a standalone check:

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-ref-search-mcp/server.py"
```

Reads on stdio (MCP stdio transport); exits on EOF/Ctrl-C.

## Configuration

Both env vars are optional; the server works with neither set (anonymous OpenAlex pool).

- `OPENALEX_API_KEY` — OpenAlex API key, raises the daily request budget ~10x over anonymous use.
  Get one free from OpenAlex; see `notes/openalex-api.md`.
- `ARTI_REF_CONTACT_EMAIL` — contact email sent as OpenAlex's `mailto` param (the "polite pool"
  mechanism) — a real identifier, not a placeholder.
- `SEMANTIC_SCHOLAR_API_KEY` — free key from semanticscholar.org/product/api. Without it the shared
  pool returned HTTP 429 on every `search_semanticscholar_papers` call (2026-10-03); with it S2 gives a
  dedicated 1 request/second, which the source respects.

- `GOOGLE_SCHOLAR_PROXY_URL` — optional HTTP(S) proxy for `search_googlescholar_papers` only.

All four are resolved by `config.get_env()`: process env first, then the `arti-ref-search-mcp` stanza's
`env` in `<arti home>/.mcp.json` (put the Semantic Scholar key there, next to the OpenAlex one).

## Tools

Every tool returns fetch/validation failures as `{error, error_type, hint}` (via `_safe` in `server.py`). All tools raise internally on a genuine failure (HTTP 429/5xx after 5 retries, or any 4xx — the OpenAlex
message, e.g. the list of valid filter names, is appended; `api_key=` and `mailto=` values are redacted to `***` and control characters dropped) instead of
returning an empty result. A real zero-match query returns `results: []` with `meta.count: 0` — the
two cases are distinguishable by construction. This is the direct fix for the third-party
package's silent-failure bug (see `CLAUDE.md`).

### `search_openalex_works(query, ...)`

Returns `{"meta": {count, returned, cost_usd, next_cursor, oql}, "results": [paper dicts]}`.
`meta.oql` is OpenAlex's own rendering of the query it ran — cite it as the logged search string.
Paper dicts keep `paper_id`, `title`, `authors`, `abstract`, `doi`, `published_date`, `pdf_url`,
`url`, `source`, `categories`, `citations`; `extra` now holds `type`, `year`, `is_retracted`,
`language`, `venue`, `oa_status`, `license`, `content_pdf_available`.

| Parameter | Notes |
|---|---|
| `query` | Boolean (`AND`/`OR`/`NOT` capitals), `"phrases"`, `"a b"~5` proximity pass through |
| `search_in` | `title_abstract` (default since 2026-10-03; title + abstract) · `all` (**title + abstract + full text** where indexed; 11-39x more hits, opt in deliberately) · `title` · `abstract` · `exact` (no stemming) · `semantic` (max 50 results, ≤2000 chars, no cursor/`sort`/`min_citations`) |
| `work_type` | string or list, validated against OpenAlex's 25 types (`review`, `article`, `preprint`, ...) |
| `exclude_retracted` | default **True** |
| `year_from`, `year_to`, `open_access_only`, `language`, `min_citations`, `has_abstract`, `has_content_pdf`, `topic_id`, `source_issn` | straight filters |
| `cites`, `cited_by`, `related_to` | OpenAlex ID or DOI; citation tracing in each direction; `related_to` = OpenAlex's precomputed related works |
| `filters` | raw OpenAlex filter string appended as-is |
| `sort` | `relevance` · `citations` · `year_desc` · `year_asc` (`sort_by_citations=True` stays as an alias) |
| `max_results`, `cursor` | cursor paging, 100 per request, so no 10,000-result ceiling; pass `meta.next_cursor` back as `cursor` |
| `include_abstract`, `abstract_max_chars` | shrink the payload; `select=` is applied server-side |

**API key reach (2026-10-03).** `config.get_env()` reads `OPENALEX_API_KEY` / `ARTI_REF_CONTACT_EMAIL` from the
process env first, then from the `arti-ref-search-mcp` stanza of `<arti home>/.mcp.json`. The user-scope entry in
`~/.claude.json` has `"env": {}`, so before this fix only sessions opened inside `~/.arti` had the key and
`download_openalex_fulltext` (which needs it) failed everywhere else. One copy of the secret, reachable from every
project; no restart-time env wiring needed beyond restarting the server.

**Semantic outage fallback (2026-10-03).** OpenAlex's own embedding backend can fail (its Databricks
gateway returned a TLS hostname-mismatch error, so every `semantic` call got HTTP 400 "Failed to embed
query"; nothing to fix client-side, no API key involved). On that specific error `search` reruns the
query as `title_abstract` with the sentence cut to content words, ANDed, dropping the shortest word
until at least 5 hits come back. It is never silent: `meta.fallback` names the query actually run and
`meta.semantic_error` keeps the upstream message. Quality is lower than semantic (generic words leak
in), so treat fallback results as a rough first pass. Other semantic failures still raise.

Cost (OpenAlex price list, $1/day free with a key): `search`/`semantic` $1 per 1,000 requests,
filter-only list calls $0.10 per 1,000, singleton/autocomplete free. `meta.cost_usd` reports the
real figure. Note `search_in='all'` also matches full text and is the pricier, broader mode —
`title_abstract` is now the default for prior-review and gap checks. Counts logged before 2026-10-03
(e.g. 3,501 in the abstract-coverage test) used the old `all` default and are not comparable.

Concept search (no keywords, or `semantic` down): use the openalex MCP keyword route; see the note in
`skills/ARTi-idea/references/stage2-gap-map-protocol.md`.

### `count_openalex_works(query=None, group_by=None, ...)`

Same filters; returns `{total, groups: [{key, label, count}], groups_truncated, cost_usd, oql}`
without pulling records. `group_by`: `publication_year` · `type` · `primary_topic.id` ·
`primary_location.source.id` · `open_access.is_oa` · `open_access.oa_status` · `has_content.pdf` ·
`language`. Boolean keys come back as `true`/`false` or `1`/`0`. Do not group by `has_abstract`: OpenAlex
reports `false` = 0 even when `has_abstract=False` matches 100k+ works; count twice instead. `exclude_retracted`
now defaults **True** (as in search), so old counts may drop slightly. Use it first to measure how narrow
or broad a query is.

### `related_openalex_works(id_or_doi, max_results=10, sort='citations', ...)`

"More like this" from a trusted seed via OpenAlex's `related_to:` filter: no embedding service, no key.
Roughly 10 related works per seed, about half relevant; use several seeds. Same result shape as search.

### Errors

Fetch failures and rejected parameters come back as `{"error", "error_type", "hint"?}` instead of the
opaque "Error executing tool". Unexpected exceptions (bugs) still raise.

### `get_openalex_work(id_or_doi)`

Free singleton lookup. Resolves DOI → OpenAlex ID; returns type, retraction status, and
`has_content` (`pdf`/`grobid_xml`).

### `lookup_openalex_entity(kind, name, limit=10)`

Autocomplete for `topics` | `sources` | `institutions` | `authors` → ID, for `topic_id` etc.
Autocomplete matches **name prefixes**, so use a short term (`photocatalysis`), not a sentence.

### `download_openalex_fulltext(items, project_path, dry_run=False, max_files=20, source="auto")`

`items` = `[{"id_or_doi", "key"}]`, `key` = the `author-year[a|b]` arti-lit key (`[a-z0-9-]+`,
validated; the destination is forced under `<project_path>/literature/fulltext/`). Per item:
`ok` · `skipped_exists` (never overwrites) · `no_content` (no cached PDF and no usable OA link, or
the link returned a landing/paywall page — checked by `%PDF` magic bytes) · `error`; one failure
never aborts the batch. `source`: `auto` (OpenAlex cached PDF via `content.openalex.org`, then
`best_oa_location`/`locations[].pdf_url`) · `openalex_content` · `oa_location`. The OpenAlex
content route needs `OPENALEX_API_KEY` and costs $0.01 per file (`dry_run` reports the estimate);
`oa_location` is free and needs no key. The report states each file's source. PDF copyright stays
with the publisher — `extra.license` in search results is the OA license where known.

The tool never writes `arti-lit.db`. To register and convert afterwards: add the row with
`arti-lit library add`, write `literature/fulltext/manifest.csv` (`pdf_filename,key`), then
`arti-pdf-ingest ingest --project P --manifest M --source-dir P/literature/fulltext
--keep-source-pdf` (verified: ingest skips the copy when source and destination are the same file).

### Semantic Scholar tools (added 2026-10-03, `sources/semanticscholar.py`)

- `search_semanticscholar_papers(query, max_results, year_from, year_to, min_citations, open_access_only,
  publication_types, fields_of_study, offset, abstract_max_chars)` — plain-text relevance search (no Boolean
  operators; quotes/hyphens stripped); up to 100 per call, page with `offset`. Returns the same
  `{meta, results}` envelope; `extra` carries year, venue, influential citations, `tldr`.
- `recommend_semanticscholar_papers(positive, negative=None, max_results=20, year_from=None, min_citations=None, pool='recent')`
  — embedding-based "more like these" from DOI, S2-id or **OpenAlex W-id** seeds (W-ids are resolved to DOIs;
  GET for one seed, POST for several or any negative seed). `year_from`/`min_citations` are applied client-side to an
  over-fetched list (`meta.fetched`, `meta.filtered_out`). Measured 2026-10-03 on an ANCOVA seed: default `pool='recent'`
  gives ~88 % 2026 papers with 0-1 citations (on topic, unproven, so a citation filter empties it); `pool='all-cs'`
  (single seed, no negatives only) gives older, highly cited, textbook-heavy results. Independent of OpenAlex's embedding service.
- `get_semanticscholar_paper(id_or_doi)` — one paper with abstract, `tldr`, OA PDF.

Verified 2026-10-03: seed lookup, GET and POST recommendations, per-endpoint field rules (the recommendations
endpoint rejects `tldr` with HTTP 400, so it is requested only by search and get), and the 429 hint. **Not
verified: `search_semanticscholar_papers` result quality**, because no key was configured and every call 429'd.
Observed limits of recommendations: they lean heavily toward 2026, zero-citation papers (seeds from the
2026 calibration paper returned only 2026 items), a single old seed (Locascio & Cordray 1983) returned nothing,
and it does not replace a topical search; use it to widen from a trusted seed, then screen by citations.

### Discovery routes added 2026-10-03

- `check_search_sources()` — which routes are live (OpenAlex keyword/semantic probe, S2 only if keyed, Scholar cooldown
  state without probing) and a `suggested_concept_route`.
- `search_in='semantic'` on `search_openalex_works` now falls back to **Semantic Scholar** when OpenAlex's embedding backend
  is down *and* `SEMANTIC_SCHOLAR_API_KEY` is set (`meta.fallback` names it; only years, `min_citations`, `open_access_only`
  carry over); otherwise the relaxed `title_abstract` fallback as before. A failing S2 call is reported in
  `meta.semanticscholar_error` and the Boolean fallback still runs.
- `trace_openalex_citations(seeds, direction='forward'|'backward'|'both', query=None, ...)` — 1-5 seeds, merged, ranked by
  `link_count` (how many seeds a work is linked to). Needs no keywords. Each seed/direction fetches the top
  `max(50, max_results)` by citations (`meta.per_seed` shows totals vs fetched).
- `resolve_external_candidates(items, project_path=None)` — DOIs, doi.org URLs or titles from Google Scholar by hand, Elicit,
  Scopus AI, Connected Papers -> verified OpenAlex records (`resolved` / `ambiguous` / `unresolved` / `error`), with retraction,
  OA, PDF-cached flags and `in_library` from a **read-only** look at `<project>/literature/arti-lit.db`. A title cut short by a
  search UI still resolves (containment scores 0.9). Everything stays `[UNVERIFIED - USER MUST CONFIRM]`.
- `search_googlescholar_papers(query, max_results<=10, year_from, year_to, start, resolve=True)` — **scraping route**, no
  official API, against Scholar's terms, can be blocked. Port of `openags/paper-search-mcp` `main`'s design (not its 0.1.4, which
  returns `[]` on CAPTCHA/HTTP errors): failures raise, cooldown after a block, >= 3 s between requests, one page per call,
  optional `GOOGLE_SCHOLAR_PROXY_URL`. Snippet only (`extra.snippet_only`), `citations` stays 0, so never use it as the authority for
  citation counts; `resolve=True` adds an OpenAlex `resolved` block per hit (~$0.001 each). This deliberately overrides the
  "never Google Scholar" rule for **discovery only**; `citation-chase` and `ARTi-crosscite` keep it.

Route ladder: keywords known -> `search_openalex_works` (Boolean) · concept, no keywords -> S2 `search`/`recommend` (needs
key for search) or OpenAlex `semantic` when up · trusted seed known -> `trace_openalex_citations` / `related_openalex_works` ·
list from elsewhere -> `resolve_external_candidates` · last resort -> `search_googlescholar_papers`.

### Limits and cautions (from the 2026-10-03 comparison)

Which route to use for which task: `skills/ARTi-ref/references/search-routing.md`. Tool-level facts:

- **Semantic fallback is keyword matching.** With OpenAlex's embedding backend down, `search_in='semantic'`
  falls back to Semantic Scholar's `/paper/search`, which behaves as a keyword engine (long sentences return
  0-3 hits, short ones return term-overlap hits), whatever `meta` says. Treat it as a rough first pass.
- **Semantic Scholar: 1 request per second with a key.** HTTP 429 still appeared at 1.2-1.3 s spacing, so call
  one at a time with pauses of 3 s or more. Bulk search, citation contexts and snippet search are not wrapped;
  `offset=10` repeats result 10 once.
- **Google Scholar: 10 hits per page, scraping.** No filters, no citation counts, no cheap paging. Against its
  terms of service and open to CAPTCHA blocks; a few queries per session, stop at the first block.
- **Secrets.** Keys are read by `config.get_env()` and never printed; errors redact `api_key=` and `mailto=`.
- **`check_search_sources`** reports which routes are live. Run it before a search session.

### Registration (moved here from `~/.arti/CLAUDE.md`)

- Project scope: `~/.arti/.mcp.json`, launched as `${ARTI_PYTHON:-python} tools/arti-ref-search-mcp/server.py`
  (a script path, not `-m <module>`). `install.ps1`/`install.sh` create the `python.cmd`/`python3` wrapper and
  point `ARTI_PYTHON` at it. Applies only when Claude Code's working directory is `~/.arti`.
- User scope: `~/.claude.json` top-level `mcpServers` (what makes it available in every paper project). Added once
  by hand (`claude mcp add --scope user ...` or a direct edit); not re-applied by the installers. The entry holds
  the resolved absolute `python/python.exe` and `server.py` paths, not `${ARTI_PYTHON:-python}`: env var changes
  do not reach an already-running Claude Code process tree, so the literal path avoids a second failure mode.
- Dependency: only the `mcp` SDK (unpinned, `tools/requirements.txt`). It replaced `openags/paper-search-mcp`,
  which needed `mcp<2` because its 0.1.4 imported `FastMCP` (renamed `MCPServer` in mcp 2.x), swallowed every
  OpenAlex/S2 HTTP failure into an empty list and had no OpenAlex key support.

## Architecture

```
server.py              # MCP instance + one thin @mcp.tool() wrapper per source
paper.py               # shared Paper dataclass (source-agnostic)
merge.py               # DOI/title normalization, dedupe, title similarity
resolve.py             # resolve_candidates(): external DOI/title lists -> OpenAlex records
config.py              # get_env(): process env, then the stanza's env in <arti home>/.mcp.json
http_client.py         # shared retry/backoff GET-JSON helper (any source can call this)
sources/
  base.py               # PaperSource ABC: abstract search(query, **kwargs) -> result built from Paper objects
  openalex.py            # OpenAlexSource: search/count/trace/get/lookup/download
  semanticscholar.py     # SemanticScholarSource: search/recommend/get
  googlescholar.py       # GoogleScholarSource: one-page HTML search (scraping)
```

Not pip-installed, no `pyproject.toml` — a plain directory of modules invoked directly by path,
same convention as every other `tools/` script (one level deeper, like `arti-lit`'s `cli.py` +
`db.py` split). Python adds a directly-run script's own directory to `sys.path[0]` automatically,
so cwd never matters — only the script's own location does.

### Adding a new source later

1. New `sources/<name>.py` implementing `PaperSource` (one `search(query, **kwargs)` returning Paper-based results
   method), reusing `http_client.get_json_with_retry` for HTTP.
2. One new thin `@mcp.tool() def search_<name>_works(...)` in `server.py`, same shape as the
   OpenAlex one: call the source's `.search(...)`, return `[p.to_dict() for p in papers]`.
3. Its own optional API-key/contact env var(s) if the source needs them, read the same
   `os.environ.get(...)` way — no config-file-loading machinery.

No change needed to `paper.py`, `sources/base.py`, `http_client.py`, or the existing OpenAlex tool.
A unified multi-source dispatcher tool (aggregating across sources in one call, like the original
package's `search_papers(sources=...)`) is deliberately not built with only one source — YAGNI —
but this per-source-module shape means adding one later is a small additive change (a `SOURCES`
registry dict in `server.py`, fanned out via `asyncio.gather`), not a rewrite.

## Not in this tool

- **PDF-to-Markdown conversion and library registration** — that's `arti-pdf-ingest` (this server only downloads PDFs).
- **A multi-source dispatcher tool** — not yet; see the extension recipe above.
- **Writing to `arti-lit.db`** — discovery only; a chosen candidate goes through `ARTi-ref`.
