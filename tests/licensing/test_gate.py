"""End-to-end check of the dashboard license gate + Settings UI, in an isolated data home."""
import base64, datetime, json, os, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import CODE, SHOTS, BROWSER  # noqa: E402

HOME = Path(tempfile.mkdtemp(prefix="arti-gate-home-"))
os.environ["ARTI_HOME"] = str(HOME)
os.environ["ARTI_MACHINE_ID"] = "test-machine-1"
os.environ["ARTI_LICENSE_API"] = "http://127.0.0.1:4198/v1"
sys.path.insert(0, str(CODE / "dashboard" / "server"))
sys.path.insert(0, str(CODE / "tools" / "_shared"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import license as lic

priv = Ed25519PrivateKey.generate()
pub_b64 = base64.b64encode(priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
pk_path = HOME / "pubkeys.test.json"
pk_path.write_text(json.dumps({"license": {"test-1": pub_b64}, "release": {}}))
lic.PUBKEYS_PATH = str(pk_path)


def fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_license(machine_hash, days=365, grace=14, name="Test Buyer"):
    now = lic.utcnow()
    payload = {"key_id": "kid-TEST42", "name": name, "tier": "individual", "seats": 1, "machine_hash": machine_hash,
               "issued": fmt(now), "expires": fmt(now + datetime.timedelta(days=days)), "grace_days": grace,
               "updates_until": fmt(now + datetime.timedelta(days=days))}
    sig = base64.b64encode(priv.sign(lic.canonical_json(payload))).decode()
    return {"payload": payload, "sig": sig, "kid": "test-1"}


calls = []


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        calls.append((self.path, body))
        if self.path == "/v1/activate":
            if body["key"].endswith("0000") and False:
                out, code = {"code": "seat_limit"}, 409
            else:
                out, code = {"license": make_license(body["machine_hash"]), "seats_used": 1}, 200
        elif self.path == "/v1/validate":
            out, code = {"license": make_license(body["machine_hash"])}, 200
        elif self.path == "/v1/deactivate":
            out, code = {"ok": True}, 200
        else:
            out, code = {"code": "not_found"}, 404
        data = json.dumps(out).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)


fake = ThreadingHTTPServer(("127.0.0.1", 4198), Fake)
threading.Thread(target=fake.serve_forever, daemon=True).start()

import server as dash
dash.PORT = 4199
httpd = dash.create_server()
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:4199"

import urllib.request, urllib.error


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


# ---- API level ----
st, body = get("/api/data")
check("locked: /api/data refused with license_required", st == 403 and body.get("code") == "license_required", (st, body))
st, body = get("/api/license/status")
check("locked: license status reachable, state=missing", st == 200 and body["state"] == "missing" and body["locked"], body)
st, body = get("/api/about")
check("locked: /api/about reachable", st == 200 and body.get("version"), body)

from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=BROWSER, headless=True)
    pg = br.new_page(viewport={"width": 1280, "height": 800})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE + "/")
    pg.wait_for_selector("#licBadge")
    time.sleep(0.8)
    check("locked: body has license-locked", pg.evaluate("document.body.classList.contains('license-locked')"))
    check("locked: Settings panel visible", pg.evaluate("!document.getElementById('settingsPanel').hidden"))
    check("locked: Projects panel hidden", pg.evaluate("document.getElementById('projectsPanel').hidden"))
    check("locked: badge says Not activated", pg.inner_text("#licBadge") == "Not activated", pg.inner_text("#licBadge"))
    check("locked: activate form visible, manage hidden", pg.is_visible("#licActivate") and not pg.is_visible("#licManage"))
    check("locked: sidebar card visible", pg.is_visible("#licenseCard"))
    pg.screenshot(path=str(SHOTS / "1-locked.png"))
    # try to leave via keyboard shortcut (Ctrl+1)
    pg.keyboard.press("Control+1")
    time.sleep(0.3)
    check("locked: Ctrl+1 does not leave Settings", pg.evaluate("document.getElementById('projectsPanel').hidden"))
    # bad checksum
    good15 = "ABCDEFGHJKMNPQR"
    wrong = "0" if lic.checksum_char(good15) != "0" else "1"
    pg.fill("#licKeyInput", lic.format_key(good15 + wrong))
    pg.click("#licActivateBtn"); time.sleep(0.6)
    check("bad key: error shown", pg.is_visible("#licErr") and "typo" in pg.inner_text("#licErr").lower(), pg.inner_text("#licErr"))
    # good key
    body15 = "ABCDEFGHJKMNPQR"
    key = lic.format_key(body15 + lic.checksum_char(body15))
    pg.fill("#licKeyInput", key)
    pg.click("#licActivateBtn"); time.sleep(1.5)
    check("activate: badge Active", pg.inner_text("#licBadge") == "Active", pg.inner_text("#licBadge"))
    check("activate: unlocked", not pg.evaluate("document.body.classList.contains('license-locked')"))
    check("activate: name shown", "Test Buyer" in pg.inner_text("#licName"))
    check("activate: license.json written", (HOME / "license.json").exists())
    check("activate: server got machine_hash, not raw id", calls and "test-machine-1" not in json.dumps(calls[-1]) and len(calls[-1][1]["machine_hash"]) == 64)
    check("activate: manage buttons visible", pg.is_visible("#licManage"))
    pg.screenshot(path=str(SHOTS / "2-active.png"))
    st, body = get("/api/data")
    check("unlocked: /api/data works", st == 200 and "projects" in body, (st, str(body)[:80]))
    pg.click('.nav-item[data-view="projects"]'); time.sleep(0.4)
    check("unlocked: can open Projects", pg.evaluate("!document.getElementById('projectsPanel').hidden"))

    # settings categories
    pg.keyboard.press("Control+,"); time.sleep(0.3)
    pg.click('.settings-nav-item[data-cat="apis"]'); time.sleep(0.5)
    check("apis: page visible", pg.is_visible('.settings-page[data-cat="apis"]'))
    pg.fill("#keyOpenalex", "oa-secret-1234567890"); pg.fill("#keyEmail", "me@example.com")
    pg.click("#saveKeysBtn"); time.sleep(0.8)
    saved = json.loads((HOME / "mcp-keys.json").read_text())
    check("apis: keys written to mcp-keys.json", saved.get("OPENALEX_API_KEY") == "oa-secret-1234567890" and saved.get("ARTI_REF_CONTACT_EMAIL") == "me@example.com", saved)
    st, view = get("/api/settings/keys")
    check("apis: API never returns the full secret", "oa-secret-1234567890" not in json.dumps(view) and view["OPENALEX_API_KEY"]["set"], view)
    check("apis: placeholder shows hint", "7890" in (pg.get_attribute("#keyOpenalex", "placeholder") or ""), pg.get_attribute("#keyOpenalex", "placeholder"))
    pg.screenshot(path=str(SHOTS / "3-apis.png"))
    pg.click('[data-clear="OPENALEX_API_KEY"]'); time.sleep(0.6)
    check("apis: Remove clears the key", "OPENALEX_API_KEY" not in json.loads((HOME / "mcp-keys.json").read_text()))

    pg.click('.settings-nav-item[data-cat="system"]'); time.sleep(1.2)
    check("system: rows rendered", pg.locator(".system-row").count() >= 6, pg.locator(".system-row").count())
    pg.screenshot(path=str(SHOTS / "4-system.png"))
    pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.5)
    check("about: version shown", pg.inner_text("#aboutVersion").startswith("v"), pg.inner_text("#aboutVersion"))
    pg.screenshot(path=str(SHOTS / "5-about.png"))
    pg.click('.settings-nav-item[data-cat="fineai"]'); time.sleep(0.8)
    check("fineai: toggle + models section present", pg.is_visible("#fineAiEnabledToggle") and pg.is_visible("#chatModelsSection"))
    pg.screenshot(path=str(SHOTS / "6-fineai.png"))

    # narrow layout
    pg.set_viewport_size({"width": 560, "height": 800})
    pg.click('.settings-nav-item[data-cat="license"]'); time.sleep(0.4)
    check("narrow: no horizontal overflow", pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"),
          pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]"))
    pg.screenshot(path=str(SHOTS / "7-narrow.png"))
    pg.set_viewport_size({"width": 1280, "height": 800})

    # expiring soon -> card; expired beyond grace -> open + banner
    (HOME / "license.json").write_text(json.dumps(make_license(lic.machine_hash(), days=10)))
    pg.reload(); time.sleep(1.2)
    check("expiring: card shows days", pg.is_visible("#licenseCard") and "10 day" in pg.inner_text("#licenseCard"), pg.inner_text("#licenseCard"))
    (HOME / "license.json").write_text(json.dumps(make_license(lic.machine_hash(), days=-30, grace=14)))
    pg.reload(); time.sleep(1.2)
    check("expired: still unlocked", not pg.evaluate("document.body.classList.contains('license-locked')"))
    check("expired: card says updates off", "Updates are off" in pg.inner_text("#licenseCard"), pg.inner_text("#licenseCard"))
    st, body = get("/api/data")
    check("expired: /api/data still works", st == 200)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="license"]'); time.sleep(0.5)
    check("expired: badge Expired + activate form for renewal", pg.inner_text("#licBadge") == "Expired" and pg.is_visible("#licActivate"))
    pg.screenshot(path=str(SHOTS / "8-expired.png"))

    # wrong machine -> locked
    (HOME / "license.json").write_text(json.dumps(make_license("0" * 64)))
    pg.reload(); time.sleep(1.2)
    check("wrong machine: locked", pg.evaluate("document.body.classList.contains('license-locked')"))
    check("wrong machine: reason shown", "another computer" in pg.inner_text("#licStateHint"), pg.inner_text("#licStateHint"))
    # tampered
    tampered = make_license(lic.machine_hash()); tampered["payload"]["expires"] = "2099-01-01T00:00:00Z"
    (HOME / "license.json").write_text(json.dumps(tampered))
    st, body = get("/api/license/status")
    check("tampered: invalid + locked", body["state"] == "invalid" and body["locked"], body)
    # corrupt file
    (HOME / "license.json").write_text("not json")
    st, body = get("/api/license/status")
    check("corrupt: invalid + locked", body["state"] == "invalid" and body["locked"], body)

    # restore + deactivate
    (HOME / "license.json").write_text(json.dumps(make_license(lic.machine_hash())))
    pg.reload(); time.sleep(1.2)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="license"]')
    pg.once("dialog", lambda d: d.accept())
    pg.click("#licDeactivateBtn"); time.sleep(1.2)
    check("deactivate: license.json removed and locked", not (HOME / "license.json").exists() and pg.evaluate("document.body.classList.contains('license-locked')"))
    check("no page errors", not errors, errors)
    br.close()

fails = [n for n, ok in results if not ok]
print("\n%d checks, %d failed" % (len(results), len(fails)))
httpd.shutdown(); fake.shutdown()
sys.exit(1 if fails else 0)
