"""License gate for the dashboard server.

Offline check on every call (Ed25519 signature, machine hash, expiry), so a missing network never
slows or blocks the dashboard. Online calls (activate / refresh / deactivate) go through
tools/arti-license/cli.py, the same code the `arti-license` command uses.

States: missing | invalid  -> locked (only the License settings page and /api/license/* work)
        valid | grace | expired -> open; grace and expired only show a banner and stop updates.
The skills and tools in Claude Code never look at this: only the dashboard is gated.
"""
import importlib.util
import json
import math
import os
import sys
import threading
import time
from pathlib import Path

# Code lives next to this file; license.json / mcp-keys.json live under ARTI_HOME (env override for tests).
CODE_HOME = Path(__file__).resolve().parent.parent.parent
REFRESH_EVERY_S = 7 * 24 * 3600

sys.path.insert(0, str(CODE_HOME / "tools" / "_shared"))
import license as lic  # noqa: E402


def _load_cli():
    spec = importlib.util.spec_from_file_location("arti_license_cli", CODE_HOME / "tools" / "arti-license" / "cli.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cli = _load_cli()

# Paths the dashboard must keep serving while locked: the lock screen itself and plain liveness.
OPEN_WHILE_LOCKED = ("/api/ping", "/api/focus", "/api/shutdown", "/api/license/", "/api/about")


def _days_left(iso):
    try:
        return math.ceil((lic.parse_time(iso) - lic.utcnow()).total_seconds() / 86400)
    except (TypeError, ValueError):
        return None


def status():
    """Plain dict for the UI. Never contains the license key or the signature."""
    base = {"machine": lic.machine_label()}
    try:
        cur = lic.read_license()
    except FileNotFoundError:
        return dict(base, state="missing", locked=True, reason="no_license")
    except (OSError, ValueError):
        return dict(base, state="invalid", locked=True, reason="unreadable")
    info = lic.evaluate(cur)
    state = info["state"]
    out = dict(base, state=state, locked=state == "invalid", reason=info.get("reason"))
    if state != "invalid":
        key_id = str(info.get("key_id") or "")
        out.update(name=info.get("name"), tier=info.get("tier"), key_id=key_id,
                   expires=info.get("expires"), updates_until=info.get("updates_until"),
                   days_left=_days_left(info.get("expires")), grace_ends=info.get("grace_ends"))
    return out


def is_locked():
    return status()["locked"]


def blocks(pathname):
    """True if this API path must be refused right now."""
    return pathname.startswith("/api/") and not pathname.startswith(OPEN_WHILE_LOCKED) and is_locked()


def _fail(e):
    code = getattr(e, "code", "error")
    return {"ok": False, "code": code, "error": cli.MESSAGES.get(code, str(e))}


def activate(key):
    try:
        cli.activate_key(key)
    except cli.ApiFailure as e:
        return _fail(e)
    return {"ok": True, "status": status()}


def refresh():
    try:
        cli.refresh_license()
    except FileNotFoundError:
        return {"ok": False, "code": "not_found", "error": "No license installed."}
    except cli.ApiFailure as e:
        return _fail(e)
    return {"ok": True, "status": status()}


def deactivate():
    try:
        cli.deactivate_local()
    except FileNotFoundError:
        return {"ok": False, "code": "not_found", "error": "No license installed."}
    except cli.ApiFailure as e:
        return _fail(e)
    return {"ok": True, "status": status()}


def refresh_in_background():
    """At most one silent online refresh per week, started once at server start. Any failure
    (offline, revoked, server down) is ignored: the offline check above stays authoritative."""
    def run():
        try:
            path = Path(lic.license_path())
            if path.is_file() and time.time() - path.stat().st_mtime > REFRESH_EVERY_S:
                cli.refresh_license()
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


# ---- API keys (mcp-keys.json) ----------------------------------------------------------------

KEY_FIELDS = ("OPENALEX_API_KEY", "SEMANTIC_SCHOLAR_API_KEY", "ARTI_REF_CONTACT_EMAIL")
SECRET_FIELDS = ("OPENALEX_API_KEY", "SEMANTIC_SCHOLAR_API_KEY")


def _keys_path():
    return Path(lic.ARTI_HOME) / "mcp-keys.json"


def _read_keys():
    try:
        return json.loads(_keys_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def keys_view():
    """What the UI may see: secrets only as 'set' + last 4 characters, the email in full."""
    stored = _read_keys()
    out = {}
    for name in KEY_FIELDS:
        value = str(stored.get(name) or "")
        if name in SECRET_FIELDS:
            out[name] = {"set": bool(value), "hint": value[-4:] if len(value) > 8 else ""}
        else:
            out[name] = {"set": bool(value), "value": value}
    return out


def keys_save(updates):
    """Set or clear (empty string) individual fields; unknown names are ignored."""
    stored = _read_keys()
    for name, value in (updates or {}).items():
        if name not in KEY_FIELDS:
            continue
        value = str(value or "").strip()
        if value:
            stored[name] = value
        else:
            stored.pop(name, None)
    path = _keys_path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(stored, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return keys_view()
