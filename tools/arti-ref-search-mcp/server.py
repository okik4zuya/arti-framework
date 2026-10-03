"""arti-ref-search-mcp: in-house, multi-source-ready literature-discovery MCP server.

OpenAlex, Semantic Scholar and (scraping, opt-in by use) Google Scholar. Adding another source later is: (1) a new sources/<name>.py implementing
PaperSource, reusing http_client.py; (2) thin @mcp.tool() wrappers below, same shape as the
OpenAlex ones; (3) its own optional env var(s) if needed. See README.md for the full recipe.

Run directly: "<vendored python>" server.py -- Python adds a directly-run script's own directory
to sys.path[0] automatically, so the bare `from paper import Paper` / `from sources...` imports
below resolve with no packaging tricks, regardless of cwd.
"""
import functools
from typing import Dict, List, Optional, Union

from mcp.server.mcpserver import MCPServer

from config import get_env
from http_client import SourceFetchError
from resolve import resolve_candidates
from sources.googlescholar import GoogleScholarSource
from sources.openalex import OpenAlexSource
from sources.semanticscholar import SemanticScholarSource

mcp = MCPServer("arti-ref-search-mcp")

openalex_source = OpenAlexSource()
semanticscholar_source = SemanticScholarSource()
googlescholar_source = GoogleScholarSource()


# Substring of the upstream message -> what the model should try instead.
_HINTS = (
    ("Failed to embed query", "OpenAlex's embedding backend is down: use related_openalex_works "
     "(seed paper) or search_in='title_abstract'."),
    ("HTTP 429", "Rate limited: set OPENALEX_API_KEY / SEMANTIC_SCHOLAR_API_KEY (read via "
     "config.get_env) or retry later."),
    ("_API_KEY is not set", "Add the key to the environment file read by config.get_env."),
    ("unknown work_type", "The message lists the valid work_type values."),
    ("SEMANTIC_SCHOLAR_API_KEY configured", "Add the free S2 key to the arti-ref-search-mcp env in "
     "<arti home>/.mcp.json; recommend_semanticscholar_papers works without one."),
    ("Google Scholar", "Scholar is a scraping route and may be blocked; wait out the cooldown, set "
     "GOOGLE_SCHOLAR_PROXY_URL, or use OpenAlex/Semantic Scholar tools. Run check_search_sources."),
)


def _safe(fn):
    """Return fetch/validation failures as {"error", "error_type", "hint"} so the model sees the
    real message instead of 'Error executing tool'. Other exceptions are bugs and still raise."""
    @functools.wraps(fn)  # keeps the real signature visible to MCPServer
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (SourceFetchError, ValueError) as e:
            msg = str(e)
            out = {"error": msg, "error_type": type(e).__name__}
            hint = next((h for needle, h in _HINTS if needle in msg), None)
            if hint:
                out["hint"] = hint
            return out
    return wrapper


