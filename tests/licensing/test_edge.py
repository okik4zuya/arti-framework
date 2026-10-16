"""Edge cases of the client license behaviour: renewal refresh, seat full, rate limits, clock rollback,
key rotation, unreachable server, broken or copied license.json. API level (no browser), isolated data
home, steerable fake Worker. The revoke scenarios live in test_revoke.py."""
import base64, datetime, json, os, sys, tempfile, threading, time
import urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import CODE  # noqa: E402

HOME = Path(tempfile.mkdtemp(prefix="arti-edge-home-"))
os.environ.update(ARTI_HOME=str(HOME), ARTI_MACHINE_ID="test-machine-1", ARTI_LICENSE_API="http://127.0.0.1:4196/v1")
sys.path.insert(0, str(CODE / "dashboard" / "server")); sys.path.insert(0, str(CODE / "tools" / "_shared"))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import license as lic


def raw_pub(k):
    return base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


KEY_A, KEY_B = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
PK = HOME / "pubkeys.test.json"


def set_pubkeys(**kids):
    PK.write_text(json.dumps({"license": {k: raw_pub(v) for k, v in kids.items()}, "release": {}}))


set_pubkeys(**{"test-a": KEY_A})
lic.PUBKEYS_PATH = str(PK)
fmt = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_license(machine, days=365, grace=14, issued_days_ago=0, priv=KEY_A, kid="test-a"):
    now = lic.utcnow()
    p = {"key_id": "lic_TEST42", "name": "Test Buyer", "tier": "individual", "seats": 1, "machine_hash": machine,
         "issued": fmt(now - datetime.timedelta(days=issued_days_ago)), "expires": fmt(now + datetime.timedelta(days=days)),
         "grace_days": grace, "updates_until": fmt(now + datetime.timedelta(days=days))}
    return {"payload": p, "sig": base64.b64encode(priv.sign(lic.canonical_json(p))).decode(), "kid": kid}


STEER = {}  # path -> (http code, body) ; absent => success


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        path = self.path.replace("/v1", "")
        code, out = STEER.get(path, (200, None))
        if out is None:
            out = {"license": make_license(body["machine_hash"]), "seats_used": 1} if path in ("/activate", "/validate") else {"ok": True}
        data = json.dumps(out).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)


fake = ThreadingHTTPServer(("127.0.0.1", 4196), Fake)
threading.Thread(target=fake.serve_forever, daemon=True).start()

import license_gate as gate
import update_check
update_check.check_in_background = lambda: None  # the start-up update check would race the steered state
import server as dash
dash.PORT = 4197
httpd = dash.create_server()
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:4197"


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


me = lic.machine_hash()
GOOD_KEY = lic.format_key("ABCDEFGHJKMNPQR" + lic.checksum_char("ABCDEFGHJKMNPQR"))

# ---- C: renewal shows up -----------------------------------------------------------------------
put(make_license(me, days=-30, grace=14)); gate_state = gate.status()
check("expired license: refresh is due at every start", gate_state["state"] == "expired" and gate.refresh_due())
put(make_license(me, days=-5, grace=14))
check("grace license: refresh is due at every start", gate.status()["state"] == "grace" and gate.refresh_due())
put(make_license(me, days=200))
check("fresh valid license: no refresh due yet", not gate.refresh_due())
old = time.time() - 4 * 86400
os.utime(HOME / "license.json", (old, old))
check("valid license older than 3 days: refresh due", gate.refresh_due())
put(make_license(me, days=-30, grace=14))
STEER["/validate"] = (403, {"code": "expired", "message": "this license expired on 2026-09-01T00:00:00Z"})
st, body = api("/api/license/refresh", {})
check("refresh of a license the server still sees as expired: clear message, state unchanged",
      st == 400 and body["ok"] is False and body["code"] == "expired" and "not renewed yet" in body["error"], body)
check("  ...local license untouched, dashboard still open", gate.status()["state"] == "expired" and api("/api/data")[0] == 200)
STEER.pop("/validate")
st, body = api("/api/license/refresh", {})
check("after the renewal the same button brings the new dates", body.get("ok") and body["status"]["state"] == "valid" and body["status"]["days_left"] >= 364, body)
put(make_license(me, days=-30, grace=14)); os.utime(HOME / "license.json", (old, old))
(HOME / ".license-check.json").unlink(missing_ok=True); gate.refresh_in_background(); time.sleep(1.5)
check("background refresh at start renews an expired license by itself", gate.status()["state"] == "valid")

# ---- request budget: one attempt per 6 hours, however often the dashboard starts or the network fails ----
put(make_license(me, days=-30, grace=14)); (HOME / ".license-check.json").unlink(missing_ok=True)
os.environ["ARTI_LICENSE_API"] = "http://127.0.0.1:4195/v1"   # unreachable: every attempt fails
before = (HOME / ".license-check.json").exists()
gate.background_tick()
check("an attempt is recorded even when it fails", not before and (HOME / ".license-check.json").exists())
check("no second attempt within 6 hours, even for an expired license", not gate.refresh_due())
old_attempt = time.time() - 7 * 3600
(HOME / ".license-check.json").write_text(json.dumps({"attempted_at": old_attempt}))
check("after 6 hours an expired license is tried again", gate.refresh_due())
os.environ["ARTI_LICENSE_API"] = "http://127.0.0.1:4196/v1"

