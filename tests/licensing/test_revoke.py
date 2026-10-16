"""Revoke and seat-release behaviour of the client, API level plus the real dashboard in a system browser.

Revoke locks the dashboard only: skills and tools (here a real tool run as a subprocess) keep working, and
nothing re-activates the revoked key by itself. Isolated data home, steerable fake Worker."""
import base64, datetime, json, os, re, subprocess, sys, tempfile, threading, time
import urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import CODE, SHOTS, BROWSER  # noqa: E402

HOME = Path(tempfile.mkdtemp(prefix="arti-revoke-home-"))
ENV = dict(ARTI_HOME=str(HOME), ARTI_MACHINE_ID="test-machine-1", ARTI_LICENSE_API="http://127.0.0.1:4192/v1")
os.environ.update(ENV)
sys.path.insert(0, str(CODE / "dashboard" / "server")); sys.path.insert(0, str(CODE / "tools" / "_shared"))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import license as lic

PRIV = Ed25519PrivateKey.generate()
PK = HOME / "pubkeys.test.json"
PK.write_text(json.dumps({"license": {"test-a": base64.b64encode(PRIV.public_key().public_bytes(
    serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()}, "release": {}}))
lic.PUBKEYS_PATH = str(PK)
fmt = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_license(machine, days=365):
    now = lic.utcnow()
    p = {"key_id": "lic_TEST42", "name": "Test Buyer", "tier": "individual", "seats": 1, "machine_hash": machine,
         "issued": fmt(now), "expires": fmt(now + datetime.timedelta(days=days)), "grace_days": 14,
         "updates_until": fmt(now + datetime.timedelta(days=days))}
    return {"payload": p, "sig": base64.b64encode(PRIV.sign(lic.canonical_json(p))).decode(), "kid": "test-a"}


STEER, CALLS = {}, []
REVOKED = {"code": "key_revoked", "message": "this license was revoked"}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        path = self.path.replace("/v1", "")
        CALLS.append((path, body))
        code, out = STEER.get(path, (200, None))
        if out is None:
            if path in ("/activate", "/validate"):
                out = {"license": make_license(body["machine_hash"]), "seats_used": 1}
            elif path == "/activations":
                out = {"key_id": "lic_TEST42", "seats": 1, "status": "active", "expires": "2027-01-01T00:00:00Z",
                       "activations": [{"machine_hash": "c" * 64, "label": "Windows OLD-LAPTOP", "last_seen": "2026-09-01T00:00:00Z", "deactivated": 0}]}
            else:
                out = {"ok": True}
        data = json.dumps(out).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)


fake = ThreadingHTTPServer(("127.0.0.1", 4192), Fake)
threading.Thread(target=fake.serve_forever, daemon=True).start()

import license_gate as gate
import update_check
update_check.check_in_background = lambda: None  # the start-up update check would race the steered state
import server as dash
dash.PORT = 4193
httpd = dash.create_server()
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:4193"


def api(path, data=None):
    req = urllib.request.Request(BASE + path, data=None if data is None else json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"}, method="GET" if data is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


def put(l):
    (HOME / "license.json").write_text(json.dumps(l))


def reset_attempt():
    (HOME / ".license-check.json").unlink(missing_ok=True)


def age_file(hours):
    t = time.time() - hours * 3600
    os.utime(HOME / "license.json", (t, t))


def run_cli(script, *argv):
    r = subprocess.run([sys.executable, str(CODE / script), *argv], capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, **ENV, ARTI_LICENSE_PUBKEYS=str(PK)))
    return r.returncode, r.stdout + r.stderr


me = lic.machine_hash()
KEY = lic.format_key("ABCDEFGHJKMNPQR" + lic.checksum_char("ABCDEFGHJKMNPQR"))
REV = HOME / "license.revoked.json"

# ---- cadence: when the client asks ---------------------------------------------------------------
put(make_license(me)); age_file(48)
check("a license validated 2 days ago is not re-checked", not gate.refresh_due())
age_file(80)
check("a license validated 3 days and 8 hours ago is re-checked at start", gate.refresh_due())
check("the background check uses a short timeout", gate.BACKGROUND_TIMEOUT_S <= 5)

# ---- revoke noticed by the background check ------------------------------------------------------
STEER["/validate"] = (403, REVOKED)
reset_attempt(); gate.background_tick()
s = gate.status()
check("revoked: state is revoked and locked, with its own reason", s["state"] == "revoked" and s["locked"] and s["reason"] == "revoked", s)
check("revoked: license.json set aside as license.revoked.json", REV.exists() and not (HOME / "license.json").exists())
st, body = api("/api/data")
check("revoked: API answers 403 license_required", st == 403 and body.get("code") == "license_required", (st, body))
st, body = api("/api/license/status")
check("revoked: the License status stays reachable", st == 200 and body["state"] == "revoked")
n = len(CALLS)
gate.background_tick(); gate.background_tick()
check("revoked: no further calls, and the key is never re-activated by itself", len(CALLS) == n and not any(c[0] == "/activate" for c in CALLS))

# ---- skills and tools are untouched -----------------------------------------------------------------
rc, out = run_cli("tools/arti-license/cli.py", "verify")
check("revoked: 'verify' (the only thing ARTi-setup runs) exits 2 with the revoked text", rc == 2 and "REVOKED" in out, (rc, out))
rc, out = run_cli("tools/arti-license/cli.py", "status")
check("revoked: 'status' says revoked", rc == 2 and "REVOKED" in out, (rc, out))
note = HOME / "note.md"
note.write_text("A sentence {==with a comment==}{>>#a1 open | check this<<} here.\n", encoding="utf-8")
rc, out = run_cli("tools/arti-annotate/cli.py", "list", str(note))
check("revoked: a real tool (arti-annotate) still runs", rc == 0 and "a1" in out, (rc, out))
readers = []
for root in ("skills", "tools"):
    for f in (CODE / root).rglob("*"):
        if f.suffix in (".py", ".md", ".ps1", ".sh", ".mjs", ".js") and "__pycache__" not in f.parts:
            rel = f.relative_to(CODE).as_posix()
            if rel.startswith(("tools/arti-license/", "tools/arti-update/", "tools/_shared/license.py")):
                continue
            if re.search(r"license\.json|license_gate|arti-license|read_license", f.read_text(encoding="utf-8", errors="ignore")):
                readers.append(rel)
check("no skill or tool outside arti-license/arti-update reads the license (only ARTi-setup's notice may mention it)",
      readers == ["skills/ARTi-setup/SKILL.md"], readers)

# ---- check again ------------------------------------------------------------------------------------
st, body = api("/api/license/recheck", {})
check("check again while still revoked: clear message, stays locked",
      st == 400 and body["code"] == "key_revoked" and "revoked" in body["error"] and gate.status()["state"] == "revoked", body)
STEER.pop("/validate")
st, body = api("/api/license/recheck", {})
check("check again after the revoke was lifted: license restored, revoked file gone",
      body.get("ok") and gate.status()["state"] == "valid" and not REV.exists() and (HOME / "license.json").exists(), body)

# ---- a new key replaces a revoked license -----------------------------------------------------------
put(make_license(me)); age_file(100); STEER["/validate"] = (403, REVOKED); reset_attempt(); gate.background_tick(); STEER.pop("/validate")
check("revoked again", gate.status()["state"] == "revoked")
st, body = api("/api/license/activate", {"key": KEY})
check("a different key activates this computer and clears the revoked state",
      body.get("ok") and gate.status()["state"] == "valid" and not REV.exists(), body)

# ---- the update check is a second signal ------------------------------------------------------------
import importlib.util
spec = importlib.util.spec_from_file_location("arti_update_cli_t", CODE / "tools" / "arti-update" / "cli.py")
upd = importlib.util.module_from_spec(spec); spec.loader.exec_module(upd)
STEER["/update"] = (403, REVOKED)
state = upd.check(force=True)
check("the daily update check noticing a revoke locks the dashboard too", state["error"]["code"] == "key_revoked" and gate.status()["state"] == "revoked", state)
STEER.pop("/update")
put(make_license(me)); REV.unlink(missing_ok=True)

# ---- seat full: only support moves a seat held by another computer -----------------------------------
(HOME / "license.json").unlink()
STEER["/activate"] = (409, {"code": "seat_limit", "message": "all 1 seat(s) are in use"})
CALLS.clear()
st, body = api("/api/license/activate", {"key": KEY})
check("seat full: message points to the old computer or support, nothing is freed by the client",
      body["code"] == "seat_limit" and "contact support" in body["error"] and [c[0] for c in CALLS] == ["/activate"], (body, CALLS))
for path in ("/api/license/seats", "/api/license/release"):
    st, body = api(path, {"key": KEY, "machine_hash": "c" * 64})
    check("no client route to list or free another computer's seat: " + path, st in (403, 404) and not any(c[0] in ("/deactivate", "/activations") for c in CALLS), (st, body))
rc, out = run_cli("tools/arti-license/cli.py", "deactivate", "--key", KEY, "--machine", "c" * 64)
check("CLI: 'deactivate --key --machine' no longer exists", rc == 2 and not any(c[0] == "/deactivate" for c in CALLS), (rc, out))
rc, out = run_cli("tools/arti-license/cli.py", "activations", KEY)
check("CLI: 'activations KEY' no longer exists", rc == 2 and not any(c[0] == "/activations" for c in CALLS), (rc, out))
STEER.pop("/activate")
put(make_license(me))
STEER["/deactivate"] = (200, {"ok": True}); CALLS.clear()
st, body = api("/api/license/deactivate", {})
check("deactivating this computer itself is still self-service, authenticated by its own license file",
      body.get("ok") and CALLS[0][0] == "/deactivate" and "license" in CALLS[0][1] and "key" not in CALLS[0][1], CALLS)
STEER.pop("/deactivate")

# ---- the real dashboard ------------------------------------------------------------------------------
from playwright.sync_api import sync_playwright
put(make_license(me)); age_file(1)
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=BROWSER, headless=True)
    pg = br.new_page(viewport={"width": 1280, "height": 800})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(BASE + "/"); time.sleep(1.5)
    check("browser: unlocked license opens the dashboard", not pg.evaluate("document.body.classList.contains('license-locked')"))
    # the server learns about the revoke while the window is open; the next blocked call locks the view
    STEER["/validate"] = (403, REVOKED); age_file(100); reset_attempt(); gate.background_tick()
    pg.click('.nav-item[data-view="files"]'); time.sleep(2.0)
    check("browser: a blocked call mid-session locks the view and opens License",
          pg.evaluate("document.body.classList.contains('license-locked')") and pg.is_visible('.settings-page[data-cat="license"]'))
    pg.reload(); time.sleep(1.5)
    check("browser: badge says Revoked", pg.inner_text("#licBadge") == "Revoked", pg.inner_text("#licBadge"))
    check("browser: hint says the dashboard is locked and tools keep working",
          "locked" in pg.inner_text("#licStateHint") and "tools keep working" in pg.inner_text("#licStateHint"), pg.inner_text("#licStateHint"))
    check("browser: red card on the sidebar", pg.is_visible("#licenseCard") and "revoked" in pg.inner_text("#licenseCard").lower()
          and "bad" in (pg.get_attribute("#licenseCard", "class") or ""))
    check("browser: Check again and the key form are visible, Deactivate is not",
          pg.is_visible("#licRecheckBtn") and pg.is_visible("#licActivate") and not pg.is_visible("#licManage"))
    check("browser: the other Settings pages and nav items are locked",
          pg.evaluate("getComputedStyle(document.querySelector('.settings-nav-item[data-cat=\"apis\"]')).pointerEvents") == "none"
          and pg.evaluate("getComputedStyle(document.querySelector('.nav-item[data-view=\"projects\"]')).pointerEvents") == "none")
    pg.screenshot(path=str(SHOTS / "r1-revoked.png"))
    pg.click("#licRecheckBtn"); time.sleep(1.0)
    check("browser: Check again while revoked shows the message", pg.is_visible("#licErr") and "revoked" in pg.inner_text("#licErr").lower(), pg.inner_text("#licErr"))
    STEER.pop("/validate")
    pg.click("#licRecheckBtn"); time.sleep(1.5)
    check("browser: Check again after the lift unlocks the dashboard", not pg.evaluate("document.body.classList.contains('license-locked')") and pg.inner_text("#licBadge") == "Active", pg.inner_text("#licBadge"))

    # seat full in the page: a plain message, no way to move the seat from here
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="license"]')
    pg.click("#licDeactivateBtn"); time.sleep(1.2)
    STEER["/activate"] = (409, {"code": "seat_limit", "message": "all 1 seat(s) are in use"})
    pg.fill("#licKeyInput", KEY); pg.click("#licActivateBtn"); time.sleep(1.0)
    check("browser: seat full says to use the old computer or contact support",
          "another computer" in pg.inner_text("#licErr") and "contact support" in pg.inner_text("#licErr") and "arti-license" not in pg.inner_text("#licErr"), pg.inner_text("#licErr"))
    check("browser: no button to free another computer's seat", pg.query_selector("#licSeatsBtn") is None and "Free" not in pg.inner_text(".settings-page[data-cat='license']"))
    pg.screenshot(path=str(SHOTS / "r2-seat-full.png"))
    STEER.pop("/activate")
    pg.set_viewport_size({"width": 560, "height": 800})
    check("browser: narrow layout has no horizontal overflow", pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))
    errors = [e for e in errors if "Activate your ARTi license" not in e]  # the blocked call itself rejects once, by design
    check("no page errors", not errors, errors)
    br.close()

print("\n%d checks, %d failed" % (len(results), results.count(False)))
httpd.shutdown(); fake.shutdown()
sys.exit(1 if False in results else 0)
