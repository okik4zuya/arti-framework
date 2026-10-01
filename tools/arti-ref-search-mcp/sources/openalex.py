"""OpenAlex source: works search/count/singleton, entity autocomplete, fulltext download.

Response-parsing logic (including the abstract inverted-index reconstruction) is adapted from
openags/paper-search-mcp (MIT, Copyright 2025 OPENAGS), `academic_platforms/openalex.py`. Rebuilt
on top of the shared `http_client` instead of `requests` + silent try/except-return-[] error
swallowing. Parameter semantics verified against help.openalex.org (not docs.openalex.org, which
now redirects) and live API calls, 2026-10-01.
"""
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from http_client import SourceFetchError, download_file, get_json_with_retry
from paper import Paper
from sources.base import PaperSource

API = "https://api.openalex.org"
CONTENT_URL = "https://content.openalex.org/works"

WORK_TYPES = {
    "article", "book", "book-chapter", "book-review", "conference-abstract", "conference-paper",
    "data-paper", "dataset", "dissertation", "editorial", "erratum", "letter", "libguides",
    "other", "paratext", "peer-review", "preprint", "reference-entry", "report", "retraction",
    "review", "software", "software-paper", "standard", "supplementary-materials",
}

# `all` is OpenAlex's default `search=` (title + abstract + full text where indexed); the
# narrower modes are filters and never touch full text.
SEARCH_IN = {"all", "title_abstract", "title", "abstract", "exact", "semantic"}
_SEARCH_FILTER = {
    "title_abstract": "title_and_abstract.search",
    "title": "title.search",
    "abstract": "abstract.search",
}

SORTS = {
    "relevance": None,
    "citations": "cited_by_count:desc",
    "year_desc": "publication_date:desc",
    "year_asc": "publication_date:asc",
}

GROUP_BY = {
    "publication_year", "type", "primary_topic.id", "primary_location.source.id",
    "open_access.is_oa", "language",
}

ENTITY_KINDS = {"topics", "sources", "institutions", "authors"}

# select= accepts root-level fields only (not open_access.is_oa).
_SELECT = (
    "id,doi,title,publication_year,publication_date,type,cited_by_count,is_retracted,language,"
    "authorships,primary_location,best_oa_location,open_access,abstract_inverted_index,"
    "has_content,primary_topic"
)

_PAGE_MAX = 100  # per_page above 100 is deprecated behaviour
_KEY_RE = re.compile(r"^[a-z0-9-]+$")
_MAX_PDF_BYTES = 80 * 1024 * 1024
_COST_PER_CONTENT_FILE = 0.01


