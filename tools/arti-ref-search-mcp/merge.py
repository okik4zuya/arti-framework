"""Cross-source helpers: DOI/title normalization, de-duplication, title similarity."""
import re
from typing import Dict, List, Optional

_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"<>]+", re.I)


def extract_doi(text: Optional[str]) -> str:
    """First DOI found in free text or a URL, lowercased, trailing punctuation stripped."""
    m = _DOI_RE.search(text or "")
    return m.group(0).rstrip(".,;:)]}'\"").lower() if m else ""


def norm_doi(doi: Optional[str]) -> str:
    return extract_doi(doi)


def norm_title(title: Optional[str]) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def title_similarity(a: Optional[str], b: Optional[str]) -> float:
    """Token Jaccard on normalized titles (1.0 = same word set).

    A title cut short by a search UI ("... nonrandomized studies") is wholly contained in the full
    one; when the shorter side has >= 4 tokens, containment scores 0.9 so it still resolves.
    """
    ta, tb = set(norm_title(a).split()), set(norm_title(b).split())
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    jaccard = inter / len(ta | tb)
    if min(len(ta), len(tb)) >= 4 and inter == min(len(ta), len(tb)):
        return max(jaccard, 0.9)
    return jaccard


def dedupe_by_doi(results: List[Dict]) -> List[Dict]:
    """Keep the first of each paper dict, keyed by DOI, else by normalized title."""
    seen, out = set(), []
    for r in results:
        key = norm_doi(r.get("doi")) or norm_title(r.get("title"))
        if key and key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out