@mcp.tool()
@_safe
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
    """Search OpenAlex works (topic discovery, prior-review checks, citation tracing).

    Args:
        query: Boolean/phrase syntax is passed through: AND/OR/NOT in capitals, "quoted phrase",
            "a b"~5 proximity. Stemming is automatic except in search_in='exact'.
        max_results: Papers to return; paged internally 100 per request (semantic: max 50).
        search_in: 'title_abstract' (default; title+abstract) | 'all' (title+abstract+full text
            where indexed; 11-39x more hits, opt in deliberately) |
            'title' | 'abstract' | 'exact' (no stemming) | 'semantic' (meaning-based; no
            min_citations or sort). If OpenAlex's embedding backend is down, semantic falls back
            to Semantic Scholar when SEMANTIC_SCHOLAR_API_KEY is set (only years, min_citations and
            open_access_only carry over), else to a relaxed title_abstract query; meta.fallback says
            which. An empty query is allowed with cites/cited_by/related_to (never use '*').
        work_type: One type or a list, e.g. 'review' or ['article','preprint']. Valid: article,
            book, book-chapter, book-review, conference-abstract, conference-paper, data-paper,
            dataset, dissertation, editorial, erratum, letter, libguides, other, paratext,
            peer-review, preprint, reference-entry, report, retraction, review, software,
            software-paper, standard, supplementary-materials.
        exclude_retracted: Drop retracted works (default True).
        year_from / year_to: Inclusive publication-year bounds.
        open_access_only: Only works with an open-access version.
        language: ISO 639-1 code, e.g. 'en'.
        min_citations: Minimum cited-by count.
        has_abstract: True/False to require/forbid an abstract.
        has_content_pdf: Only works whose PDF OpenAlex has cached (downloadable via
            download_openalex_fulltext).
        topic_id: OpenAlex primary-topic ID (find via lookup_openalex_entity).
        source_issn: Journal ISSN of the primary location.
        cites: Works that cite this work (OpenAlex ID or DOI).
        cited_by: Works cited by this work (OpenAlex ID or DOI).
        related_to: Works OpenAlex lists as related to this work (ID or DOI); see
            related_openalex_works.
        filters: Raw OpenAlex filter string appended as-is (escape hatch).
        sort: 'relevance' | 'citations' | 'year_desc' | 'year_asc'.
        sort_by_citations: Legacy alias for sort='citations'.
        cursor: meta.next_cursor from a previous call to fetch the next page.
        include_abstract: False drops abstracts for a much smaller payload.
        abstract_max_chars: Truncate each abstract to this many characters.
    Returns:
        {"meta": {count (total matches), returned, cost_usd, next_cursor, oql}, "results":
        [paper dicts; extra holds type, year, is_retracted, language, venue, oa_status, license,
        content_pdf_available]}. A genuine fetch failure or rejected filter comes back as
        {"error", "error_type", "hint"} (the OpenAlex message is included), never an empty list.
    """
    if sort_by_citations and sort == "relevance":
        sort = "citations"
    return openalex_source.search(
        query,
        max_results=max_results,
        sort=sort,
        cursor=cursor,
        include_abstract=include_abstract,
        abstract_max_chars=abstract_max_chars,
        search_in=search_in,
        work_type=work_type,
        exclude_retracted=exclude_retracted,
        year_from=year_from,
        year_to=year_to,
        open_access_only=open_access_only,
        language=language,
        min_citations=min_citations,
        has_abstract=has_abstract,
        has_content_pdf=has_content_pdf,
        topic_id=topic_id,
        source_issn=source_issn,
        cites=cites,
        cited_by=cited_by,
        related_to=related_to,
        filters=filters,
    )


@mcp.tool()
@_safe
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
    """Count OpenAlex works matching a query without pulling records (cheap; measures how
    narrow or broad a query is). Same filter parameters as search_openalex_works.

    Args:
        group_by: Optional breakdown: publication_year | type | primary_topic.id |
            primary_location.source.id | open_access.is_oa | open_access.oa_status | language |
            has_content.pdf (boolean keys come back as 'true'/'false' or '0'/'1'). For abstract
            coverage do NOT group by has_abstract (OpenAlex reports false=0); count twice with
            has_abstract=True / False instead.
    Returns:
        {"total", "groups": [{key, label, count}], "groups_truncated", "cost_usd", "oql"}
    """
    return openalex_source.count(
        query,
        group_by=group_by,
        search_in=search_in,
        work_type=work_type,
        exclude_retracted=exclude_retracted,
        year_from=year_from,
        year_to=year_to,
        open_access_only=open_access_only,
        language=language,
        min_citations=min_citations,
        has_abstract=has_abstract,
        has_content_pdf=has_content_pdf,
        topic_id=topic_id,
        source_issn=source_issn,
        cites=cites,
        cited_by=cited_by,
        related_to=related_to,
        filters=filters,
    )


@mcp.tool()
@_safe
def related_openalex_works(
    id_or_doi: str,
    max_results: int = 10,
    sort: str = "citations",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    work_type: Union[str, List[str], None] = None,
    abstract_max_chars: Optional[int] = None,
) -> Dict:
    """'More like this' from a trusted seed paper using OpenAlex's precomputed related works
    (no embedding service, no key). Use when search_in='semantic' is down or the topic has no
    stable keywords.

    Limits seen in testing: roughly 10 related works per seed, about half relevant; try several
    seeds and merge. Same result shape as search_openalex_works.

    Args:
        id_or_doi: Seed work (OpenAlex W-id or DOI).
        sort: 'citations' (default) | 'relevance' | 'year_desc' | 'year_asc'.
    """
    return openalex_source.search(
        "",
        max_results=max_results,
        sort=sort,
        abstract_max_chars=abstract_max_chars,
        year_from=year_from,
        year_to=year_to,
        work_type=work_type,
        exclude_retracted=True,
        related_to=id_or_doi,
    )


@mcp.tool()
@_safe
def get_openalex_work(id_or_doi: str) -> Dict:
    """Fetch one OpenAlex work by W-id or DOI (free singleton lookup). Use it to resolve a DOI to
    an OpenAlex ID and to check type, retraction status and whether a PDF is cached
    (has_content.pdf).
    """
    return openalex_source.get_work(id_or_doi)