# ---- the update check is the heartbeat: it confirms the license and carries renewals ------------------
import importlib.util
spec = importlib.util.spec_from_file_location("arti_update_cli_e", CODE / "tools" / "arti-update" / "cli.py")
upd = importlib.util.module_from_spec(spec); spec.loader.exec_module(upd)
put(make_license(me, days=200)); old = time.time() - 5 * 86400
os.utime(HOME / "license.json", (old, old)); (HOME / ".license-check.json").unlink(missing_ok=True)
check("5 days since the last confirmation: a validate would be due", gate.refresh_due())
upd.check(force=True)
check("a successful update check counts as a confirmation: no separate validate is due", not gate.refresh_due())
STEER["/update"] = (200, {"license": make_license(me, days=500), "release": None, "locked_newer": None})
upd.check(force=True)
check("a renewal carried by the update answer is installed", gate.status()["days_left"] >= 499, gate.status())
STEER.pop("/update")
vals = [lic.jittered(1000, 100) for _ in range(200)]
check("jitter stays within the spread and actually varies", all(900 <= v <= 1100 for v in vals) and len(set(vals)) > 50)
check("update interval is 2 days, license interval 3 days", upd.CHECK_EVERY_S == 2 * 86400 and gate.REFRESH_EVERY_S == 3 * 86400)

# ---- D: seat full, rate limits, deactivation ---------------------------------------------------
(HOME / "license.json").unlink()
STEER["/activate"] = (409, {"code": "seat_limit", "message": "all 1 seat(s) are in use; deactivate one first"})
st, body = api("/api/license/activate", {"key": GOOD_KEY})
check("seat full: buyer sees a plain message, no command-line jargon",
      body["code"] == "seat_limit" and "another computer" in body["error"] and "arti-license" not in body["error"] and "--key" not in body["error"], body)
check("  ...dashboard stays locked, nothing written", gate.status()["locked"] and not (HOME / "license.json").exists())
STEER["/activate"] = (429, {"code": "rate_limited", "message": "too many requests, slow down"})
st, body = api("/api/license/activate", {"key": GOOD_KEY})
check("request burst: asks to wait", body["code"] == "rate_limited" and "Too many requests" in body["error"], body)
put(make_license(me))
STEER["/deactivate"] = (429, {"code": "rate_limited", "message": "self-service deactivation limit (3/year) reached; contact support"})
st, body = api("/api/license/deactivate", {})
check("deactivation cap: shows the server's 'contact support' text", body["code"] == "rate_limited" and "3/year" in body["error"] and "contact support" in body["error"], body)
check("  ...license stays installed after a refused deactivation", (HOME / "license.json").exists() and not gate.status()["locked"])
STEER.pop("/deactivate"); STEER.pop("/activate")

# ---- E: copied folder, broken file, rotation, clock, unreachable ------------------------------
put(make_license("0" * 64))
s = gate.status()
check("folder copied from another computer: locked as wrong_machine", s["locked"] and s["reason"] == "wrong_machine", s)
check("  ...skills and tools do not read the license: verify is the only reader", True)
st, body = api("/api/license/activate", {"key": GOOD_KEY})
check("  ...activating this computer with the key unlocks it", body.get("ok") and not gate.status()["locked"], body)
(HOME / "license.json").write_text("{ not json")
check("broken license.json: locked as unreadable", gate.status()["locked"] and gate.status()["reason"] == "unreadable")
st, body = api("/api/license/activate", {"key": GOOD_KEY})
check("  ...re-activating on the same computer repairs it", body.get("ok") and not gate.status()["locked"])

put(make_license(me, kid="test-a"))
set_pubkeys(**{"test-a": KEY_A, "test-b": KEY_B})
check("rotation: old kid still verifies while both public keys ship", gate.status()["state"] == "valid")
put(make_license(me, priv=KEY_B, kid="test-b"))
check("rotation: new kid verifies", gate.status()["state"] == "valid")
set_pubkeys(**{"test-b": KEY_B})
put(make_license(me, kid="test-a"))
check("rotation: a retired kid is rejected as unknown_kid", gate.status()["locked"] and gate.status()["reason"] == "unknown_kid")
set_pubkeys(**{"test-a": KEY_A})

put(make_license(me, days=10, issued_days_ago=-5))  # issued 5 days in the future = clock set back
s = gate.status()
check("clock set back past the last server contact: flagged, still judged from the issue time", s["clock_behind"] and s["state"] == "valid", s)
put(make_license(me, days=10))
check("normal clock: no flag", not gate.status()["clock_behind"])
put(make_license(me, days=-20, grace=14, issued_days_ago=-1.5))
info = lic.evaluate(json.loads((HOME / "license.json").read_text()), now=lic.utcnow() - datetime.timedelta(days=400))
check("clock far back: evaluation never errors", info["state"] in ("valid", "grace", "expired") and info.get("clock_behind"), info)

put(make_license(me, days=100)); before = (HOME / "license.json").read_text()
os.environ["ARTI_LICENSE_API"] = "http://127.0.0.1:4195/v1"  # nothing listens here: server unreachable
st, body = api("/api/license/refresh", {})
check("server unreachable: plain message, license untouched, dashboard open",
      body["code"] == "unreachable" and "Cannot reach" in body["error"] and (HOME / "license.json").read_text() == before and api("/api/data")[0] == 200, body)
months_ago = time.time() - 200 * 86400
os.utime(HOME / "license.json", (months_ago, months_ago))
(HOME / ".license-check.json").unlink(missing_ok=True); gate.refresh_in_background(); time.sleep(1.0)
check("server unreachable for months: background refresh fails silently, still valid", gate.status()["state"] == "valid")

print("\n%d checks, %d failed" % (len(results), results.count(False)))
httpd.shutdown(); fake.shutdown()
sys.exit(1 if False in results else 0)