def _reconstruct_abstract(inverted_index: Optional[dict]) -> str:
    """OpenAlex stores abstracts as a word->positions inverted index to save space."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in word_positions)


def _auth_params() -> Dict:
    params = {}
    api_key = os.environ.get("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key
    mailto = os.environ.get("ARTI_REF_CONTACT_EMAIL")
    if mailto:
        params["mailto"] = mailto
    return params


def _short_id(value: Optional[str]) -> str:
    return (value or "").replace("https://openalex.org/", "")


def _strip_doi(value: Optional[str]) -> str:
    return (value or "").replace("https://doi.org/", "")


def _filter_text(text: str) -> str:
    """Commas separate filters inside `filter=`, so they cannot appear in a search value."""
    return text.replace(",", " ")


def _normalize_work_id(ref: str) -> str:
    """Accept a W-id, OpenAlex URL, DOI, or doi.org URL; return the form the API path takes."""
    ref = ref.strip()
    if re.fullmatch(r"W\d+", ref, re.I):
        return ref.upper()
    if ref.startswith("https://openalex.org/"):
        return _short_id(ref)
    doi = _strip_doi(ref)
    if doi.lower().startswith("doi:"):
        doi = doi[4:]
    if doi.startswith("10."):
        return f"doi:{doi}"
    raise ValueError(f"not an OpenAlex work ID or DOI: {ref!r}")


class OpenAlexSource(PaperSource):
    """OpenAlex works: search, count, singleton, entity autocomplete, fulltext download."""

    # ---- query building -------------------------------------------------------------------

    def _resolve_work_ref(self, ref: str) -> str:
        """W-id for a DOI/ID (cites/cited_by filters need the W-id; the singleton is free)."""
        norm = _normalize_work_id(ref)
        if norm.startswith("W"):
            return norm
        data = get_json_with_retry(f"{API}/works/{norm}", {"select": "id", **_auth_params()})
        return _short_id(data.get("id"))

    def _build_query(
        self,
        query: Optional[str],
        search_in: str = "all",
        work_type=None,
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
        """Return request params (search param + `filter`) shared by search and count."""
        if search_in not in SEARCH_IN:
            raise ValueError(f"search_in must be one of {sorted(SEARCH_IN)}, got {search_in!r}")
        params: Dict = {}
        flt: List[str] = []

        if query and query.strip():
            if search_in == "all":
                params["search"] = query
            elif search_in == "exact":
                params["search.exact"] = query
            elif search_in == "semantic":
                params["search.semantic"] = query
            else:
                flt.append(f"{_SEARCH_FILTER[search_in]}:{_filter_text(query)}")
        elif search_in == "semantic":
            raise ValueError("search_in='semantic' needs a query")

        if work_type:
            types = [work_type] if isinstance(work_type, str) else list(work_type)
            bad = [t for t in types if t not in WORK_TYPES]
            if bad:
                raise ValueError(f"unknown work_type {bad}; valid: {sorted(WORK_TYPES)}")
            flt.append("type:" + "|".join(types))
        if exclude_retracted:
            flt.append("is_retracted:false")
        if year_from is not None:
            flt.append(f"from_publication_date:{year_from}-01-01")
        if year_to is not None:
            flt.append(f"to_publication_date:{year_to}-12-31")
        if open_access_only:
            flt.append("open_access.is_oa:true")
        if language:
            flt.append(f"language:{language}")
        if min_citations is not None:
            if search_in == "semantic":
                raise ValueError("semantic search is not compatible with min_citations")
            flt.append(f"cited_by_count:>{int(min_citations) - 1}")
        if has_abstract is not None:
            flt.append(f"has_abstract:{str(bool(has_abstract)).lower()}")
        if has_content_pdf:
            flt.append("has_content.pdf:true")
        if topic_id:
            flt.append(f"primary_topic.id:{topic_id}")
        if source_issn:
            flt.append(f"primary_location.source.issn:{source_issn}")
        if cites:
            flt.append(f"cites:{self._resolve_work_ref(cites)}")
        if cited_by:
            flt.append(f"cited_by:{self._resolve_work_ref(cited_by)}")
        if filters:
            flt.append(filters.strip().strip(","))

        if flt:
            params["filter"] = ",".join(flt)
        return params

    # ---- tools ----------------------------------------------------------------------------

    def search(
        self,
        query: str,
        max_results: int = 10,
        sort: str = "relevance",
        cursor: Optional[str] = None,
        include_abstract: bool = True,
        abstract_max_chars: Optional[int] = None,
        **query_kwargs,
    ) -> Dict:
        """Search works. Returns {"meta": {...}, "results": [Paper dict, ...]}.

        Pages with a cursor (100 per request) so max_results is not capped by the 10,000-result
        plain-paging ceiling. Raises SourceFetchError on any failure; a real zero-match response
        returns an empty `results` with meta.count == 0.
        """
        if sort not in SORTS:
            raise ValueError(f"sort must be one of {sorted(SORTS)}, got {sort!r}")
        if max_results < 1:
            raise ValueError("max_results must be >= 1")
        search_in = query_kwargs.get("search_in", "all")
        if search_in == "semantic":
            max_results = min(max_results, 50)  # API ceiling for semantic search

        params = self._build_query(query, **query_kwargs)
        if sort != "relevance":
            if search_in == "semantic":
                raise ValueError("semantic search is already ranked; sort must be 'relevance'")
            params["sort"] = SORTS[sort]
        params["select"] = _SELECT if include_abstract else _SELECT.replace(
            "abstract_inverted_index,", "")
        params.update(_auth_params())

        papers: List[Paper] = []
        meta: Dict = {}
        next_cursor = cursor or "*"
        while len(papers) < max_results and next_cursor:
            page_params = dict(params)
            page_params["per_page"] = min(_PAGE_MAX, max_results - len(papers))
            if search_in == "semantic":
                page_params["page"] = 1  # semantic search rejects cursor paging
            else:
                page_params["cursor"] = next_cursor
            data = get_json_with_retry(f"{API}/works", params=page_params)
            meta = data.get("meta", {})
            items = data.get("results", [])
            for item in items:
                paper = self._parse_work(item, abstract_max_chars)
                if paper:
                    papers.append(paper)
            next_cursor = meta.get("next_cursor") if items else None
            if search_in == "semantic":
                break  # no cursor paging for semantic search

        xq = meta.get("x_query") or {}
        return {
            "meta": {
                "count": meta.get("count"),
                "returned": len(papers),
                "cost_usd": meta.get("cost_usd"),
                "next_cursor": next_cursor,
                "oql": xq.get("oql"),
            },
            "results": [p.to_dict() for p in papers],
        }

    def count(self, query: Optional[str] = None, group_by: Optional[str] = None, **query_kwargs):
        """Count matching works, optionally grouped. Returns {"total", "groups", "cost_usd"}."""
        if group_by is not None and group_by not in GROUP_BY:
            raise ValueError(f"group_by must be one of {sorted(GROUP_BY)}, got {group_by!r}")
        params = self._build_query(query, **query_kwargs)
        params["per_page"] = 1
        if group_by:
            params["group_by"] = group_by
            params["cursor"] = "*"  # group_by has no `page`; cursor is required
            params.pop("per_page")
        params.update(_auth_params())

        data = get_json_with_retry(f"{API}/works", params=params)
        meta = data.get("meta", {})
        groups = []
        for bucket in data.get("group_by", []) or []:
            groups.append({
                "key": re.sub(r"^https://openalex.org/(types/)?", "", str(bucket.get("key"))),
                "label": bucket.get("key_display_name"),
                "count": bucket.get("count"),
            })
        total = meta.get("count")
        if group_by and total is None:
            total = sum(g["count"] or 0 for g in groups)
        return {
            "total": total,
            "groups": groups,
            "groups_truncated": bool(group_by and (meta.get("groups_count") or 0) > len(groups)),
            "cost_usd": meta.get("cost_usd"),
            "oql": (meta.get("x_query") or {}).get("oql"),
        }

    def get_work(self, ref: str) -> Dict:
        """One work by W-id/DOI (singleton: free). Returns a Paper dict plus has_content."""
        norm = _normalize_work_id(ref)
        data = get_json_with_retry(
            f"{API}/works/{norm}", {"select": _SELECT, **_auth_params()})
        paper = self._parse_work(data, None, require_title=False)
        out = paper.to_dict()
        out["has_content"] = data.get("has_content") or {}
        return out

    def lookup_entity(self, kind: str, name: str, limit: int = 10) -> List[Dict]:
        """Autocomplete topics/sources/institutions/authors -> OpenAlex IDs (free)."""
        if kind not in ENTITY_KINDS:
            raise ValueError(f"kind must be one of {sorted(ENTITY_KINDS)}, got {kind!r}")
        data = get_json_with_retry(
            f"{API}/autocomplete/{kind}", {"q": name, **_auth_params()})
        out = []
        for r in (data.get("results") or [])[: max(1, limit)]:
            out.append({
                "id": _short_id(r.get("id")),
                "name": r.get("display_name"),
                "hint": r.get("hint"),
                "works_count": r.get("works_count"),
                "cited_by_count": r.get("cited_by_count"),
                "issn_l": (r.get("external_id") if kind == "sources" else None),
            })
        return out

    # ---- parsing --------------------------------------------------------------------------

    def _parse_work(self, item: Dict, abstract_max_chars: Optional[int],
                    require_title: bool = True) -> Optional[Paper]:
        title = item.get("title")
        if not title and require_title:
            return None

        authors = [
            a.get("author", {}).get("display_name", "")
            for a in item.get("authorships", []) or []
            if a.get("author", {}).get("display_name")
        ]
        abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
        if abstract_max_chars and len(abstract) > abstract_max_chars:
            abstract = abstract[:abstract_max_chars].rstrip() + "..."

        primary = item.get("primary_location") or {}
        best_oa = item.get("best_oa_location") or {}
        oa = item.get("open_access") or {}
        pdf_url = primary.get("pdf_url") or best_oa.get("pdf_url") or ""
        if not pdf_url and oa.get("is_oa"):
            pdf_url = oa.get("oa_url") or ""
        url = primary.get("landing_page_url") or item.get("id") or ""
        venue = (primary.get("source") or {}).get("display_name") or ""

        published_date = None
        if item.get("publication_date"):
            try:
                published_date = datetime.strptime(item["publication_date"], "%Y-%m-%d")
            except ValueError:
                pass

        topic = item.get("primary_topic") or {}
        categories = [topic["display_name"]] if topic.get("display_name") else []
        has_content = item.get("has_content") or {}

        return Paper(
            paper_id=_short_id(item.get("id")),
            title=title or "",
            authors=authors,
            abstract=abstract,
            doi=_strip_doi(item.get("doi")),
            published_date=published_date,
            pdf_url=pdf_url,
            url=url,
            source="openalex",
            categories=categories,
            citations=item.get("cited_by_count", 0),
            extra={
                "type": item.get("type"),
                "year": item.get("publication_year"),
                "is_retracted": item.get("is_retracted"),
                "language": item.get("language"),
                "venue": venue,
                "oa_status": oa.get("oa_status"),
                "license": best_oa.get("license"),
                "content_pdf_available": bool(has_content.get("pdf")),
            },
        )

    # ---- fulltext download ----------------------------------------------------------------

    def download_fulltext(
        self,
        items: List[Dict],
        project_path: str,
        dry_run: bool = False,
        max_files: int = 20,
        source: str = "auto",
    ) -> Dict:
        """Download PDFs into <project_path>/literature/fulltext/<key>.pdf.

        items: [{"id_or_doi": ..., "key": "author-year[a|b]"}]. One failed item never aborts
        the batch. Never overwrites. Never touches arti-lit.db.
        """
        if source not in {"auto", "openalex_content", "oa_location"}:
            raise ValueError("source must be auto | openalex_content | oa_location")
        if len(items) > max_files:
            raise ValueError(f"{len(items)} items exceeds max_files={max_files}; raise it "
                             "deliberately or split the batch (each content download costs $0.01)")
        api_key = os.environ.get("OPENALEX_API_KEY")
        need_key = source in {"auto", "openalex_content"}
        if need_key and not api_key and not dry_run:
            raise SourceFetchError(
                "OPENALEX_API_KEY is not set; OpenAlex content downloads require a (free) key. "
                "Use source='oa_location' to fetch from open-access locations without one.")

        dest_dir = os.path.realpath(os.path.join(project_path, "literature", "fulltext"))
        if not os.path.isdir(project_path):
            raise ValueError(f"project_path does not exist: {project_path}")

        report, est_cost, spent = [], 0.0, 0.0
        for item in items:
            key = str(item.get("key", ""))
            ref = str(item.get("id_or_doi", ""))
            row = {"key": key, "status": "error", "path": None, "bytes": 0, "source": None}
            report.append(row)
            try:
                if not _KEY_RE.match(key):
                    raise ValueError("key must match [a-z0-9-]+ (author-year[a|b])")
                dest = os.path.realpath(os.path.join(dest_dir, f"{key}.pdf"))
                if os.path.dirname(dest) != dest_dir:
                    raise ValueError("destination escapes literature/fulltext")
                row["path"] = dest
                if os.path.exists(dest):
                    row["status"] = "skipped_exists"
                    continue

                work = get_json_with_retry(
                    f"{API}/works/{_normalize_work_id(ref)}",
                    {"select": "id,has_content,best_oa_location,locations", **_auth_params()})
                wid = _short_id(work.get("id"))
                use_content = source != "oa_location" and (work.get("has_content") or {}).get("pdf")
                oa_urls = []
                if source != "openalex_content":
                    best = (work.get("best_oa_location") or {}).get("pdf_url")
                    oa_urls = [u for u in [best] + [
                        (loc or {}).get("pdf_url") for loc in work.get("locations") or []] if u]
                    oa_urls = list(dict.fromkeys(oa_urls))
                if not use_content and not oa_urls:
                    row["status"] = "no_content"
                    row["detail"] = "no OpenAlex-cached PDF and no OA pdf_url"
                    continue

                if dry_run:
                    row["status"] = "would_download"
                    row["source"] = "openalex_content" if use_content else oa_urls[0]
                    if use_content:
                        est_cost += _COST_PER_CONTENT_FILE
                    continue

                os.makedirs(dest_dir, exist_ok=True)
                tmp = dest + ".part"
                attempts = ([(f"{CONTENT_URL}/{wid}.pdf", {"Authorization": f"Bearer {api_key}"}, "openalex_content")]
                            if use_content else []) + [(u, None, u) for u in oa_urls]
                last_err = "no source tried"
                for url, headers, label in attempts:
                    try:
                        size, head = download_file(url, tmp, _MAX_PDF_BYTES, headers)
                    except SourceFetchError as e:
                        last_err = str(e)
                        continue
                    if head != b"%PDF":
                        last_err = f"not a PDF (publisher/landing page?): {label}"
                        os.remove(tmp)
                        continue
                    os.replace(tmp, dest)
                    row.update(status="ok", bytes=size, source=label)
                    if label == "openalex_content":
                        spent += _COST_PER_CONTENT_FILE
                    break
                else:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                    row["status"] = "no_content"
                    row["detail"] = last_err
            except Exception as e:  # one item failing must not cancel the batch
                row["status"] = "error"
                row["detail"] = str(e)

        counts: Dict[str, int] = {}
        for r in report:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
        summary = {"counts": counts, "dry_run": dry_run}
        if dry_run:
            summary["estimated_cost_usd"] = round(est_cost, 4)
        else:
            summary["cost_usd"] = round(spent, 4)
        return {"summary": summary, "items": report}
