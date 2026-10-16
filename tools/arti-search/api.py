"""Plain-function API over the search sources, shared by `cli.py`.

One function per route, same parameters and return shapes the MCP tools had (see README.md for each
parameter). No `mcp` import: this module is what lets the search work without any MCP registration.

Failures come back as `{"error", "error_type", "hint"?}` through `safe()`, never as an empty list; other
exceptions are bugs and still raise.
"""
from typing import Dict, List, Optional, Union

from config import get_env
from http_client import SourceFetchError
from resolve import resolve_candidates
from sources.googlescholar import GoogleScholarSource
from sources.openalex import OpenAlexSource
from sources.semanticscholar import SemanticScholarSource

openalex_source = OpenAlexSource()
semanticscholar_source = SemanticScholarSource()
googlescholar_source = GoogleScholarSource()

# Substring of the upstream message -> what to try instead (command names are cli.py subcommands).
HINTS = (
    ("Failed to embed query", "OpenAlex's embedding backend is down: use `related` (seed paper) or "
     "search_in=title_abstract."),
    ("HTTP 429", "Rate limited: add OPENALEX_API_KEY / SEMANTIC_SCHOLAR_API_KEY in the dashboard under "
     "Settings > APIs (stored in mcp-keys.json), or retry later."),
    ("_API_KEY is not set", "Add the key in the dashboard under Settings > APIs."),
    ("unknown work_type", "The message lists the valid work_type values."),
    ("SEMANTIC_SCHOLAR_API_KEY configured", "Add the free S2 key in Settings > APIs; `s2-recommend` "
     "works without one."),
    ("Google Scholar", "Scholar is a scraping route and may be blocked; wait out the cooldown, set "
     "GOOGLE_SCHOLAR_PROXY_URL, or use `search` / `s2-search`. Run `sources`."),
)


def safe(fn, **kwargs):
    """Call fn(**kwargs); fetch/validation failures become the {error, error_type, hint} envelope."""
    try:
        return fn(**kwargs)
    except (SourceFetchError, ValueError) as e:
        msg = str(e)
        out = {"error": msg, "error_type": type(e).__name__}
        hint = next((h for needle, h in HINTS if needle in msg), None)
        if hint:
            out["hint"] = hint
        return out


def search_openalex_works(
    query: str,
    max_results: int = 10,
    search_in: str = "title_abstract",
    work_type: Union[str, List[str], None] = None,
    exclude_retracted: bool = True,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    open_access_only: bool = False,
    language: Optional[str] = None,
    min_citations: Optional[int] = None,
    has_abstract: Optional[bool] = None,
    has_content_pdf: bool = False,
    topic_id: Optional[str] = None,
    source_issn: Optional[str] = None,
    cites: Optional[str] = None,
    cited_by: Optional[str] = None,
    related_to: Optional[str] = None,
    filters: Optional[str] = None,
    sort: str = "relevance",
    sort_by_citations: bool = False,
    cursor: Optional[str] = None,
    include_abstract: bool = True,
    abstract_max_chars: Optional[int] = None,
) -> Dict:
    """Search OpenAlex works. Returns {"meta": {count, returned, cost_usd, next_cursor, oql}, "results": [...]}."""
    if sort_by_citations and sort == "relevance":
        sort = "citations"
    return openalex_source.search(
        query, max_results=max_results, sort=sort, cursor=cursor, include_abstract=include_abstract,
        abstract_max_chars=abstract_max_chars, search_in=search_in, work_type=work_type,
        exclude_retracted=exclude_retracted, year_from=year_from, year_to=year_to,
        open_access_only=open_access_only, language=language, min_citations=min_citations,
        has_abstract=has_abstract, has_content_pdf=has_content_pdf, topic_id=topic_id,
        source_issn=source_issn, cites=cites, cited_by=cited_by, related_to=related_to, filters=filters)


def count_openalex_works(
    query: Optional[str] = None,
    group_by: Optional[str] = None,
    search_in: str = "title_abstract",
    work_type: Union[str, List[str], None] = None,
    exclude_retracted: bool = True,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    open_access_only: bool = False,
    language: Optional[str] = None,
    min_citations: Optional[int] = None,
    has_abstract: Optional[bool] = None,
    has_content_pdf: bool = False,
    topic_id: Optional[str] = None,
    source_issn: Optional[str] = None,
    cites: Optional[str] = None,
    cited_by: Optional[str] = None,
    related_to: Optional[str] = None,
    filters: Optional[str] = None,
) -> Dict:
    """Count matches without pulling records. Returns {total, groups, groups_truncated, cost_usd, oql}."""
    return openalex_source.count(
        query, group_by=group_by, search_in=search_in, work_type=work_type,
        exclude_retracted=exclude_retracted, year_from=year_from, year_to=year_to,
        open_access_only=open_access_only, language=language, min_citations=min_citations,
        has_abstract=has_abstract, has_content_pdf=has_content_pdf, topic_id=topic_id,
        source_issn=source_issn, cites=cites, cited_by=cited_by, related_to=related_to, filters=filters)


def related_openalex_works(
    id_or_doi: str,
    max_results: int = 10,
    sort: str = "citations",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    work_type: Union[str, List[str], None] = None,
    abstract_max_chars: Optional[int] = None,
) -> Dict:
    """OpenAlex's precomputed related works for one seed (no embedding service, no key)."""
    return openalex_source.search(
        "", max_results=max_results, sort=sort, abstract_max_chars=abstract_max_chars,
        year_from=year_from, year_to=year_to, work_type=work_type, exclude_retracted=True,
        related_to=id_or_doi)


