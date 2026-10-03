"""Resolve externally found candidates (DOI / URL / title strings) to verified OpenAlex records.

Used for lists that come from outside this server (Google Scholar by hand, Elicit, Scopus AI,
Connected Papers). Nothing here touches the network except OpenAlex, and the project library
(`literature/arti-lit.db`) is opened read-only.
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set

from http_client import SourceFetchError
from merge import extract_doi, norm_doi, norm_title, title_similarity

_RESOLVED_MIN = 0.85
_AMBIGUOUS_MIN = 0.6
_MAX_ITEMS = 50
NOTE = ("[UNVERIFIED - USER MUST CONFIRM] Records come from OpenAlex metadata (abstract-only); "
        "'resolved' means the identifier/title matched, not that the paper fits the claim.")


def _library_dois(project_path: Optional[str]) -> Set[str]:
    """DOIs already in <project>/literature/arti-lit.db (read-only); empty set if unavailable."""
    if not project_path:
        return set()
    db = Path(project_path) / "literature" / "arti-lit.db"
    if not db.is_file():
        return set()
    try:
        con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
        try:
            return {norm_doi(r[0]) for r in con.execute(
                "select doi from sources where doi is not null and doi != ''") if norm_doi(r[0])}
        finally:
            con.close()
    except sqlite3.Error:
        return set()


def _record(d: Dict, in_library: bool) -> Dict:
    extra = d.get("extra") or {}
    return {
        "openalex_id": d.get("paper_id"),
        "doi": d.get("doi"),
        "title": d.get("title"),
        "year": extra.get("year"),
        "type": extra.get("type"),
        "is_retracted": extra.get("is_retracted"),
        "oa_status": extra.get("oa_status"),
        "content_pdf_available": extra.get("content_pdf_available"),
        "abstract_present": bool(d.get("abstract")),
        "cited_by_count": d.get("citations"),
        "in_library": in_library,
    }


def resolve_candidates(source, items: List[str], project_path: Optional[str] = None) -> Dict:
    """Resolve each item. `source` is an OpenAlexSource. One bad item never aborts the batch."""
    if not items:
        raise ValueError("items is empty")
    if len(items) > _MAX_ITEMS:
        raise ValueError(f"{len(items)} items exceeds the cap of {_MAX_ITEMS}")
    lib = _library_dois(project_path)
    out, counts = [], {"resolved": 0, "ambiguous": 0, "unresolved": 0, "error": 0}

    for raw in items:
        text = (raw or "").strip()
        row: Dict = {"input": text}
        try:
            doi = extract_doi(text)
            if doi:
                work = source.get_work(doi)
                row.update(status="resolved", **_record(work, norm_doi(work.get("doi")) in lib))
            else:
                row.update(_resolve_title(source, text, lib))
        except SourceFetchError as e:
            msg = str(e)
            if "HTTP 404" in msg:
                row.update(status="unresolved", reason="DOI not found in OpenAlex")
            else:
                row.update(status="error", reason=msg[:200])
        except ValueError as e:
            row.update(status="error", reason=str(e)[:200])
        counts[row["status"]] += 1
        out.append(row)

    return {"note": NOTE, "summary": {**counts, "total": len(out), "library_checked": bool(project_path)},
            "items": out}


def _resolve_title(source, title: str, lib: Set[str]) -> Dict:
    if len(norm_title(title).split()) < 3:
        return {"status": "unresolved", "reason": "too short to match as a title"}
    hits = source._search(title, max_results=5, search_in="title", include_abstract=True,
                          exclude_retracted=False)["results"]
    scored = sorted(((title_similarity(title, h.get("title")), h) for h in hits),
                    key=lambda x: -x[0])
    if not scored or scored[0][0] < _AMBIGUOUS_MIN:
        return {"status": "unresolved", "reason": "no OpenAlex title close enough"}
    best_score, best = scored[0]
    if best_score >= _RESOLVED_MIN:
        return {"status": "resolved", "title_similarity": round(best_score, 2),
                **_record(best, norm_doi(best.get("doi")) in lib)}
    return {"status": "ambiguous",
            "candidates": [{"title_similarity": round(s, 2), **_record(h, norm_doi(h.get("doi")) in lib)}
                           for s, h in scored[:3] if s >= _AMBIGUOUS_MIN]}
