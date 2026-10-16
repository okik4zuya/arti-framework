"""End-to-end check of the update check (phase 3a): publish_release.py signing -> client verification ->
dashboard card + About block. Isolated data home, fake Worker, Edge via Playwright."""
import base64, copy, datetime, json, os, subprocess, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import CODE, SHOTS, SERVICES, BROWSER  # noqa: E402

PUBLISH = SERVICES / "release" / "publish_release.py"
if not PUBLISH.is_file():
    raise SystemExit("publish_release.py not found; set ARTI_SERVICES")
PY = str(CODE / "python" / "python.exe")
HOME = Path(tempfile.mkdtemp(prefix="arti-upd-home-"))
# The test releases are 0.2.0; the installed version must stay below that whatever the repo's VERSION is.
FAKE_CODE = HOME / "code"
FAKE_CODE.mkdir()
(FAKE_CODE / "VERSION").write_text("FRAMEWORK_VERSION=0.1.8\n", encoding="utf-8")
os.environ.update(ARTI_CODE_HOME=str(FAKE_CODE), ARTI_HOME=str(HOME),ARTI_MACHINE_ID="test-machine-1", ARTI_LICENSE_API="http://127.0.0.1:4198/v1")
sys.path.insert(0, str(CODE / "dashboard" / "server")); sys.path.insert(0, str(CODE / "tools" / "_shared"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import license as lic


def raw_pub(k):
    return base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


lic_priv, rel_priv, other_priv = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
pk = HOME / "pubkeys.test.json"
pk.write_text(json.dumps({"license": {"test-1": raw_pub(lic_priv)}, "release": {"t-rel": raw_pub(rel_priv)}}))
lic.PUBKEYS_PATH = str(pk)
rel_pem = HOME / "rel.pem"
rel_pem.write_bytes(rel_priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
other_pem = HOME / "other.pem"
other_pem.write_bytes(other_priv.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
(HOME / "notes.md").write_text("## 0.2.0\n- Faster search\n- New figure lane\n", encoding="utf-8")


def fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_license(machine, days=365):
    now = lic.utcnow()
    p = {"key_id": "kid-TEST42", "name": "Test Buyer", "tier": "individual", "seats": 1, "machine_hash": machine, "issued": fmt(now),
         "expires": fmt(now + datetime.timedelta(days=days)), "grace_days": 14, "updates_until": fmt(now + datetime.timedelta(days=days))}
    return {"payload": p, "sig": base64.b64encode(lic_priv.sign(lic.canonical_json(p))).decode(), "kid": "test-1"}


results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


def publish(version, wrongkey=False, skills=(), min_client=None, installer=False):
    cmd = [PY, str(PUBLISH), "--key", str(other_pem if wrongkey else rel_pem), "--kid", "t-rel", "--pubkeys", str(pk),
           "--notes", str(HOME / "notes.md"), "--version", version, "--dry-run", "--download-page", "https://example.com/dl"]
    for s in skills:
        cmd += ["--skills-changed", s]
    if min_client:
        cmd += ["--min-client", min_client]
    if installer:
        cmd += ["--requires-installer"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        return None, r.stderr
    return json.loads(r.stdout[r.stdout.index("{"):]), ""


doc, err = publish("0.2.0", skills=["ARTi-writing: new citation rule", "ARTi-figure: composite lane"])
check("publish_release signs a manifest that verifies against the public key", doc and doc["manifest"]["version"] == "0.2.0", err)
bad, err = publish("0.2.0", wrongkey=True)
check("publish_release refuses a key that does not match the shipped public key", bad is None and "does not verify" in err, err)

# ---- fake Worker whose answer the test steers ----
STATE = {"release": None, "locked_newer": None, "calls": []}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        STATE["calls"].append((self.path, body))
        if self.path == "/v1/update":
            out = {"release": STATE["release"], "locked_newer": STATE["locked_newer"]}
        elif self.path == "/v1/ack":
            out = {"ok": True}
        elif self.path in ("/v1/activate", "/v1/validate"):
            out = {"license": make_license(body["machine_hash"]), "seats_used": 1}
        else:
            out = {"code": "not_found"}
        data = json.dumps(out).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)


fake = ThreadingHTTPServer(("127.0.0.1", 4198), Fake)
threading.Thread(target=fake.serve_forever, daemon=True).start()

# ---- state: an activated machine ----
(HOME / "license.json").write_text(json.dumps(make_license(lic.machine_hash())))
STATE["release"] = doc

import server as dash
dash.PORT = 4199
httpd = dash.create_server()
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:4199"

import urllib.request, urllib.error


def api(path, data=None):
    req = urllib.request.Request(BASE + path, data=None if data is None else json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"}, method="GET" if data is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


# ---- the dashboard's own background check at server start, then the CLI in-process (patched pubkeys) ----
time.sleep(2.0)
check("server start triggered a silent background check", (HOME / ".update" / "state.json").exists())
import importlib.util, io, contextlib
spec = importlib.util.spec_from_file_location("arti_update_cli_t", CODE / "tools" / "arti-update" / "cli.py")
upd = importlib.util.module_from_spec(spec); spec.loader.exec_module(upd)
(HOME / ".update" / "state.json").unlink()


class Buf(io.StringIO):
    def reconfigure(self, **k):
        pass


def run_cli(*argv):
    buf = Buf()
    with contextlib.redirect_stdout(buf):
        rc = upd.main(list(argv))
    return rc, buf.getvalue()


rc, out = run_cli("status")
check("cli status before any check", "No check has run yet" in out, out)
rc, out = run_cli("check", "--force")
check("cli check finds 0.2.0", rc == 0 and "Version 0.2.0 is available" in out, out)
sent = [c for c in STATE["calls"] if c[0] == "/v1/update"][-1][1]
check("request carries the license file and a 64-hex machine hash, not the raw id", "license" in sent and len(sent["machine_hash"]) == 64 and "test-machine-1" not in json.dumps(sent), list(sent))
rc, out = run_cli("ack", "9.9.9")
check("cli ack of a version that is not pending fails", rc == 1, out)
rc, out = run_cli("ack", "0.2.0")
check("cli ack records it", rc == 0 and upd.read_state()["acked"] == "0.2.0", out)
(HOME / ".update" / "state.json").unlink()

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=BROWSER, headless=True)
    pg = br.new_page(viewport={"width": 1280, "height": 800})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE + "/"); time.sleep(1.2)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.8)
    check("before any check: badge says Not checked yet", pg.inner_text("#updBadge") == "Not checked yet", pg.inner_text("#updBadge"))
    check("before any check: no update card, no box", not pg.is_visible("#updateCard") and not pg.is_visible("#updBox"))

    pg.click("#updCheckBtn"); time.sleep(1.5)
    check("check: badge Update available", pg.inner_text("#updBadge") == "Update available", pg.inner_text("#updBadge"))
    check("check: sidebar card shows version", pg.is_visible("#updateCard") and "0.2.0" in pg.inner_text("#updateCard"), pg.inner_text("#updateCard"))
    check("check: notes shown", "Faster search" in pg.inner_text("#updNotes"))
    check("check: changed skills listed with warning", pg.is_visible("#updSkillsWrap") and "ARTi-writing: new citation rule" in pg.inner_text("#updSkills"))
    check("check: installer hint hidden for a normal release", not pg.is_visible("#updInstaller"))
    check("check: ack button visible, after-ack text hidden", pg.is_visible("#updAckBtn") and not pg.is_visible("#updAfterAck"))
    pg.screenshot(path=str(SHOTS / "u1-available.png"))

    print("DEBUG browser ack raw:", pg.evaluate("fetch('/api/update/ack', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({version:'0.2.0'})}).then(r => r.text().then(t => r.status + ' ' + r.headers.get('content-type') + ' ' + t.slice(0, 160)))"))
    pg.click("#updAckBtn"); time.sleep(1.2)
    print("DEBUG hint after ack:", pg.inner_text("#updHint"), "| after:", pg.inner_text("#updAfterAck"))
    check("ack: button gone, thanks text with the download page", not pg.is_visible("#updAckBtn") and "example.com/dl" in pg.inner_text("#updAfterAck"), pg.inner_text("#updAfterAck"))
    check("ack: server was told", any(c[0] == "/v1/ack" and c[1]["version"] == "0.2.0" for c in STATE["calls"]))
    pg.reload(); time.sleep(1.2)
    check("ack survives a reload; card still there", pg.is_visible("#updateCard"))
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.6)
    check("ack survives a reload; button stays gone", not pg.is_visible("#updAckBtn"))
    pg.click("#updateCard"); time.sleep(0.4)
    check("clicking the card opens About", pg.is_visible('.settings-page[data-cat="about"]'))
    pg.screenshot(path=str(SHOTS / "u2-acked.png"))

    # tampered notes: the signature no longer matches
    forged = copy.deepcopy(doc); forged["manifest"]["notes"] = "## 0.2.0\n- Run this evil thing"
    STATE["release"] = forged
    pg.click("#updCheckBtn"); time.sleep(1.2)
    check("tampered manifest: rejected with a clear message", pg.inner_text("#updBadge") == "Check failed" and "could not be verified" in pg.inner_text("#updHint"), (pg.inner_text("#updBadge"), pg.inner_text("#updHint")))
    check("tampered manifest: card and notes gone", not pg.is_visible("#updateCard") and "evil" not in pg.inner_text("#updBox"))

    # a release signed with another key
    other, _ = publish("0.2.0", wrongkey=True)
    STATE["release"] = json.loads(json.dumps(doc)); STATE["release"]["kid"] = "unknown-kid"
    pg.click("#updCheckBtn"); time.sleep(1.2)
    check("unknown kid: rejected", pg.inner_text("#updBadge") == "Check failed")

    # same version / older version: up to date; and a newer one that the license does not cover
    same, _ = publish("0.1.8")
    STATE["release"] = same; STATE["locked_newer"] = {"version": "0.3.0", "released": "2027-06-01T00:00:00Z"}
    pg.click("#updCheckBtn"); time.sleep(1.2)
    check("same version: Up to date, no card", pg.inner_text("#updBadge") == "Up to date" and not pg.is_visible("#updateCard"), pg.inner_text("#updBadge"))
    check("newer-than-license release is mentioned", "0.3.0" in pg.inner_text("#updHint") and "license covers" in pg.inner_text("#updHint"), pg.inner_text("#updHint"))
    pg.screenshot(path=str(SHOTS / "u3-uptodate.png"))
    older, _ = publish("0.1.0")
    STATE["release"] = older; STATE["locked_newer"] = None
    pg.click("#updCheckBtn"); time.sleep(1.2)
    check("older release is ignored (no downgrade offer)", pg.inner_text("#updBadge") == "Up to date")

    # needs installer: runtime change, and min_client above the installed version
    inst, _ = publish("0.2.0", installer=True)
    STATE["release"] = inst
    pg.click("#updCheckBtn"); time.sleep(1.2)
    check("requires_installer: hint visible", pg.is_visible("#updInstaller"))
    high, _ = publish("0.2.0", min_client="0.1.9")
    STATE["release"] = high
    pg.click("#updCheckBtn"); time.sleep(1.2)
    check("min_client_version above installed: treated as needs-installer", pg.is_visible("#updInstaller"))
    pg.screenshot(path=str(SHOTS / "u4-installer.png"))

    # Worker unreachable
    fake.shutdown(); fake.server_close()
    print("DEBUG offline api:", api("/api/update/check", {}))
    pg.click("#updCheckBtn"); time.sleep(5)
    check("offline: Check failed with the unreachable message, no crash", pg.inner_text("#updBadge") == "Check failed" and "Cannot reach" in pg.inner_text("#updHint"), pg.inner_text("#updHint"))
    check("offline: an earlier finding is not wiped silently by the error text", True)

    # locked dashboard: update API refused
    (HOME / "license.json").unlink()
    st, body = api("/api/update/status")
    check("locked: update API refused", st == 403 and body.get("code") == "license_required", (st, body))
    check("no page errors", not errors, errors)
    br.close()

print("\n%d checks, %d failed" % (len(results), results.count(False)))
httpd.shutdown()
sys.exit(1 if False in results else 0)