@mcp.tool()
@_safe
def lookup_openalex_entity(kind: str, name: str, limit: int = 10) -> Union[List[Dict], Dict]:
    """Autocomplete a name to OpenAlex IDs (free).

    Args:
        kind: 'topics' | 'sources' (journals) | 'institutions' | 'authors'.
        name: Text to complete, e.g. 'photocatalytic CO2 reduction'.
        limit: Max candidates to return.
    Returns:
        List of {id, name, hint, works_count, cited_by_count, issn_l}; use id as topic_id.
        (On failure: the {"error", ...} envelope.)
    """
    return openalex_source.lookup_entity(kind, name, limit)


@mcp.tool()
@_safe
def download_openalex_fulltext(
    items: List[Dict],
    project_path: str,
    dry_run: bool = False,
    max_files: int = 20,
    source: str = "auto",
) -> Dict:
    """Download PDFs to <project_path>/literature/fulltext/<key>.pdf. Does not touch arti-lit.db;
    register and convert afterwards with arti-pdf-ingest (manifest.csv: '<key>.pdf,<key>').

    Args:
        items: List of {"id_or_doi": W-id or DOI, "key": "author-year[a|b]"} (key: [a-z0-9-]+).
        project_path: Paper project root.
        dry_run: Report what would be downloaded and the estimated cost; download nothing.
        max_files: Batch cap (OpenAlex content costs $0.01 per file).
        source: 'auto' (OpenAlex cached PDF first, then OA locations) | 'openalex_content'
            (needs OPENALEX_API_KEY) | 'oa_location' (publisher/repository OA links, no key).
    Returns:
        {"summary": {counts, cost}, "items": [{key, status: ok|skipped_exists|no_content|error
        |would_download, path, bytes, source, detail}]}. Existing files are never overwritten.
        PDF copyright stays with the publisher; check each work's license in search results.
    """
    return openalex_source.download_fulltext(
        items, project_path, dry_run=dry_run, max_files=max_files, source=source)


@mcp.tool()
@_safe
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
    """Search Semantic Scholar (relevance-ranked over title+abstract; plain text, no Boolean
    operators). Use when OpenAlex's semantic mode is down or for a second opinion on a concept
    query. Needs SEMANTIC_SCHOLAR_API_KEY (free) to avoid shared-pool HTTP 429.

    Args:
        query: Plain-text query; quotes/hyphens are stripped.
        max_results: Up to 100 per call; page with `offset` / meta.next_offset.
        year_from / year_to: Inclusive publication-year bounds.
        min_citations: Minimum citation count.
        open_access_only: Only papers with an open-access PDF.
        publication_types: Comma list, e.g. 'JournalArticle,Review'.
        fields_of_study: Comma list, e.g. 'Education,Engineering'.
        abstract_max_chars: Truncate each abstract.
    Returns:
        {"meta": {count, returned, offset, next_offset}, "results": [paper dicts; extra holds
        year, venue, influential_citations, publication_types, is_open_access, tldr]}.
    """
    return semanticscholar_source.search(
        query,
        max_results=max_results,
        year_from=year_from,
        year_to=year_to,
        min_citations=min_citations,
        open_access_only=open_access_only,
        publication_types=publication_types,
        fields_of_study=fields_of_study,
        offset=offset,
        abstract_max_chars=abstract_max_chars,
    )


@mcp.tool()
@_safe
def recommend_semanticscholar_papers(
    positive: List[str],
    negative: Optional[List[str]] = None,
    max_results: int = 20,
    abstract_max_chars: Optional[int] = None,
    year_from: Optional[int] = None,
    min_citations: Optional[int] = None,
    pool: str = "recent",
) -> Dict:
    """Embedding-based 'more like these' (SPECTER) from seed papers; independent of OpenAlex's
    embedding service. Best when the topic has no stable keywords: seed with 1-5 papers you
    already trust, add `negative` seeds to steer away from a wrong neighbourhood.

    Args:
        positive: Seed papers as DOIs, OpenAlex W-ids (resolved to their DOI) or
            S2/ARXIV:/PMID:/CorpusId: ids.
        negative: Optional seeds to move away from.
        max_results: Up to 500.
        year_from / min_citations: Applied here, not by S2 (the endpoint has no filters and leans to
            recent zero-citation papers); it over-fetches (10x, min 100, max 500) and meta.filtered_out says how many dropped.
        pool: 'recent' (default; ~88% 2026 papers, on topic but uncited) | 'all-cs' (older, highly
            cited, textbook-heavy; single positive seed, no negatives only).
    Returns:
        {"meta": {returned, positive, negative[, fetched, filtered_out]}, "results": [paper dicts]}.
    """
    return semanticscholar_source.recommend(
        positive, negative, max_results=max_results, abstract_max_chars=abstract_max_chars,
        year_from=year_from, min_citations=min_citations, pool=pool)


