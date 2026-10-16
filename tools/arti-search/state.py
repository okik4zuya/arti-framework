"""Throttle state shared between separate CLI processes.

Why it exists: the Google Scholar cooldown and the Semantic Scholar request spacing used to live in the
memory of one long-running MCP server. Every `cli.py` call is a new process, so without a file the
anti-block guards would reset on each call. The state is one small JSON at
`<arti home>/.cache/search-state.json` (override with the ARTI_SEARCH_STATE env var, used by tests):

    {"googlescholar": {"cooldown_until": <epoch s>, "consecutive_blocks": n, "last_call": <epoch s>,
                       "paused": false},
     "semanticscholar": {"last_call": <epoch s>}}

Timestamps are wall-clock (`time.time()`), because `time.monotonic()` means nothing across processes.
A missing, unreadable or corrupt file counts as "no state"; a failed write is ignored (a guard that
cannot persist must never break a search). Writes go through a temp file and `os.replace`.
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Dict

_ARTI_HOME = Path(__file__).resolve().parents[2]  # <arti home>/tools/arti-search/state.py


def state_path() -> Path:
    override = os.environ.get("ARTI_SEARCH_STATE")
    return Path(override) if override else _ARTI_HOME / ".cache" / "search-state.json"


def _load_all() -> Dict:
    try:
        data = json.loads(state_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load(section: str) -> Dict:
    """The stored dict for one section, or {} when there is none."""
    value = _load_all().get(section)
    return value if isinstance(value, dict) else {}


def save(section: str, values: Dict) -> None:
    """Replace one section, keeping the others. Errors are swallowed on purpose."""
    path = state_path()
    try:
        data = _load_all()
        data[section] = values
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".search-state-", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except OSError:
        pass
