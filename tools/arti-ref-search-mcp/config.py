"""Config lookup shared by every source: process env first, then `<arti home>/mcp-keys.json`
(git-ignored, per machine, never shipped), then the ARTi home's `.mcp.json` stanza env.

Why: the user-scope MCP entry in `~/.claude.json` has `"env": {}`, so a session opened outside
`~/.arti` never saw OPENALEX_API_KEY (it lived only in `~/.arti/.mcp.json`, which Claude Code reads
for sessions started in that folder). Reading it here keeps one copy of the secret and makes the
key reachable from every project. An explicit env var always wins.
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional

_ARTI_HOME = Path(__file__).resolve().parents[2]  # <arti home>/tools/arti-ref-search-mcp/config.py
_MCP_JSON = _ARTI_HOME / ".mcp.json"
_KEYS_JSON = _ARTI_HOME / "mcp-keys.json"
_SERVER_NAME = "arti-ref-search-mcp"

_cache: Optional[Dict[str, str]] = None


def _file_env() -> Dict[str, str]:
    global _cache
    if _cache is None:
        _cache = {}
        try:
            cfg = json.loads(_MCP_JSON.read_text(encoding="utf-8"))
            env = cfg.get("mcpServers", {}).get(_SERVER_NAME, {}).get("env", {})
            _cache.update({k: str(v) for k, v in env.items() if v})
        except (OSError, ValueError):
            pass
        try:
            keys = json.loads(_KEYS_JSON.read_text(encoding="utf-8"))
            _cache.update({k: str(v) for k, v in keys.items() if v})
        except (OSError, ValueError):
            pass
    return _cache


def get_env(name: str) -> Optional[str]:
    """Process env var if set and non-empty, else mcp-keys.json, else the .mcp.json stanza env, else None."""
    return os.environ.get(name) or _file_env().get(name)
