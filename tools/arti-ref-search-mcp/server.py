"""arti-ref-search-mcp: in-house, multi-source-ready literature-discovery MCP server.

OpenAlex only for now. Adding another source later is: (1) a new sources/<name>.py implementing
PaperSource, reusing http_client.py; (2) thin @mcp.tool() wrappers below, same shape as the
OpenAlex ones; (3) its own optional env var(s) if needed. See README.md for the full recipe.

Run directly: "<vendored python>" server.py -- Python adds a directly-run script's own directory
to sys.path[0] automatically, so the bare `from paper import Paper` / `from sources...` imports
below resolve with no packaging tricks, regardless of cwd.
"""
from typing import Dict, List, Optional, Union

from mcp.server.mcpserver import MCPServer

from sources.openalex import OpenAlexSource

mcp = MCPServer("arti-ref-search-mcp")

openalex_source = OpenAlexSource()


@mcp.tool()
def search_openalex_works(
    query: str,
    max_results: int = 10,
    search_in: str = "all",
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
        search_in: 'all' (default; title+abstract+full text where indexed) | 'title_abstract' |
            'title' | 'abstract' | 'exact' (no stemming) | 'semantic' (meaning-based; no
            min_citations or sort).
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
        filters: Raw OpenAlex filter string appended as-is (escape hatch).
        sort: 'relevance' | 'citations' | 'year_desc' | 'year_asc'.
        sort_by_citations: Legacy alias for sort='citations'.
        cursor: meta.next_cursor from a previous call to fetch the next page.
        include_abstract: False drops abstracts for a much smaller payload.
        abstract_max_chars: Truncate each abstract to this many characters.
    Returns:
        {"meta": {count (total matches), returned, cost_usd, next_cursor, oql}, "results":
        [paper dicts; extra holds type, year, is_retracted, language, venue, oa_status, license,
        content_pdf_available]}. Raises on a genuine fetch failure or a rejected filter (the
        OpenAlex message is included) instead of returning an empty list.
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
        filters=filters,
    )


@mcp.tool()
def count_openalex_works(
    query: Optional[str] = None,
    group_by: Optional[str] = None,
    search_in: str = "all",
    work_type: Union[str, List[str], None] = None,
    exclude_retracted: bool = False,
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
    filters: Optional[str] = None,
) -> Dict:
    """Count OpenAlex works matching a query without pulling records (cheap; measures how
    narrow or broad a query is). Same filter parameters as search_openalex_works.

    Args:
        group_by: Optional breakdown: publication_year | type | primary_topic.id |
            primary_location.source.id | open_access.is_oa | language.
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
        filters=filters,
    )


@mcp.tool()
def get_openalex_work(id_or_doi: str) -> Dict:
    """Fetch one OpenAlex work by W-id or DOI (free singleton lookup). Use it to resolve a DOI to
    an OpenAlex ID and to check type, retraction status and whether a PDF is cached
    (has_content.pdf).
    """
    return openalex_source.get_work(id_or_doi)


@mcp.tool()
def lookup_openalex_entity(kind: str, name: str, limit: int = 10) -> List[Dict]:
    """Autocomplete a name to OpenAlex IDs (free).

    Args:
        kind: 'topics' | 'sources' (journals) | 'institutions' | 'authors'.
        name: Text to complete, e.g. 'photocatalytic CO2 reduction'.
        limit: Max candidates to return.
    Returns:
        List of {id, name, hint, works_count, cited_by_count, issn_l}; use id as topic_id.
    """
    return openalex_source.lookup_entity(kind, name, limit)


@mcp.tool()
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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
