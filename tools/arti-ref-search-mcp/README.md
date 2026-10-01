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

## Tools

All five tools raise on a genuine failure (HTTP 429/5xx after 5 retries, or any 4xx — the OpenAlex
message, e.g. the list of valid filter names, is appended and any `api_key=` is redacted) instead of
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
| `search_in` | `all` (default; **title + abstract + full text** where indexed) · `title_abstract` · `title` · `abstract` · `exact` (no stemming) · `semantic` (max 50 results, ≤2000 chars, no cursor/`sort`/`min_citations`) |
| `work_type` | string or list, validated against OpenAlex's 25 types (`review`, `article`, `preprint`, ...) |
| `exclude_retracted` | default **True** |
| `year_from`, `year_to`, `open_access_only`, `language`, `min_citations`, `has_abstract`, `has_content_pdf`, `topic_id`, `source_issn` | straight filters |
| `cites`, `cited_by` | OpenAlex ID or DOI; citation tracing in each direction |
| `filters` | raw OpenAlex filter string appended as-is |
| `sort` | `relevance` · `citations` · `year_desc` · `year_asc` (`sort_by_citations=True` stays as an alias) |
| `max_results`, `cursor` | cursor paging, 100 per request, so no 10,000-result ceiling; pass `meta.next_cursor` back as `cursor` |
| `include_abstract`, `abstract_max_chars` | shrink the payload; `select=` is applied server-side |

Cost (OpenAlex price list, $1/day free with a key): `search`/`semantic` $1 per 1,000 requests,
filter-only list calls $0.10 per 1,000, singleton/autocomplete free. `meta.cost_usd` reports the
real figure. Note `search_in='all'` also matches full text and is the pricier, broader mode —
prefer `title_abstract` for prior-review and gap checks.

### `count_openalex_works(query=None, group_by=None, ...)`

Same filters; returns `{total, groups: [{key, label, count}], groups_truncated, cost_usd, oql}`
without pulling records. `group_by`: `publication_year` · `type` · `primary_topic.id` ·
`primary_location.source.id` · `open_access.is_oa` · `language`. Use it first to measure how narrow
or broad a query is.

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

## Architecture

```
server.py              # MCP instance + one thin @mcp.tool() wrapper per source
paper.py               # shared Paper dataclass (source-agnostic)
http_client.py         # shared retry/backoff GET-JSON helper (any source can call this)
sources/
  base.py               # PaperSource ABC: abstract search(query, **kwargs) -> result built from Paper objects
  openalex.py            # OpenAlexSource(PaperSource) -- the only concrete source for now
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