def get_openalex_work(id_or_doi: str) -> Dict:
    """One OpenAlex work by W-id or DOI (free): type, retraction status, cached-PDF flag."""
    return openalex_source.get_work(id_or_doi)


def lookup_openalex_entity(kind: str, name: str, limit: int = 10) -> Union[List[Dict], Dict]:
    """Autocomplete a name to OpenAlex IDs: kind is topics | sources | institutions | authors."""
    return openalex_source.lookup_entity(kind, name, limit)


def download_openalex_fulltext(
    items: List[Dict],
    project_path: str,
    dry_run: bool = False,
    max_files: int = 20,
    source: str = "auto",
) -> Dict:
    """Download PDFs to <project_path>/literature/fulltext/<key>.pdf (never touches arti-lit.db)."""
    return openalex_source.download_fulltext(
        items, project_path, dry_run=dry_run, max_files=max_files, source=source)


def search_semanticscholar_papers(
    query: str,
    max_results: int = 10,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_citations: Optional[int] = None,
    open_access_only: bool = False,
    publication_types: Optional[str] = None,
    fields_of_study: Optional[str] = None,
    offset: int = 0,
    abstract_max_chars: Optional[int] = None,
) -> Dict:
    """Semantic Scholar relevance search (plain text, no Boolean operators)."""
    return semanticscholar_source.search(
        query, max_results=max_results, year_from=year_from, year_to=year_to,
        min_citations=min_citations, open_access_only=open_access_only,
        publication_types=publication_types, fields_of_study=fields_of_study, offset=offset,
        abstract_max_chars=abstract_max_chars)


def recommend_semanticscholar_papers(
    positive: List[str],
    negative: Optional[List[str]] = None,
    max_results: int = 20,
    abstract_max_chars: Optional[int] = None,
    year_from: Optional[int] = None,
    min_citations: Optional[int] = None,
    pool: str = "recent",
) -> Dict:
    """Embedding-based 'more like these' from seed papers (works without a key)."""
    return semanticscholar_source.recommend(
        positive, negative, max_results=max_results, abstract_max_chars=abstract_max_chars,
        year_from=year_from, min_citations=min_citations, pool=pool)


def get_semanticscholar_paper(id_or_doi: str) -> Dict:
    """One Semantic Scholar paper by DOI or S2 id."""
    return semanticscholar_source.get_paper(id_or_doi)


def trace_openalex_citations(
    seeds: List[str],
    direction: str = "forward",
    query: Optional[str] = None,
    max_results: int = 20,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    min_citations: Optional[int] = None,
    abstract_max_chars: Optional[int] = None,
) -> Dict:
    """Citation tracing from 1-5 seeds, merged and ranked by link_count."""
    return openalex_source.trace(
        seeds, direction=direction, query=query, max_results=max_results, year_from=year_from,
        year_to=year_to, min_citations=min_citations, abstract_max_chars=abstract_max_chars)


def resolve_external_candidates(items: List[str], project_path: Optional[str] = None) -> Dict:
    """Match DOIs, DOI URLs or titles (max 50) to OpenAlex records; flags in_library read-only."""
    return resolve_candidates(openalex_source, items, project_path)


def search_googlescholar_papers(
    query: str,
    max_results: int = 10,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    start: int = 0,
    resolve: bool = True,
) -> Dict:
    """Google Scholar keyword search (scraping route, one page per call, persisted cooldown)."""
    out = googlescholar_source.search(query, max_results, year_from, year_to, start)
    if resolve and out["results"]:
        items = [r["doi"] or r["title"] for r in out["results"]]
        rows = resolve_candidates(openalex_source, items)["items"]
        for r, row in zip(out["results"], rows):
            r["resolved"] = {k: v for k, v in row.items() if k != "input"}
        out["meta"]["resolved_note"] = "[UNVERIFIED - USER MUST CONFIRM] OpenAlex match, not a fit check."
    return out


def check_search_sources() -> Dict:
    """Which routes are live. Probes OpenAlex keyword and semantic search, and Semantic Scholar only
    when its key is set; Google Scholar is never probed (only its cooldown state is reported)."""
    out: Dict = {}
    oa: Dict = {"key_configured": bool(get_env("OPENALEX_API_KEY"))}
    for label, mode in (("keyword", "title_abstract"), ("semantic", "semantic")):
        try:
            openalex_source._search("learning", max_results=1, search_in=mode, include_abstract=False)
            oa[label] = {"reachable": True}
        except SourceFetchError as e:
            oa[label] = {"reachable": False, "detail": str(e)[:200]}
    s2_key = bool(get_env("SEMANTIC_SCHOLAR_API_KEY"))
    s2: Dict = {"key_configured": s2_key}
    if s2_key:
        try:
            semanticscholar_source.search("learning", max_results=1)
            s2["search"] = {"reachable": True}
        except SourceFetchError as e:
            s2["search"] = {"reachable": False, "detail": str(e)[:200]}
    else:
        s2["search"] = {"reachable": None, "detail": "not probed: unauthenticated search returns 429"}
        s2["recommend"] = "works without a key (skews to recent zero-citation papers)"
    out["openalex"] = oa
    out["semanticscholar"] = s2
    out["googlescholar"] = {"probed": False, **googlescholar_source.status()}
    sem_up = oa["semantic"]["reachable"]
    out["suggested_concept_route"] = (
        "openalex semantic (search --search-in semantic)" if sem_up else
        "semanticscholar (search --search-in semantic falls back to it automatically)" if s2_key else
        "`s2-recommend` or `trace` from trusted seeds; add SEMANTIC_SCHOLAR_API_KEY for concept search")
    return out
