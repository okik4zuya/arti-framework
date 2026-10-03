"""Google Scholar source: one-page keyword search by direct HTML fetch (a scraping route).

Design adapted from openags/paper-search-mcp (MIT, Copyright 2025 OPENAGS),
`academic_platforms/google_scholar.py` on `main` (user-agent rotation, CONSENT cookie, `div.gs_ri`
parsing, CAPTCHA/consent detection, exponential cooldown with Retry-After). Changes here:
- every failure raises SourceFetchError (the installed 0.1.4 returned [] on CAPTCHA/HTTP errors,
  which is indistinguishable from a real zero-result page); a genuine empty page returns [];
- one request per call (max 10 results; `start` pages), >= _MIN_INTERVAL seconds between requests;
- stable md5 paper ids (the original used the per-process-random `hash(url)`).

Scholar has no official API; this reads the public HTML from the researcher's own IP, which is
against Scholar's terms and can trigger CAPTCHA blocks. It is for discovery only: the snippet is
not an abstract, `citations` stays 0 (Scholar's count is not parsed), and DOIs come only from
what the page shows. Never use it as the authority for citation counts (see citation-chase
HANDOFF.md Path D, which this route deliberately does not touch).
"""
import hashlib
import math
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from threading import Lock
from typing import Dict, Optional

import requests
from bs4 import BeautifulSoup

from config import get_env
from http_client import SourceFetchError
from merge import extract_doi
from paper import Paper
from sources.base import PaperSource

SCHOLAR_URL = "https://scholar.google.com/scholar"
_BROWSERS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
]
_COOLDOWN_SECONDS = 60.0
_MAX_COOLDOWN_SECONDS = 900.0
_MAX_RETRY_AFTER_SECONDS = 86400.0
_MIN_INTERVAL = 3.0
_PAGE_SIZE = 10
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0
_FALLBACK_HINT = "Use search_openalex_works or search_semanticscholar_papers instead."


def _retry_after(response) -> float:
    """Retry-After as seconds (delta or HTTP date); inf when beyond the supported horizon."""
    value = (getattr(response, "headers", None) or {}).get("Retry-After", "").strip()
    if not value:
        return 0.0
    try:
        if value.isascii() and value.isdigit():
            digits = value.lstrip("0") or "0"
            delay = float(digits) if len(digits) <= 10 else math.inf
        else:
            at = parsedate_to_datetime(value)
            if at.tzinfo is None:
                return 0.0
            delay = (at - datetime.now(timezone.utc)).total_seconds()
        return math.inf if delay > _MAX_RETRY_AFTER_SECONDS else max(0.0, delay)
    except (TypeError, ValueError, OverflowError):
        return 0.0


def _is_captcha(soup: BeautifulSoup, text: str) -> bool:
    return bool(
        soup.find("form", {"id": "gs_captcha_f"})
        or soup.find("input", {"name": "captcha"})
        or "please show you're not a robot" in text
        or "unusual traffic from your computer network" in text
    )


def _is_consent(soup: BeautifulSoup, text: str) -> bool:
    return bool(
        soup.find("form", {"action": re.compile(r"consent\.google", re.I)})
        or "before you continue to google scholar" in text
    )


