"""Semantic Scholar source: relevance search, seed-based recommendations, singleton lookup.

Why it exists: OpenAlex `semantic` search depended on OpenAlex's own embedding service, which broke
on 2026-10-03 (TLS hostname mismatch). Semantic Scholar's recommendations endpoint is embedding-based
(SPECTER) and independent of that, and its `/paper/search` ranks by relevance over title+abstract.

Rate limits: unauthenticated calls share one global pool and returned HTTP 429 on every search
probed 2026-10-03 even after retries; a free API key (`SEMANTIC_SCHOLAR_API_KEY`) gets a dedicated
1 request/second. Calls are spaced `_MIN_INTERVAL` apart to stay under that.
"""
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

from config import get_env
from http_client import SourceFetchError, get_json_with_retry
from paper import Paper
from sources.base import PaperSource

GRAPH = "https://api.semanticscholar.org/graph/v1"
RECS = "https://api.semanticscholar.org/recommendations/v1"

_FIELDS = (
    "paperId,externalIds,title,abstract,year,publicationDate,venue,citationCount,"
    "influentialCitationCount,openAccessPdf,isOpenAccess,authors,publicationTypes,"
    "fieldsOfStudy"
)
_FIELDS_WITH_TLDR = _FIELDS + ",tldr"  # the recommendations endpoint rejects `tldr` (HTTP 400)
_MIN_INTERVAL = 1.1  # seconds between calls (key tier: 1 request/second)
_SEARCH_MAX = 100  # /paper/search page ceiling
_REC_MAX = 500
_last_call = 0.0


def _headers() -> Dict[str, str]:
    key = get_env("SEMANTIC_SCHOLAR_API_KEY")
    return {"x-api-key": key} if key else {}


def _call(url: str, params: Optional[Dict] = None, json_body=None) -> Dict:
    """One rate-spaced call. Adds a how-to-fix hint to a 429 when no key is configured."""
    global _last_call
    wait = _MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    try:
        return get_json_with_retry(url, params, _headers(), json_body)
    except SourceFetchError as e:
        if "HTTP 429" in str(e) and not get_env("SEMANTIC_SCHOLAR_API_KEY"):
            raise SourceFetchError(
                f"{e} -- no SEMANTIC_SCHOLAR_API_KEY configured, so the shared unauthenticated "
                "pool is saturated. Get a free key at semanticscholar.org/product/api and add "
                "SEMANTIC_SCHOLAR_API_KEY to the arti-ref-search-mcp env in <arti home>/.mcp.json."
            )
        raise
    finally:
        _last_call = time.monotonic()


def _normalize_ref(ref: str) -> str:
    """W-id/DOI/arXiv/S2 id -> the id form S2 paths accept (bare DOI gets the `DOI:` prefix)."""
    ref = ref.strip()
    ref = re.sub(r"^https?://(dx\.)?doi\.org/", "", ref)
    if ref.lower().startswith("doi:"):
        return "DOI:" + ref[4:]
    if ref.startswith("10."):
        return "DOI:" + ref
    return ref  # S2 paper id, CorpusId:, ARXIV:, PMID:, URL: already valid


def _seed_to_s2(ref: str) -> str:
    """Seed -> S2 id form. OpenAlex W-ids/URLs are resolved to their DOI first (free singleton)."""
    r = ref.strip()
    if re.fullmatch(r"W\d+", r, re.I) or r.startswith("https://openalex.org/"):
        from sources.openalex import OpenAlexSource  # lazy: avoids an import cycle

        doi = OpenAlexSource().get_work(r).get("doi")
        if not doi:
            raise ValueError(f"OpenAlex work {r} has no DOI; Semantic Scholar needs a DOI or S2 id")
        return "DOI:" + doi
    return _normalize_ref(r)


