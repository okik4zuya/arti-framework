"""Crossref lookup for `arti-lit library enrich`: DOI -> CSL-JSON (the item format Zotero and
CSL engines consume). Self-contained on purpose -- `arti-ref-search-mcp`'s retry helper lives in a
hyphenated directory that isn't importable as a package, so the small retry loop is copied here
rather than reached across tools.

Crossref asks polite clients to identify themselves: the contact email (env
`ARTI_REF_CONTACT_EMAIL`, shared with arti-ref-search-mcp) goes in the User-Agent and as `mailto`.
"""
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.crossref.org/works/"
MAX_RETRIES = 4
CSL_ACCEPT = "application/vnd.citationstyles.csl+json"


class CrossrefError(RuntimeError):
    pass


def _user_agent():
    mailto = os.environ.get("ARTI_REF_CONTACT_EMAIL")
    base = "arti-lit/0.1 (~/.arti/tools/arti-lit"
    return f"{base}; mailto:{mailto})" if mailto else f"{base})"


def normalize_doi(doi):
    doi = (doi or "").strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", doi, flags=re.I)
    return doi


def fetch_csl(doi):
    """Return the CSL-JSON dict for `doi`. Raises CrossrefError on any failure (incl. 404)."""
    doi = normalize_doi(doi)
    if not doi:
        raise CrossrefError("empty DOI")
    url = API + urllib.parse.quote(doi, safe="/") + "/transform/" + CSL_ACCEPT
    mailto = os.environ.get("ARTI_REF_CONTACT_EMAIL")
    if mailto:
        url += "?" + urllib.parse.urlencode({"mailto": mailto})
    req = urllib.request.Request(url, headers={"User-Agent": _user_agent()})
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            if (e.code == 429 or 500 <= e.code < 600) and attempt < MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise CrossrefError(f"HTTP {e.code} for DOI {doi}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise CrossrefError(f"network error for DOI {doi}: {e}")
    if not isinstance(data, dict) or "title" not in data:
        raise CrossrefError(f"unexpected Crossref response for DOI {doi}")
    return data