class GoogleScholarSource(PaperSource):
    """Google Scholar keyword search (single page per call)."""

    def __init__(self):
        self._lock = Lock()
        self._cooldown_until = 0.0
        self._consecutive_blocks = 0
        self._last_call = 0.0
        self._session: Optional[requests.Session] = None

    # ---- session / cooldown ----------------------------------------------------------------

    def _new_session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({
            "User-Agent": random.choice(_BROWSERS),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        })
        s.cookies.set("CONSENT", "YES+", domain=".google.com")
        proxy = (get_env("GOOGLE_SCHOLAR_PROXY_URL") or "").strip()
        if proxy:
            s.proxies.update({"http": proxy, "https": proxy})
        return s

    def cooldown_remaining(self) -> float:
        if math.isinf(self._cooldown_until):
            return math.inf
        return max(0.0, self._cooldown_until - time.monotonic())

    def status(self) -> Dict:
        rem = self.cooldown_remaining()
        return {"cooldown_remaining_s": None if math.isinf(rem) else round(rem),
                "paused_for_process": math.isinf(rem),
                "proxy_configured": bool(get_env("GOOGLE_SCHOLAR_PROXY_URL"))}

    def _begin_cooldown(self, response=None) -> None:
        self._consecutive_blocks = min(self._consecutive_blocks + 1, 5)
        delay = min(_COOLDOWN_SECONDS * (2 ** (self._consecutive_blocks - 1)), _MAX_COOLDOWN_SECONDS)
        if response is not None:
            delay = max(delay, _retry_after(response))
        self._cooldown_until = max(self._cooldown_until, time.monotonic() + delay)

    def _cooldown_hint(self) -> str:
        if math.isinf(self._cooldown_until):
            return ("Upstream Retry-After exceeds 24 hours; Scholar requests are paused for this "
                    "process. " + _FALLBACK_HINT)
        return f"Retry after {math.ceil(self.cooldown_remaining())} seconds. {_FALLBACK_HINT}"

    # ---- search ----------------------------------------------------------------------------

    def search(
        self,
        query: str,
        max_results: int = 10,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        start: int = 0,
    ) -> Dict:
        """One Scholar results page. Returns {"meta": {...}, "results": [Paper dict, ...]}.

        Raises SourceFetchError for CAPTCHA, consent wall, HTTP 403/429/503 after retries, or a
        network failure; returns an empty `results` only for a real no-result page.
        """
        if not query or not query.strip():
            raise ValueError("query is empty")
        if max_results < 1:
            raise ValueError("max_results must be >= 1")
        max_results = min(max_results, _PAGE_SIZE)
        if not self._lock.acquire(timeout=30):
            raise SourceFetchError("Google Scholar is busy (another search holds the session). "
                                   + _FALLBACK_HINT)
        try:
            if time.monotonic() < self._cooldown_until:
                raise SourceFetchError("Google Scholar is cooling down after an access limit. "
                                       + self._cooldown_hint())
            return self._fetch_page(query, max_results, year_from, year_to, max(0, start))
        finally:
            self._lock.release()

    def _fetch_page(self, query, max_results, year_from, year_to, start) -> Dict:
        params = {"q": query, "start": start, "hl": "en", "as_sdt": "0,5"}
        if year_from is not None:
            params["as_ylo"] = int(year_from)
        if year_to is not None:
            params["as_yhi"] = int(year_to)
        if self._session is None:
            self._session = self._new_session()

        consent_retried = False
        response = None
        for attempt in range(_MAX_RETRIES):
            wait = _MIN_INTERVAL - (time.monotonic() - self._last_call)
            time.sleep(max(0.0, wait) + random.uniform(0.0, 1.0))
            self._session.headers["User-Agent"] = random.choice(_BROWSERS)
            try:
                response = self._session.get(SCHOLAR_URL, params=params, timeout=30)
            except requests.RequestException as e:
                # Not echoing the exception text: it can contain the proxy URL and credentials.
                raise SourceFetchError(
                    f"Google Scholar request failed ({type(e).__name__}); check connectivity or "
                    f"GOOGLE_SCHOLAR_PROXY_URL. {_FALLBACK_HINT}") from None
            finally:
                self._last_call = time.monotonic()

            soup = None
            if response.status_code in (200, 403, 429, 503):
                soup = BeautifulSoup(response.text, "html.parser")
                text = soup.get_text(" ", strip=True).lower()
                if _is_captcha(soup, text):
                    self._begin_cooldown(response)
                    raise SourceFetchError("Google Scholar returned a bot-detection/CAPTCHA page. "
                                           + self._cooldown_hint())
            if response.status_code == 200:
                if _is_consent(soup, text):
                    if consent_retried:
                        raise SourceFetchError("Google Scholar returned a consent page after retry. "
                                               + _FALLBACK_HINT)
                    consent_retried = True
                    self._session.cookies.set("CONSENT", "YES+", domain=".google.com")
                    continue
                break
            if response.status_code in (403, 429, 503):
                retry_after = _retry_after(response)
                if retry_after > 30.0 or attempt == _MAX_RETRIES - 1:
                    break
                time.sleep(max(_RETRY_DELAY * (2 ** attempt) + random.uniform(0, 0.5), retry_after))
                continue
            break  # non-retryable status

        if response is None or response.status_code != 200:
            code = getattr(response, "status_code", "no response")
            hint = _FALLBACK_HINT
            if code in (403, 429, 503):
                self._begin_cooldown(response)
                hint = self._cooldown_hint()
            raise SourceFetchError(f"Google Scholar search failed: HTTP {code}. {hint}")

        self._consecutive_blocks = 0
        self._cooldown_until = 0.0
        papers = []
        for item in soup.find_all("div", class_="gs_ri"):
            paper = self._parse(item)
            if paper:
                papers.append(paper)
            if len(papers) >= max_results:
                break
        return {
            "meta": {"returned": len(papers), "start": start, "next_start": start + _PAGE_SIZE,
                     "source_note": "Google Scholar HTML (scraping route); snippet only, citations not parsed"},
            "results": [p.to_dict() for p in papers],
        }

    # ---- parsing ---------------------------------------------------------------------------

    @staticmethod
    def _year(text: str) -> Optional[int]:
        for word in re.findall(r"\b(?:19|20)\d{2}\b", text):
            if 1900 <= int(word) <= datetime.now().year:
                return int(word)
        return None

    def _parse(self, item) -> Optional[Paper]:
        title_el = item.find("h3", class_="gs_rt")
        info_el = item.find("div", class_="gs_a")
        snippet_el = item.find("div", class_="gs_rs")
        if not title_el or not info_el:
            return None
        title = re.sub(r"^\s*\[(PDF|HTML|BOOK|CITATION)\]\s*", "", title_el.get_text(" ", strip=True), flags=re.I)
        link = title_el.find("a", href=True)
        url = link["href"] if link else ""
        info = info_el.get_text(" ", strip=True)
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
        authors = [a.strip() for a in info.split(" - ")[0].split(",") if a.strip()]
        year = self._year(info)
        doi = extract_doi(url) or extract_doi(title) or extract_doi(info) or extract_doi(snippet)
        pid = "gs_" + hashlib.md5((url or title).encode("utf-8")).hexdigest()[:12]
        return Paper(
            paper_id=pid,
            title=title,
            authors=authors,
            abstract=snippet,
            doi=doi,
            published_date=datetime(year, 1, 1) if year else None,
            pdf_url="",
            url=url,
            source="google_scholar",
            categories=[],
            citations=0,
            extra={"year": year, "snippet_only": True, "venue_line": info[:200]},
        )
