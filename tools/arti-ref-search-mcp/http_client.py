"""Shared retry/backoff GET-JSON helper, reused by every source module.

Ported from `tools/citation-chase/cli.py`'s `http_get_json` (same repo, proven in production).
The original `paper-search-mcp` package's OpenAlex connector had no retry/backoff at all and
swallowed every failure into an empty list -- indistinguishable from a genuine zero-match query.
This helper fixes that by raising on exhausted retries or a non-retryable HTTP error instead of
returning `None`/`{}`; a real 200 response with zero results still returns an empty `results` list,
so the two cases stay distinguishable by construction.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

MAX_RETRIES = 5
USER_AGENT = "arti-ref-search-mcp/0.1 (~/.arti/tools/arti-ref-search-mcp)"


class SourceFetchError(RuntimeError):
    """Raised when a source's HTTP fetch fails after retries or hits a non-retryable error.

    Any `api_key=` value in the message is redacted -- these errors are shown to the model.
    """

    def __init__(self, message):
        super().__init__(re.sub(r"(api_key=)[^&\s]+", r"***", str(message)))


def _error_detail(e):
    """OpenAlex puts the real reason (bad filter name, etc.) in the 4xx body; surface it."""
    try:
        body = json.loads(e.read().decode("utf-8"))
        msg = body.get("message") or body.get("error")
        return f" -- {msg}" if msg else ""
    except Exception:
        return ""


def get_json_with_retry(url, params=None, headers=None):
    """GET url (+ params) and return parsed JSON. Raises SourceFetchError on failure."""
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{url}?{query}" if query else url

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 or 500 <= e.code < 600:
                if attempt == MAX_RETRIES - 1:
                    raise SourceFetchError(f"HTTP {e.code} after {MAX_RETRIES} retries: {url}")
                time.sleep(delay)
                delay *= 2
                continue
            raise SourceFetchError(f"HTTP {e.code}: {url}{_error_detail(e)}")
        except urllib.error.URLError as e:
            if attempt == MAX_RETRIES - 1:
                raise SourceFetchError(f"network error after {MAX_RETRIES} retries: {e}")
            time.sleep(delay)
            delay *= 2
    raise SourceFetchError(f"exhausted retries: {url}")


def download_file(url, dest_tmp, max_bytes, headers=None, timeout=60):
    """Stream url to dest_tmp, aborting past max_bytes. Returns (bytes_written, first_4_bytes).

    No retry loop: a failed download is reported per item by the caller, not retried silently
    (each OpenAlex content download costs money).
    """
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    written, head = 0, b""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_tmp, "wb") as out:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                if not head:
                    head = chunk[:4]
                written += len(chunk)
                if written > max_bytes:
                    raise SourceFetchError(f"file exceeds {max_bytes} bytes: {url}")
                out.write(chunk)
    except urllib.error.HTTPError as e:
        raise SourceFetchError(f"HTTP {e.code}: {url}{_error_detail(e)}")
    except urllib.error.URLError as e:
        raise SourceFetchError(f"network error: {e}")
    return written, head