@mcp.tool()
@_safe
def get_semanticscholar_paper(id_or_doi: str) -> Dict:
    """Fetch one Semantic Scholar paper by DOI or S2 id (abstract, tldr, OA PDF, citation counts)."""
    return semanticscholar_source.get_paper(id_or_doi)


@mcp.tool()
@_safe
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
    """Citation tracing from 1-5 trusted seed papers, merged and ranked by how many seeds each
    result is linked to. Works without keywords, so it closes gaps keyword search cannot name.

    Args:
        seeds: OpenAlex W-ids or DOIs (max 5).
        direction: 'forward' (works citing a seed) | 'backward' (a seed's references) | 'both'.
        query: Optional title/abstract keywords to narrow (no wildcards).
        max_results: Results returned after merging (each seed/direction fetches up to
            max(50, max_results) by citations first).
    Returns:
        {"meta": {seeds, per_seed, unique_found, ...}, "results": [paper dicts + linked_to_seeds,
        link_count, directions]}. Seeds are excluded. link_count >= 2 is the strong signal.
    """
    return openalex_source.trace(
        seeds, direction=direction, query=query, max_results=max_results, year_from=year_from,
        year_to=year_to, min_citations=min_citations, abstract_max_chars=abstract_max_chars)


@mcp.tool()
@_safe
def resolve_external_candidates(items: List[str], project_path: Optional[str] = None) -> Dict:
    """Verify papers found outside this server (Google Scholar by hand, Elicit, Scopus AI,
    Connected Papers): each DOI, doi.org URL or title is matched to an OpenAlex record.

    Args:
        items: DOIs, URLs containing a DOI, or full titles (max 50). Titles need a close match
            (token Jaccard >= 0.85 resolved, >= 0.6 ambiguous with up to 3 candidates).
        project_path: Optional paper project root; flags in_library from the read-only
            literature/arti-lit.db (never written).
    Returns:
        {"note", "summary", "items": [{input, status: resolved|ambiguous|unresolved|error,
        openalex_id, doi, title, year, type, is_retracted, oa_status, content_pdf_available,
        abstract_present, in_library}]}. Feed resolved DOIs to download_openalex_fulltext.
    """
    return resolve_candidates(openalex_source, items, project_path)


@mcp.tool()
@_safe
def search_googlescholar_papers(
    query: str,
    max_results: int = 10,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    start: int = 0,
    resolve: bool = True,
) -> Dict:
    """Google Scholar keyword search (scraping route; no official API, may be blocked or rate
    limited, against Scholar's terms). Use sparingly for concept queries OpenAlex and Semantic
    Scholar miss; never as the authority for citation counts.

    Args:
        query: Plain text.
        max_results: 1-10 (one Scholar page per call); page with `start` / meta.next_start.
        resolve: Match each hit to OpenAlex (DOI, retraction, OA, real abstract). Costs about
            $0.001 per title lookup; False returns raw Scholar snippets only.
    Returns:
        {"meta", "results"}; results hold the Scholar snippet (extra.snippet_only) and, when
        resolve=True, a "resolved" block per hit. Failures (CAPTCHA, cooldown) come back as the
        {"error", "error_type", "hint"} envelope, never an empty list.
    """
    out = googlescholar_source.search(query, max_results, year_from, year_to, start)
    if resolve and out["results"]:
        items = [r["doi"] or r["title"] for r in out["results"]]
        rows = resolve_candidates(openalex_source, items)["items"]
        for r, row in zip(out["results"], rows):
            r["resolved"] = {k: v for k, v in row.items() if k != "input"}
        out["meta"]["resolved_note"] = "[UNVERIFIED - USER MUST CONFIRM] OpenAlex match, not a fit check."
    return out


@mcp.tool()
@_safe
def check_search_sources() -> Dict:
    """Which search routes are live right now. Run before choosing between OpenAlex semantic,
    Semantic Scholar, citation tracing and Google Scholar.

    Probes OpenAlex keyword and semantic search (a few cents at most) and Semantic Scholar only
    when its key is configured (unauthenticated search 429s). Google Scholar is never probed
    (a probe could trigger a block); only its cooldown state is reported.
    """
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
        "openalex semantic" if sem_up else
        "semanticscholar (search_in='semantic' falls back to it automatically)" if s2_key else
        "recommend_semanticscholar_papers or trace_openalex_citations from trusted seeds; "
        "add SEMANTIC_SCHOLAR_API_KEY for concept search")
    return out


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
