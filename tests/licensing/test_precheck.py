"""installer/precheck.ps1: the key is checked before the installer writes anything.

Runs the real PowerShell script (what the NSIS installer unpacks and calls) against a fake Worker on localhost:
typo, unknown key, revoked, expired, seats full elsewhere, own seat already bound, healthy key, server down.
Read-only against the fake: /activations must be the only route used. Windows only (the script reads MachineGuid).
"""
import datetime, json, os, subprocess, sys, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import CODE  # noqa: E402

sys.path.insert(0, str(CODE / "tools" / "_shared"))
import license as lic  # noqa: E402

if sys.platform != "win32":
    print("SKIP precheck (Windows only)")
    sys.exit(0)

SCRIPT = CODE / "installer" / "precheck.ps1"
MINE = lic.machine_hash()   # same MachineGuid-based hash the script computes (no ARTI_MACHINE_ID override here)
results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


def make_key(seed):
    body = (seed * 4)[:15]
    return lic.format_key(body + lic.checksum_char(body))


def iso(days):
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


KEYS = {
    make_key("0123456789ABCDE"): ("ok", {"seats": 1, "status": "active", "expires": iso(300), "activations": []}),
    make_key("1111222233334444"): ("revoked", {"seats": 1, "status": "revoked", "expires": iso(300), "activations": []}),
    make_key("2222333344445555"): ("expired", {"seats": 1, "status": "active", "expires": iso(-5), "activations": []}),
    make_key("3333444455556666"): ("full", {"seats": 1, "status": "active", "expires": iso(300), "activations": [{"machine_hash": "f" * 64, "deactivated": 0}]}),
    make_key("4444555566667777"): ("mine", {"seats": 1, "status": "active", "expires": iso(300), "activations": [{"machine_hash": MINE, "deactivated": 0}]}),
    make_key("5555666677778888"): ("freed", {"seats": 1, "status": "active", "expires": iso(300), "activations": [{"machine_hash": "f" * 64, "deactivated": 1}]}),
}
CALLS = []


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        CALLS.append((self.path, body))
        if self.path != "/v1/activations":
            out, status = {"code": "server_error"}, 500
        elif body.get("key") in KEYS:
            out, status = dict(KEYS[body["key"]][1], key_id="kid-X"), 200
        else:
            out, status = {"code": "not_found", "message": "no such license key"}, 404
        data = json.dumps(out).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)


srv = ThreadingHTTPServer(("127.0.0.1", 4297), Fake)
threading.Thread(target=srv.serve_forever, daemon=True).start()


def run(key, api="http://127.0.0.1:4297/v1"):
    env = dict(os.environ, ARTI_PRECHECK_KEY=key)
    env.pop("ARTI_LICENSE_API", None)
    r = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-Api", api],
                       capture_output=True, text=True, env=env, timeout=60)
    return r.returncode, r.stdout.strip()


good, revoked, expired, full, mine, freed = list(KEYS)
n = len(CALLS)
rc, out = run(good[:-1] + ("0" if good[-1] != "0" else "1"))
check("a typo is refused offline, before any request", rc == 2 and "typo" in out and len(CALLS) == n, (rc, out))
rc, out = run("ARTI-ABCD-EFGH")
check("a key of the wrong length is refused offline", rc == 2 and len(CALLS) == n, (rc, out))
rc, out = run("")
check("an empty key is refused", rc == 2, (rc, out))
rc, out = run('"; Remove-Item C:\\nonexistent -Recurse; "')
check("a hostile string is just a bad key (no command injection)", rc == 2, (rc, out))
rc, out = run(good)
check("a healthy key passes", rc == 0 and "accepted" in out, (rc, out))
rc, out = run(good.lower().replace("-", " "))
check("lower case and spaces are accepted like the client does", rc == 0, (rc, out))
unknown = make_key("9999888877776666")
rc, out = run(unknown)
check("a well-formed key the server does not know is refused", rc == 3 and "No such" in out, (rc, out))
rc, out = run(revoked)
check("a revoked key is refused", rc == 3 and "revoked" in out, (rc, out))
rc, out = run(expired)
check("an expired key is refused", rc == 3 and "expired" in out, (rc, out))
rc, out = run(full)
check("a key whose only seat is on another computer is refused", rc == 4 and "another computer" in out, (rc, out))
rc, out = run(mine)
check("a key already bound to THIS computer passes (reinstall)", rc == 0, (rc, out))
rc, out = run(freed)
check("a seat that was deactivated counts as free", rc == 0, (rc, out))
rc, out = run(good, api="http://127.0.0.1:4296/v1")
check("server unreachable: refused with a clear message", rc == 5 and "Cannot reach" in out, (rc, out))
check("only the read-only /activations route was used", {c[0] for c in CALLS} == {"/v1/activations"}, {c[0] for c in CALLS})

# the NSIS script must call the check before anything is written
nsi = (CODE / "installer" / "arti-installer.nsi").read_text(encoding="utf-8")
leave = nsi[nsi.index("Function KeyPageLeave"):nsi.index("Section \"Install\"")]
check("KeyPageLeave calls PrecheckKey", "Call PrecheckKey" in leave)
oninit = nsi[nsi.index("Function .onInit"):nsi.index("Function KeyPageShow")]
check(".onInit checks a /KEY= key before the install starts", "Call PrecheckKey" in oninit and "Abort" in oninit)
check("the first File/RMDir of the install section comes after both checks", nsi.index("Call PrecheckKey") < nsi.index("Section \"Install\""))
check("precheck.ps1 is not part of the shipped payload list", "precheck.ps1" not in nsi[nsi.index("Section \"Install\""):])

print("\n%d checks, %d failed" % (len(results), results.count(False)))
srv.shutdown()
sys.exit(1 if False in results else 0)
