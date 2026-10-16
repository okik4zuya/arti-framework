"""Config lookup shared by every source: process env first, then `<arti home>/mcp-keys.json`
(git-ignored, per machine, never shipped; the Settings > APIs page of the dashboard writes it).

The file keeps its old name on purpose: the dashboard, the installer checks and the licensing tests all
refer to `mcp-keys.json`, and renaming it would need a migration on every installed machine. An explicit
env var always wins. `--no-keys` on the CLI calls `ignore_keys()` to test the anonymous path.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional

_ARTI_HOME = Path(__file__).resolve().parents[2]  # <arti home>/tools/arti-search/config.py
_KEYS_JSON = _ARTI_HOME / "mcp-keys.json"

_cache: Optional[Dict[str, str]] = None
_ignore_keys = False


def ignore_keys() -> None:
    """Pretend no key is configured (env vars and mcp-keys.json both ignored) for this process."""
    global _ignore_keys
    _ignore_keys = True


def _file_env() -> Dict[str, str]:
    global _cache
    if _cache is None:
        _cache = {}
        try:
            keys = json.loads(_KEYS_JSON.read_text(encoding="utf-8"))
            _cache.update({k: str(v) for k, v in keys.items() if v})
        except (OSError, ValueError, AttributeError):
            pass
    return _cache


def get_env(name: str) -> Optional[str]:
    """Process env var if set and non-empty, else mcp-keys.json, else None."""
    if _ignore_keys:
        return None
    return os.environ.get(name) or _file_env().get(name)