class SemanticScholarSource(PaperSource):
    """Semantic Scholar: search, recommendations, singleton."""

    def search(
        self,
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
        """Relevance search. Returns {"meta": {...}, "results": [Paper dict, ...]}.

        `query` is plain text (S2 ignores Boolean operators; hyphens and quotes can break it, so
        they are stripped). One request covers up to 100 results; use `offset` to page.
        """
        if max_results < 1:
            raise ValueError("max_results must be >= 1")
        clean = re.sub(r'["\-+|()~*]', " ", query).strip()
        if not clean:
            raise ValueError("query is empty after cleaning")
        params: Dict = {
            "query": clean,
            "limit": min(max_results, _SEARCH_MAX),
            "offset": max(0, offset),
            "fields": _FIELDS_WITH_TLDR,
        }
        if year_from is not None or year_to is not None:
            params["year"] = f"{year_from if year_from is not None else ''}-" \
                             f"{year_to if year_to is not None else ''}"
        if min_citations is not None:
            params["minCitationCount"] = int(min_citations)
        if open_access_only:
            params["openAccessPdf"] = ""  # presence of the key filters to papers with a PDF
        if publication_types:
            params["publicationTypes"] = publication_types
        if fields_of_study:
            params["fieldsOfStudy"] = fields_of_study

        data = _call(f"{GRAPH}/paper/search", params)
        papers = [self._parse(p, abstract_max_chars) for p in data.get("data") or []]
        return {
            "meta": {
                "count": data.get("total"),
                "returned": len(papers),
                "offset": data.get("offset", 0),
                "next_offset": data.get("next"),
            },
            "results": [p.to_dict() for p in papers],
        }

    def recommend(
        self,
        positive: List[str],
        negative: Optional[List[str]] = None,
        max_results: int = 20,
        abstract_max_chars: Optional[int] = None,
        year_from: Optional[int] = None,
        min_citations: Optional[int] = None,
        pool: str = "recent",
    ) -> Dict:
        """Papers similar to the positive seeds (and unlike the negative ones), embedding-based.

        `pool` ('recent' | 'all-cs') picks S2's candidate pool and exists only on the single-seed GET
        endpoint. Measured 2026-10-03 on an ANCOVA seed: 'recent' returned ~88 % 2026 papers with
        0-1 citations (on topic but unproven); 'all-cs' returned older, highly cited, textbook-heavy
        results. The POST endpoint (several seeds or any negative) has no pool and behaves like 'recent'.

        One seed uses the GET endpoint; several (or any negative) use POST. Seeds are DOIs, OpenAlex
        W-ids (resolved to DOIs), S2 ids, or `ARXIV:`/`PMID:`/`CorpusId:` ids. The endpoint has no
        filters and skews to recent zero-citation papers, so `year_from` / `min_citations` are applied
        here to an over-fetched list; `meta.filtered_out` reports how many were dropped.
        """
        if not positive:
            raise ValueError("recommend needs at least one positive seed")
        if pool not in {"recent", "all-cs"}:
            raise ValueError("pool must be 'recent' or 'all-cs'")
        if pool != "recent" and (len(positive) != 1 or negative):
            raise ValueError("pool='all-cs' works only with exactly one positive seed and no negatives")
        wanted = max(1, min(max_results, _REC_MAX))
        filtering = year_from is not None or min_citations is not None
        limit = min(_REC_MAX, max(wanted * 10, 100)) if filtering else wanted
        pos = [_seed_to_s2(r) for r in positive]
        neg = [_seed_to_s2(r) for r in negative or []]
        params = {"limit": limit, "fields": _FIELDS}
        if pool != "recent":
            params["from"] = pool
        if len(pos) == 1 and not neg:
            data = _call(f"{RECS}/papers/forpaper/{pos[0]}", params)
        else:
            data = _call(f"{RECS}/papers/", params,
                         {"positivePaperIds": pos, "negativePaperIds": neg})
        papers = [self._parse(p, abstract_max_chars) for p in data.get("recommendedPapers") or []]
        fetched = len(papers)
        if filtering:
            papers = [p for p in papers
                      if (year_from is None or (p.extra.get("year") or 0) >= year_from)
                      and (min_citations is None or p.citations >= min_citations)]
        passed = len(papers)
        papers = papers[:wanted]
        meta = {"returned": len(papers), "positive": pos, "negative": neg}
        if filtering:
            meta["fetched"] = fetched
            meta["filtered_out"] = fetched - passed
        return {"meta": meta, "results": [p.to_dict() for p in papers]}

    def get_paper(self, ref: str) -> Dict:
        """One paper by DOI or S2 id."""
        data = _call(f"{GRAPH}/paper/{_normalize_ref(ref)}", {"fields": _FIELDS_WITH_TLDR})
        return self._parse(data, None).to_dict()

    @staticmethod
    def _parse(item: Dict, abstract_max_chars: Optional[int]) -> Paper:
        abstract = item.get("abstract") or ""
        if abstract_max_chars and len(abstract) > abstract_max_chars:
            abstract = abstract[:abstract_max_chars].rstrip() + "..."
        ext = item.get("externalIds") or {}
        oa = item.get("openAccessPdf") or {}
        published = None
        if item.get("publicationDate"):
            try:
                published = datetime.strptime(item["publicationDate"], "%Y-%m-%d")
            except ValueError:
                pass
        pid = item.get("paperId") or ""
        return Paper(
            paper_id=pid,
            title=item.get("title") or "",
            authors=[a.get("name", "") for a in item.get("authors") or [] if a.get("name")],
            abstract=abstract,
            doi=ext.get("DOI") or "",
            published_date=published,
            pdf_url=oa.get("url") or "",
            url=f"https://www.semanticscholar.org/paper/{pid}" if pid else "",
            source="semanticscholar",
            categories=item.get("fieldsOfStudy") or [],
            citations=item.get("citationCount") or 0,
            extra={
                "year": item.get("year"),
                "venue": item.get("venue") or "",
                "influential_citations": item.get("influentialCitationCount"),
                "publication_types": item.get("publicationTypes"),
                "is_open_access": item.get("isOpenAccess"),
                "tldr": (item.get("tldr") or {}).get("text"),
            },
        )
