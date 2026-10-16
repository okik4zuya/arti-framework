"""License gate for the dashboard server.

Offline check on every call (Ed25519 signature, machine hash, expiry), so a missing network never
slows or blocks the dashboard. Online calls (activate / refresh / deactivate) go through
tools/arti-license/cli.py, the same code the `arti-license` command uses.

States: missing | invalid | revoked -> locked (only the License settings page and /api/license/* work)
        valid | grace | expired -> open; grace and expired only show a banner and stop updates.
revoked = the server answered key_revoked and license.json was set aside as license.revoked.json
(cli.mark_revoked); it is learned by the online check at start and every 12 hours, never offline.
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
REFRESH_EVERY_S = 3 * 24 * 3600   # a usable license is re-validated online when its file is older than this
MIN_RETRY_S = 6 * 3600             # at most one attempt per this long, success or not (many starts, flaky network)
TICK_EVERY_S = 12 * 3600       # how often a running dashboard asks again
BACKGROUND_TIMEOUT_S = 4

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
        if cli.is_revoked():
            return dict(base, state="revoked", locked=True, reason="revoked")
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
                   days_left=_days_left(info.get("expires")), grace_ends=info.get("grace_ends"),
                   clock_behind=bool(info.get("clock_behind")))
    return out


def is_locked():
    return status()["locked"]


def blocks(pathname):
    """True if this API path must be refused right now."""
    return pathname.startswith("/api/") and not pathname.startswith(OPEN_WHILE_LOCKED) and is_locked()


def _fail(e):
    code = getattr(e, "code", "error")
    return {"ok": False, "code": code, "error": cli.message_for(e)}


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
        return dict(_fail(e), status=status())
    return {"ok": True, "status": status()}


def recheck():
    """'Check again' on a revoked license: restores it if the server no longer revokes it."""
    try:
        cli.recheck_revoked()
    except FileNotFoundError:
        return {"ok": False, "code": "not_found", "error": "No revoked license is stored."}
    except cli.ApiFailure as e:
        return dict(_fail(e), status=status())
    return {"ok": True, "status": status()}


def deactivate():
    try:
        cli.deactivate_local()
    except FileNotFoundError:
        return {"ok": False, "code": "not_found", "error": "No license installed."}
    except cli.ApiFailure as e:
        return _fail(e)
    return {"ok": True, "status": status()}


def refresh_due():
    """Should the dashboard ask the server about this license now?

    Yes for a grace or expired license (so a renewal shows up on its own), or once the file is older
    than REFRESH_EVERY_S (3 days, +-1 h jitter) since the last confirmation (validate, or the update heartbeat); never more than one attempt per MIN_RETRY_S, so repeated starts or an
    unreachable server cannot turn into a stream of requests. A revoke is also caught earlier by the
    daily update check (tools/arti-update), which shares the same server answer."""
    path = Path(lic.license_path())
    if not path.is_file() or time.time() - float(lic.read_check().get("attempted_at", 0) or 0) < MIN_RETRY_S:
        return False
    if status()["state"] in ("grace", "expired"):
        return True
    return time.time() - lic.last_confirmed() > lic.jittered(REFRESH_EVERY_S)


def background_tick():
    """One silent check. Any failure (offline, server down) is ignored: the offline verdict stays
    authoritative. A key_revoked answer locks the dashboard (cli.refresh_license sets the file aside)."""
    try:
        if refresh_due():
            lic.write_check(attempted_at=time.time())
            cli.refresh_license(timeout=BACKGROUND_TIMEOUT_S)
    except Exception:
        pass


def refresh_in_background():
    """Check at server start, then every TICK_EVERY_S while the dashboard stays open."""
    def run():
        while True:
            background_tick()
            time.sleep(TICK_EVERY_S)
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
