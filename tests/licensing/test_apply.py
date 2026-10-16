"""End-to-end check of "Update now" (phase 3b): build_bundle.py -> publish_release.py --bundle -> fake Worker ->
download -> updater.py in its own process -> health check -> rollback, plus the dashboard UI.

Nothing here touches the real ~/.arti: the installed code is a throw-away tree (ARTI_CODE_HOME), the data home is
a temp folder (ARTI_HOME), the Worker is fake, skill links go to a temp folder, and "the dashboard" that the
updater stops and starts again is a small stub server. Edge via Playwright for the UI part.
"""
import base64, datetime, hashlib, io, json, os, re, shutil, sqlite3, subprocess, sys, tempfile, threading, time, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import CODE as REAL, SHOTS, SERVICES, BROWSER  # noqa: E402

PY = str(REAL / "python" / "python.exe") if sys.platform == "win32" else str(REAL / "python" / "bin" / "python3")
BUILD = SERVICES / "release" / "build_bundle.py"
PUBLISH = SERVICES / "release" / "publish_release.py"
if not BUILD.is_file() or not PUBLISH.is_file():
    raise SystemExit("build_bundle.py / publish_release.py not found; set ARTI_SERVICES")

ROOT = Path(tempfile.mkdtemp(prefix="arti-apply-"))
HOME, CODE, CLAUDE_SKILLS = ROOT / "home", ROOT / "code", ROOT / "claude-skills"
for d in (HOME, CLAUDE_SKILLS):
    d.mkdir()
REAL_LINKS = Path.home() / ".claude" / "skills"
LINKS_BEFORE = sorted(os.listdir(REAL_LINKS)) if REAL_LINKS.is_dir() else []
os.environ.update(ARTI_HOME=str(HOME), ARTI_CODE_HOME=str(CODE), ARTI_MACHINE_ID="test-machine-1",
                  ARTI_LICENSE_API="http://127.0.0.1:4298/v1", ARTI_CLAUDE_SKILLS=str(CLAUDE_SKILLS))
assert Path(os.environ["ARTI_HOME"]).resolve() != (Path.home() / ".arti").resolve()
sys.path.insert(0, str(REAL / "dashboard" / "server")); sys.path.insert(0, str(REAL / "tools" / "_shared"))
sys.path.insert(0, str(REAL / "tools" / "arti-update"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
import license as lic
import bundle

results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


def raw_pub(k):
    return base64.b64encode(k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()


def pem(k):
    return k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())


lic_priv, rel_priv = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
PK = ROOT / "pubkeys.test.json"
PK.write_text(json.dumps({"license": {"test-1": raw_pub(lic_priv)}, "release": {"t-rel": raw_pub(rel_priv)}}))
lic.PUBKEYS_PATH = str(PK)
REL_PEM = ROOT / "rel.pem"
REL_PEM.write_bytes(pem(rel_priv))
NOTES = ROOT / "notes.md"
NOTES.write_text("## Notes\n- things changed\n", encoding="utf-8")


def fmt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def make_license(machine, days=365):
    now = lic.utcnow()
    p = {"key_id": "kid-TEST42", "name": "Test Buyer", "tier": "individual", "seats": 1, "machine_hash": machine, "issued": fmt(now),
         "expires": fmt(now + datetime.timedelta(days=days)), "grace_days": 14, "updates_until": fmt(now + datetime.timedelta(days=days))}
    return {"payload": p, "sig": base64.b64encode(lic_priv.sign(lic.canonical_json(p))).decode(), "kid": "test-1"}


# ---- fake code trees --------------------------------------------------------------------------------------------

STUB = '''import http.server, json, os, sqlite3, sys, threading, time
here = os.path.dirname(os.path.abspath(__file__))
ver = open(os.path.join(here, "..", "VERSION"), encoding="utf-8").read().split("FRAMEWORK_VERSION=")[1].split()[0]
if os.path.exists(os.path.join(here, "migrate.flag")):   # a release that migrates the database, then fails
    con = sqlite3.connect(os.path.join(os.environ["ARTI_HOME"], "memory", "arti.db"))
    con.execute("INSERT INTO t VALUES ('migrated')"); con.commit(); con.close()
if os.path.exists(os.path.join(here, "crash.flag")):
    sys.exit(3)
if os.path.exists(os.path.join(here, "silent.flag")):
    time.sleep(600)
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.endswith("/quit"):
            self.send_response(200); self.end_headers(); threading.Thread(target=srv.shutdown, daemon=True).start(); return
        data = json.dumps({"version": ver}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
srv = http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H)
srv.serve_forever()
'''
TEXT_FILES = ("CLAUDE.md", "CAPABILITIES.md", "LICENSE.txt", "README.md", "UPDATING.md", "prompt-templates.md",
              "install.ps1", "install.sh", "install.bat", ".mcp.json")


def make_tree(root, version, flags=(), break_cli=False, with_old_skill=False, junk=False):
    root = Path(root)
    if root.exists():
        shutil.rmtree(root)
    for sub in ("tools/arti-update", "tools/_shared", "tools/arti-license", "skills/ARTi-common", "dashboard", "logo"):
        (root / sub).mkdir(parents=True)
    for f in ("cli.py", "bundle.py", "updater.py"):
        shutil.copy(REAL / "tools" / "arti-update" / f, root / "tools" / "arti-update" / f)
    for f in ("license.py", "paths.py"):
        shutil.copy(REAL / "tools" / "_shared" / f, root / "tools" / "_shared" / f)
    for f in ("cli.py", "pubkeys.json", "config.json"):
        shutil.copy(REAL / "tools" / "arti-license" / f, root / "tools" / "arti-license" / f)
    if break_cli:
        (root / "tools" / "arti-update" / "cli.py").write_text("def broken(:\n", encoding="utf-8")
    (root / "tools" / "marker.txt").write_text("tools %s" % version, encoding="utf-8")
    (root / "skills" / "ARTi-common" / "SKILL.md").write_text("common skill %s" % version, encoding="utf-8")
    if with_old_skill:
        (root / "skills" / "ARTi-old").mkdir()
        (root / "skills" / "ARTi-old" / "SKILL.md").write_text("old skill", encoding="utf-8")
    else:
        (root / "skills" / "ARTi-new").mkdir()
        (root / "skills" / "ARTi-new" / "SKILL.md").write_text("new skill %s" % version, encoding="utf-8")
    (root / "dashboard" / "stub.py").write_text(STUB, encoding="utf-8")
    (root / "dashboard" / "index.html").write_text("dashboard %s" % version, encoding="utf-8")
    for flag in flags:
        (root / "dashboard" / flag).write_text("1", encoding="utf-8")
    (root / "logo" / "mark.txt").write_text("logo", encoding="utf-8")
    for name in TEXT_FILES:
        (root / name).write_text("%s %s\n" % (name, version), encoding="utf-8")
    (root / ".gitignore").write_text("__pycache__/\nserver.log\nmemory/\n", encoding="utf-8")
    (root / "VERSION").write_text("PYTHON_BUILD_TAG=1\nPYTHON_VERSION=3.11.10\nFRAMEWORK_VERSION=%s\n" % version, encoding="utf-8")
    if junk:   # ignored files that must never reach a bundle
        (root / "tools" / "__pycache__").mkdir()
        (root / "tools" / "__pycache__" / "x.pyc").write_bytes(b"junk")
        (root / "dashboard" / "server.log").write_text("log", encoding="utf-8")
        (root / "memory").mkdir()
        (root / "memory" / "private.md").write_text("private", encoding="utf-8")
    return root


def tree_hash(root):
    h = hashlib.sha256()
    for item in sorted(bundle.UPDATE_ITEMS):
        p = Path(root) / item
        files = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file()) if p.is_dir() else []
        for f in files:
            rel = f.relative_to(root).as_posix()
            if "__pycache__" in rel or rel.endswith(".pyc"):
                continue
            h.update(rel.encode()); h.update(f.read_bytes())
    return h.hexdigest()


def git(cwd, *a):
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "core.autocrlf=false", *a], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("git %s: %s" % (a, r.stderr))
    return r.stdout


RELEASES = {}   # version -> {"zip": Path, "doc": dict}


def build_release(version, **tree_kw):
    """Make a release source tree in its own git repo, build the bundle with the real build_bundle.py and sign the
    manifest with the real publish_release.py (--dry-run), exactly the maintainer's path."""
    src = make_tree(ROOT / ("src-" + version), version, junk=True, **tree_kw)
    git(src, "init", "-q"); git(src, "add", "-A"); git(src, "commit", "-q", "-m", "r")
    out = ROOT / "dist"
    r = subprocess.run([PY, str(BUILD), "--source", str(src), "--out", str(out)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr + r.stdout
    zpath = out / ("arti-%s.zip" % version)
    p = subprocess.run([PY, str(PUBLISH), "--key", str(REL_PEM), "--kid", "t-rel", "--pubkeys", str(PK), "--notes", str(NOTES),
                        "--version", version, "--dry-run", "--bundle", str(zpath)], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    doc = json.loads(p.stdout[p.stdout.index("\n{") + 1:])
    RELEASES[version] = {"zip": zpath, "doc": doc, "publish_out": p.stdout}
    return RELEASES[version]


def sign_doc(manifest):
    return {"manifest": manifest, "sig": base64.b64encode(rel_priv.sign(lic.canonical_json(manifest))).decode(), "kid": "t-rel"}


# ---- fake Worker ------------------------------------------------------------------------------------------------

W = {"release": None, "zip": None, "calls": [], "drop_after": None, "dropped": 0, "corrupt": False, "dl_error": None, "downloads": 0}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, status, obj):
        data = json.dumps(obj).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        W["calls"].append((self.path, body, self.headers.get("Range")))
        if self.path == "/v1/update":
            return self._json(200, {"release": W["release"], "locked_newer": None})
        if self.path == "/v1/ack":
            return self._json(200, {"ok": True})
        if self.path in ("/v1/activate", "/v1/validate"):
            return self._json(200, {"license": make_license(body["machine_hash"]), "seats_used": 1})
        if self.path == "/v1/download":
            if W["dl_error"]:
                status, code = W["dl_error"]
                return self._json(status, {"code": code, "message": code})
            data = bytearray(W["zip"].read_bytes())
            if W["corrupt"]:
                data[len(data) // 2] ^= 0xFF
            start = 0
            rng = self.headers.get("Range")
            if rng:
                start = int(re.match(r"bytes=(\d+)-", rng).group(1))
            part = bytes(data[start:])
            W["downloads"] += 1
            self.send_response(206 if rng else 200)
            self.send_header("Content-Type", "application/zip"); self.send_header("Content-Length", str(len(part)))
            if rng:
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, len(data) - 1, len(data)))
            self.end_headers()
            if W["drop_after"] and not rng:   # the connection dies half way through the first request only
                self.wfile.write(part[:W["drop_after"]]); self.wfile.flush(); W["dropped"] += 1
                self.close_connection = True
                return
            self.wfile.write(part)
            return
        return self._json(404, {"code": "not_found"})


fake = ThreadingHTTPServer(("127.0.0.1", 4298), Fake)
threading.Thread(target=fake.serve_forever, daemon=True).start()

import importlib.util
spec = importlib.util.spec_from_file_location("arti_update_cli_apply", REAL / "tools" / "arti-update" / "cli.py")
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
cli.DASHBOARD_PING = "http://127.0.0.1:4396/api/ping"   # nothing listens here; never the researcher's real dashboard on 4174

# ---- environment helpers ----------------------------------------------------------------------------------------

_stub_ports = iter(range(4310, 4390))
_stubs = []
_dummies = []


def rm_links():
    for p in CLAUDE_SKILLS.iterdir():
        try:
            if bool(os.lstat(p).st_file_attributes & 0x400):
                os.rmdir(p)
            else:
                shutil.rmtree(p)
        except (AttributeError, OSError):
            shutil.rmtree(p, ignore_errors=True)


def link(name, target):
    subprocess.run(["cmd", "/c", "mklink", "/J", str(CLAUDE_SKILLS / name), str(target)], capture_output=True, check=True)


def reset(installed="0.1.0"):
    """A fresh installed tree, fresh data home, no links, no state."""
    stop_stubs()
    rm_links()
    make_tree(CODE, installed, with_old_skill=True)
    for d in (".update", ".backup", "memory"):
        shutil.rmtree(HOME / d, ignore_errors=True)
    (HOME / "memory").mkdir()
    con = sqlite3.connect(HOME / "memory" / "arti.db")
    con.execute("CREATE TABLE t (v TEXT)"); con.execute("INSERT INTO t VALUES ('orig')"); con.commit(); con.close()
    (HOME / "memory" / "notes.md").write_text("my notes", encoding="utf-8")
    (HOME / "voice-profiles").mkdir(exist_ok=True)
    (HOME / "voice-profiles" / "v.md").write_text("voice", encoding="utf-8")
    (HOME / "mcp-keys.json").write_text('{"OPENALEX_API_KEY": "secret"}', encoding="utf-8")
    (HOME / "license.json").write_text(json.dumps(make_license(lic.machine_hash())))
    link("ARTi-common", CODE / "skills" / "ARTi-common")
    link("ARTi-old", CODE / "skills" / "ARTi-old")
    W.update(release=None, zip=None, calls=[], drop_after=None, dropped=0, corrupt=False, dl_error=None, downloads=0)


def home_snapshot():
    out = {}
    for rel in ("memory/notes.md", "voice-profiles/v.md", "mcp-keys.json", "license.json"):
        out[rel] = (HOME / rel).read_bytes()
    return out


def db_rows():
    con = sqlite3.connect(HOME / "memory" / "arti.db")
    rows = [r[0] for r in con.execute("SELECT v FROM t ORDER BY rowid")]
    con.close()
    return rows


def ping(port):
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/ping" % port, timeout=2) as r:
            return json.load(r)["version"]
    except Exception:
        return None


def quit_stub(port):
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:%d/api/quit" % port, timeout=2).read()
    except Exception:
        pass
    if port in _stubs:
        _stubs.remove(port)


def start_stub_for_current():
    """Pretend the old dashboard is running: a stub for the installed tree, so 'put back' can be seen to restart it."""
    port = next(_stub_ports)
    subprocess.Popen([PY, str(CODE / "dashboard" / "stub.py"), str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _stubs.append(port)
    return port


def options(pid=0, relaunch=True, health_s=10, wait_s=2):
    port = next(_stub_ports)
    o = {"pid": pid, "claude_skills": str(CLAUDE_SKILLS), "wait_s": wait_s, "health_s": health_s,
         "smoke": [PY, str(CODE / "tools" / "arti-update" / "cli.py"), "status"]}
    if relaunch:
        o.update(relaunch=[PY, str(CODE / "dashboard" / "stub.py"), str(port)], relaunch_cwd=str(CODE / "dashboard"),
                 ping_url="http://127.0.0.1:%d/api/ping" % port)
        _stubs.append(port)
    o["port"] = port
    return o


def stop_stubs():
    for port in list(_stubs):
        quit_stub(port)
    time.sleep(0.8)


def dummy_dashboard():
    p = subprocess.Popen([PY, "-c", "import time; time.sleep(600)"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _dummies.append(p)
    return p


def serve(version):
    W["release"] = RELEASES[version]["doc"]
    W["zip"] = RELEASES[version]["zip"]


def prepare(version, ack=True):
    serve(version)
    st = cli.check(force=True)
    assert st["available"] and st["available"]["version"] == version, st
    if ack:
        assert cli.ack(version)[0]


def run_apply(version, opts, expect_ok=None):
    for port in list(_stubs):
        if port != opts.get("port"):
            quit_stub(port)   # the previous 'dashboard' must not be running: it would hold its folder as the working directory
    time.sleep(0.5)
    proc = cli.apply(version, opts=opts)
    res = cli.wait_for_result(proc, timeout=120, say=lambda s: None)
    proc.wait(timeout=30)
    return res


# =================================================================================================================
print("== build_bundle / publish_release ==")
r1 = build_release("0.2.0")
build_release("0.3.0")
build_release("0.4.0")
z = zipfile.ZipFile(r1["zip"])
names = z.namelist()
check("bundle holds only tracked items: no __pycache__, server.log or memory/", not any("__pycache__" in n or n.endswith("server.log") or n.startswith("memory") for n in names), [n for n in names if "pycache" in n or "memory" in n])
check("bundle top-level entries are all update items", {n.split("/")[0] for n in names} <= set(bundle.UPDATE_ITEMS))
check("bundle passes the client's own validation", bundle.validate(z, "0.2.0"))
man = RELEASES["0.2.0"]["doc"]["manifest"]
check("manifest.bundle carries sha256, size, r2_key and items", man["bundle"]["sha256"] == bundle.sha256_file(r1["zip"]) and man["bundle"]["size"] == r1["zip"].stat().st_size and man["bundle"]["r2_key"] == "releases/arti-0.2.0.zip" and "VERSION" in man["bundle"]["items"], man["bundle"])
check("publish_release prints the R2 upload command, upload before publish", "wrangler r2 object put \"arti-releases/releases/arti-0.2.0.zip\"" in r1["publish_out"] and "FIRST" in r1["publish_out"], r1["publish_out"][:400])
check("the signed manifest verifies against the release key", lic.verify_signature(man, RELEASES["0.2.0"]["doc"]["sig"], raw_pub(rel_priv)))
b1 = subprocess.run([PY, str(BUILD), "--source", str(ROOT / "src-0.2.0"), "--out", str(ROOT / "dist2")], capture_output=True, text=True)
check("the same tree builds to the same sha256 (deterministic)", bundle.sha256_file(ROOT / "dist2" / "arti-0.2.0.zip") == man["bundle"]["sha256"], b1.stderr)
(ROOT / "src-0.2.0" / "README.md").write_text("changed", encoding="utf-8")
b2 = subprocess.run([PY, str(BUILD), "--source", str(ROOT / "src-0.2.0"), "--out", str(ROOT / "dist3")], capture_output=True, text=True)
check("a dirty tree is refused without --allow-dirty", b2.returncode != 0 and "uncommitted" in b2.stderr, b2.stderr)
b3 = subprocess.run([PY, str(BUILD), "--source", str(ROOT / "src-0.2.0"), "--out", str(ROOT / "dist3"), "--allow-dirty"], capture_output=True, text=True)
check("--allow-dirty builds but warns", b3.returncode == 0 and "dirty tree" in b3.stdout)
git(ROOT / "src-0.2.0", "checkout", "--", "README.md")
p = subprocess.run([PY, str(PUBLISH), "--key", str(REL_PEM), "--kid", "t-rel", "--pubkeys", str(PK), "--notes", str(NOTES), "--version", "0.9.0",
                    "--dry-run", "--bundle", str(r1["zip"])], capture_output=True, text=True)
check("publish_release refuses a bundle whose VERSION is not the release version", p.returncode != 0 and "expected 0.9.0" in p.stderr, p.stderr)
p = subprocess.run([PY, str(PUBLISH), "--key", str(REL_PEM), "--kid", "t-rel", "--pubkeys", str(PK), "--notes", str(NOTES), "--version", "0.2.0",
                    "--dry-run", "--bundle", str(r1["zip"]), "--requires-installer"], capture_output=True, text=True)
check("--bundle and --requires-installer exclude each other", p.returncode != 0 and "exclude each other" in p.stderr, p.stderr)

print("== UPDATE_ITEMS parity ==")
ps1 = (REAL / "install.ps1").read_text(encoding="utf-8")
sh = (REAL / "install.sh").read_text(encoding="utf-8")
nsi = (REAL / "installer" / "arti-installer.nsi").read_text(encoding="utf-8")
ps_items = re.findall(r"'([^']+)'", re.search(r"\$TrackedItems = @\((.*?)\)", ps1, re.S).group(1))
sh_items = re.search(r"TRACKED_ITEMS=\((.*?)\)", sh).group(1).split()
nsi_items = [m.group(1) for m in re.finditer(r'^\s*File (?:/r )?(?:/x "[^"]*" )*"\.\.\\([^"\\]+)"\s*$', nsi, re.M)]
check("UPDATE_ITEMS equals install.ps1 TrackedItems", list(bundle.UPDATE_ITEMS) == ps_items, ps_items)
check("UPDATE_ITEMS equals install.sh TRACKED_ITEMS", list(bundle.UPDATE_ITEMS) == sh_items, sh_items)
check("UPDATE_ITEMS equals the NSIS File list (same set)", set(bundle.UPDATE_ITEMS) == set(nsi_items), sorted(set(bundle.UPDATE_ITEMS) ^ set(nsi_items)))

print("== bundle rules against hostile zips ==")


def zip_with(entries, mode_for=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name)
            if mode_for and name in mode_for:
                info.external_attr = mode_for[name] << 16
            zf.writestr(info, data)
    buf.seek(0)
    return zipfile.ZipFile(buf)


ver_ok = ("VERSION", "FRAMEWORK_VERSION=0.2.0\n")
for label, entries, mode in [
    ("zip-slip with ..", [ver_ok, ("tools/../../evil.txt", "x")], None),
    ("zip-slip hidden behind a good prefix", [ver_ok, ("skills/../../evil.txt", "x")], None),
    ("absolute path", [ver_ok, ("/etc/evil", "x")], None),
    ("backslash path", [ver_ok, ("tools\\..\\evil", "x")], None),
    ("drive letter", [ver_ok, ("C:/evil.txt", "x")], None),
    ("an item outside the list (memory/)", [ver_ok, ("memory/private.md", "x")], None),
    ("an item outside the list (license.json)", [ver_ok, ("license.json", "x")], None),
    ("a symlink entry", [ver_ok, ("tools/link", "../../x")], {"tools/link": 0o120777}),
    ("no VERSION file", [("tools/a.txt", "x")], None),
    ("duplicate names", [ver_ok, ("tools/a", "1"), ("tools/A", "2")], None),
    ("a file where a single file is required", [ver_ok, ("CLAUDE.md/inner", "x")], None),
]:
    try:
        bundle.validate(zip_with(entries, mode), "0.2.0")
        check("rejected: " + label, False)
    except bundle.BundleError:
        check("rejected: " + label, True)
try:
    bundle.validate(zip_with([("VERSION", "FRAMEWORK_VERSION=0.3.0\n")]), "0.2.0")
    check("rejected: a bundle of another version", False)
except bundle.BundleError:
    check("rejected: a bundle of another version", True)

# =================================================================================================================
print("== update succeeds ==")
reset()
before_home = home_snapshot()
old_tree = tree_hash(CODE)
dash_pid = dummy_dashboard()
prepare("0.2.0")
check("link to an existing skill works before the update", (CLAUDE_SKILLS / "ARTi-common" / "SKILL.md").read_text() == "common skill 0.1.0")
o = options(pid=dash_pid.pid)
res = run_apply("0.2.0", o)
check("result is ok, from 0.1.0 to 0.2.0", res.get("ok") and res["from"] == "0.1.0" and res["to"] == "0.2.0" and res["action"] == "update", res)
check("installed VERSION is 0.2.0", cli.current_version() == "0.2.0")
check("the code really changed (tools, skills, dashboard)", (CODE / "tools" / "marker.txt").read_text() == "tools 0.2.0" and (CODE / "dashboard" / "index.html").read_text() == "dashboard 0.2.0" and tree_hash(CODE) != old_tree)
check("the old dashboard process was stopped", dash_pid.poll() is not None)
check("the relaunched dashboard answers and is the new version", ping(o["port"]) == "0.2.0", ping(o["port"]))
after = home_snapshot()
check("memory/, voice-profiles, mcp-keys.json and license.json are untouched", after == before_home)
check("arti.db is untouched on success", db_rows() == ["orig"], db_rows())
check("a backup of the old version exists with its items", (HOME / ".backup" / "0.1.0" / "tools" / "marker.txt").read_text() == "tools 0.1.0" and (HOME / ".backup" / "0.1.0" / "VERSION").exists())
bak = sqlite3.connect(HOME / ".backup" / "0.1.0" / "arti.db.bak"); rows = [r[0] for r in bak.execute("SELECT v FROM t")]; bak.close()
check("arti.db.bak is a usable copy of the database", rows == ["orig"], rows)
check("staging and download folders are cleaned up", not (HOME / ".update" / "staging").exists() and not (HOME / ".update" / "download").exists())
check("skill link kept working and shows the new text", (CLAUDE_SKILLS / "ARTi-common" / "SKILL.md").read_text() == "common skill 0.2.0")
check("a new skill got a link", (CLAUDE_SKILLS / "ARTi-new" / "SKILL.md").read_text() == "new skill 0.2.0")
check("the link of a removed skill is gone, not left dangling", not os.path.lexists(CLAUDE_SKILLS / "ARTi-old"))
check("the Worker was asked for the download with the license file", any(c[0] == "/v1/download" and c[1].get("version") == "0.2.0" and "license" in c[1] and len(c[1]["machine_hash"]) == 64 for c in W["calls"]))
rolled = cli.read_result()
check("result.json stays until the dashboard shows it, then shows once", cli.read_result(consume=True) is not None and cli.read_result() is None)

print("== keep only 2 backups ==")
for v in ("0.3.0", "0.4.0"):
    prepare(v)
    res = run_apply(v, options())
    check("update to %s ok" % v, res.get("ok"), res)
check("only the 2 newest backups remain", sorted(os.listdir(HOME / ".backup")) == ["0.2.0", "0.3.0"], os.listdir(HOME / ".backup"))
check("list_backups newest first", cli.list_backups() == ["0.3.0", "0.2.0"], cli.list_backups())

print("== manual rollback ==")
con = sqlite3.connect(HOME / "memory" / "arti.db"); con.execute("INSERT INTO t VALUES ('added later')"); con.commit(); con.close()
tree_030 = None
res_pid = dummy_dashboard()
stop_stubs()
o = options(pid=res_pid.pid)
proc = cli.rollback("0.3.0", opts=o)
res = cli.wait_for_result(proc, timeout=60, say=lambda s: None)
check("rollback result ok to 0.3.0", res.get("ok") and res["action"] == "rollback" and res["to"] == "0.3.0" and res["from"] == "0.4.0", res)
check("installed version is 0.3.0 again, code restored", cli.current_version() == "0.3.0" and (CODE / "tools" / "marker.txt").read_text() == "tools 0.3.0")
check("the database is NOT rolled back by a manual rollback", db_rows() == ["orig", "added later"], db_rows())
check("the used backup is consumed", "0.3.0" not in os.listdir(HOME / ".backup"), os.listdir(HOME / ".backup"))
check("the relaunched dashboard is the restored version", ping(o["port"]) == "0.3.0")
try:
    cli.rollback("9.9.9", opts=options(relaunch=False)); check("rollback of an unknown version refused", False)
except cli.UpdateFailure as e:
    check("rollback of an unknown version refused", e.code == "no_backup")

# =================================================================================================================
print("== refusals before anything changes ==")
reset()
serve("0.2.0")
cli.check(force=True)
try:
    cli.apply("0.2.0", opts=options(relaunch=False)); check("not acknowledged: refused", False)
except cli.UpdateFailure as e:
    check("not acknowledged: refused", e.code == "not_acked", e.code)
check("...and nothing was downloaded or changed", W["downloads"] == 0 and cli.current_version() == "0.1.0")
cli.ack("0.2.0")
try:
    cli.apply("9.9.9", opts=options(relaunch=False)); check("a version that is not pending: refused", False)
except cli.UpdateFailure as e:
    check("a version that is not pending: refused", e.code == "no_update", e.code)
# requires_installer
ri = dict(RELEASES["0.2.0"]["doc"]["manifest"], requires_installer=True, bundle=None)
W["release"] = sign_doc(ri)
cli.check(force=True); cli.ack("0.2.0")
try:
    cli.apply("0.2.0", opts=options(relaunch=False)); check("requires_installer: refused", False)
except cli.UpdateFailure as e:
    check("requires_installer: refused", e.code == "requires_installer", e.code)
# min_client above installed
mc = dict(RELEASES["0.2.0"]["doc"]["manifest"], min_client_version="0.1.5")
W["release"] = sign_doc(mc)
cli.check(force=True); cli.ack("0.2.0")
try:
    cli.apply("0.2.0", opts=options(relaunch=False)); check("min_client_version above installed: refused", False)
except cli.UpdateFailure as e:
    check("min_client_version above installed: refused", e.code == "requires_installer", e.code)
# release without a bundle
nb = dict(RELEASES["0.2.0"]["doc"]["manifest"], bundle=None)
W["release"] = sign_doc(nb)
cli.check(force=True); cli.ack("0.2.0")
try:
    cli.apply("0.2.0", opts=options(relaunch=False)); check("a release without a bundle: refused", False)
except cli.UpdateFailure as e:
    check("a release without a bundle: refused", e.code == "no_bundle", e.code)
# not entitled: released after updates_until
late = dict(RELEASES["0.2.0"]["doc"]["manifest"], released=fmt(lic.utcnow() + datetime.timedelta(days=900)))
W["release"] = sign_doc(late); W["zip"] = RELEASES["0.2.0"]["zip"]
cli.check(force=True); cli.ack("0.2.0")
try:
    cli.apply("0.2.0", opts=options(relaunch=False)); check("released after updates_until: refused", False)
except cli.UpdateFailure as e:
    check("released after updates_until: refused", e.code == "not_entitled", e.code)
# revoked
serve("0.2.0"); cli.check(force=True); cli.ack("0.2.0")
cli._license_cli().mark_revoked()
try:
    cli.apply("0.2.0", opts=options(relaunch=False)); check("revoked license: refused", False)
except cli.UpdateFailure as e:
    check("revoked license: refused", e.code == "revoked", e.code)
check("nothing was downloaded in any refusal", W["downloads"] == 0)
# the Worker itself says no
reset(); prepare("0.2.0")
W["dl_error"] = (403, "not_entitled")
try:
    cli.apply("0.2.0", opts=options(relaunch=False)); check("Worker says not_entitled: apply stops", False)
except cli.UpdateFailure as e:
    check("Worker says not_entitled: apply stops", e.code == "not_entitled", e.code)
W["dl_error"] = (403, "key_revoked")
try:
    cli.apply("0.2.0", opts=options(relaunch=False)); check("Worker says key_revoked: apply stops", False)
except cli.UpdateFailure as e:
    check("Worker says key_revoked: apply stops", e.code == "revoked", e.code)
check("...and key_revoked sets the license aside", not (HOME / "license.json").exists() and (HOME / "license.revoked.json").exists())
check("code untouched after all that", cli.current_version() == "0.1.0")

print("== download problems ==")
reset(); prepare("0.2.0")
W["corrupt"] = True
try:
    cli.apply("0.2.0", opts=options(relaunch=False)); check("corrupt download: refused", False)
except cli.UpdateFailure as e:
    check("corrupt download (wrong sha256): refused", e.code == "bad_download", e.code)
check("...the bad file is thrown away and nothing changed", not list((HOME / ".update" / "download").glob("*.zip*")) and cli.current_version() == "0.1.0")
W["corrupt"] = False
size = RELEASES["0.2.0"]["zip"].stat().st_size
W["drop_after"] = size // 3
snap = tree_hash(CODE)
calls_before = len(W["calls"])
path = cli.download("0.2.0", retry_wait=0.2)
check("an interrupted download resumes with a Range request and finishes", bundle.sha256_file(path) == RELEASES["0.2.0"]["doc"]["manifest"]["bundle"]["sha256"] and W["dropped"] == 1, (W["dropped"], W["calls"][-2:]))
rngs = [c[2] for c in W["calls"][calls_before:] if c[0] == "/v1/download"]
check("the second request carried Range: bytes=<received>-", len(rngs) >= 2 and rngs[0] is None and re.match(r"bytes=\d+-$", rngs[1] or ""), rngs)
done_calls = []
os.remove(path)
cli.download("0.2.0", progress=lambda d, t: done_calls.append((d, t)))
check("progress reports bytes up to the total", done_calls and done_calls[-1] == (size, size), done_calls[-1:] if done_calls else None)
n = W["downloads"]
cli.download("0.2.0")
check("a complete verified download is reused, not fetched again", W["downloads"] == n)

# the updater must not trust the process that started it: tampered manifest, hostile zips signed by the release key
print("== updater re-verifies everything itself ==")


def run_updater_direct(zip_path, doc, version="0.2.0", old="0.1.0"):
    reset()
    dd = HOME / ".update" / "download"; dd.mkdir(parents=True, exist_ok=True)
    zp = dd / "x.zip"; shutil.copy(zip_path, zp)
    dp = dd / "x.json"; dp.write_text(json.dumps(doc))
    # copy as _spawn_updater does
    run = HOME / ".update" / "run"; run.mkdir(parents=True, exist_ok=True)
    for src in (REAL / "tools" / "arti-update" / "updater.py", REAL / "tools" / "arti-update" / "bundle.py", REAL / "tools" / "_shared" / "license.py", REAL / "tools" / "_shared" / "paths.py"):
        shutil.copy(src, run)
    shutil.copy(PK, run / "pubkeys.json")
    snap = tree_hash(CODE)
    r = subprocess.run([PY, str(run / "updater.py"), "--home", str(HOME), "--code", str(CODE), "--zip", str(zp), "--doc", str(dp), "--version", version,
                        "--from", old, "--claude-skills", str(CLAUDE_SKILLS)], capture_output=True, text=True)
    return cli.read_result(), snap == tree_hash(CODE), r


good = RELEASES["0.2.0"]
forged = json.loads(json.dumps(good["doc"])); forged["manifest"]["notes"] = "evil"
res, unchanged, r = run_updater_direct(good["zip"], forged)
check("forged manifest: updater refuses, code unchanged", res and not res["ok"] and res["reason"] == "bad_manifest" and unchanged, res)
other = Ed25519PrivateKey.generate()
wrong = dict(good["doc"]); wrong["sig"] = base64.b64encode(other.sign(lic.canonical_json(good["doc"]["manifest"]))).decode()
res, unchanged, r = run_updater_direct(good["zip"], wrong)
check("manifest signed by an unknown key: refused", res and not res["ok"] and res["reason"] == "bad_manifest" and unchanged, res)
bigger = ROOT / "other.zip"; shutil.copy(good["zip"], bigger)
with open(bigger, "ab") as f:
    f.write(b"\0")
res, unchanged, r = run_updater_direct(bigger, good["doc"])
check("zip that does not match the signed size/sha256: refused", res and not res["ok"] and res["reason"] == "bad_download" and unchanged, res)


def hostile(label, entries, mode=None, items=None):
    buf = ROOT / ("hostile-%s.zip" % re.sub(r"\W", "", label))
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries:
            info = zipfile.ZipInfo(name)
            if mode and name in mode:
                info.external_attr = mode[name] << 16
            zf.writestr(info, data)
    m = dict(good["doc"]["manifest"])
    m["bundle"] = {"sha256": bundle.sha256_file(buf), "size": buf.stat().st_size, "r2_key": "releases/arti-0.2.0.zip", "items": items or ["VERSION"]}
    res, unchanged, r = run_updater_direct(buf, sign_doc(m))
    escaped = (ROOT / "evil.txt").exists() or (ROOT.parent / "evil.txt").exists()
    check("signed but hostile zip (%s): refused, nothing written outside" % label, res and not res["ok"] and res["reason"] == "bad_bundle" and unchanged and not escaped, res)


hostile("zip-slip", [("VERSION", "FRAMEWORK_VERSION=0.2.0\n"), ("tools/../../evil.txt", "x")], items=["VERSION", "tools"])
hostile("outside the list", [("VERSION", "FRAMEWORK_VERSION=0.2.0\n"), ("memory/arti.db", "x")], items=["VERSION"])
hostile("symlink", [("VERSION", "FRAMEWORK_VERSION=0.2.0\n"), ("tools/l", "../x")], {"tools/l": 0o120777}, items=["VERSION", "tools"])
hostile("items differ from the manifest", [("VERSION", "FRAMEWORK_VERSION=0.2.0\n"), ("tools/a.txt", "x")], items=["VERSION"])
hostile("wrong version inside", [("VERSION", "FRAMEWORK_VERSION=0.7.0\n")])

# =================================================================================================================
print("== swap fails: a locked file ==")
if sys.platform == "win32":
    reset(); prepare("0.2.0")
    snap_tree, snap_home = tree_hash(CODE), home_snapshot()
    held = open(CODE / "tools" / "marker.txt", "rb")   # an open handle makes renaming the folder impossible on Windows
    pid = dummy_dashboard()
    o = options(pid=pid.pid, relaunch=True)
    res = run_apply("0.2.0", o)
    held.close()
    check("locked file: the update is cancelled with a clear reason", not res.get("ok") and res["reason"] == "locked" and "Close other" in res["message"], res)
    check("locked file: the code tree is exactly as before", tree_hash(CODE) == snap_tree and cli.current_version() == "0.1.0")
    check("locked file: data untouched, no pointless backup left", home_snapshot() == snap_home and cli.list_backups() == [] and not (HOME / ".backup" / "0.1.0").exists(), os.listdir(HOME / ".backup") if (HOME / ".backup").exists() else None)
    check("locked file: the old dashboard was started again", ping(o["port"]) == "0.1.0", ping(o["port"]))
    check("locked file: skill links still fine", (CLAUDE_SKILLS / "ARTi-old" / "SKILL.md").read_text() == "old skill")
    reset(); prepare("0.2.0")
    held = open(CODE / "skills" / "ARTi-common" / "SKILL.md", "rb")   # tools swaps fine, then skills fails: tools must go back
    snap_tree = tree_hash(CODE)
    o = options(pid=0, relaunch=False)
    res = run_apply("0.2.0", o)
    held.close()
    check("locked file in a later item: what was swapped is put back", not res.get("ok") and res["reason"] == "locked" and tree_hash(CODE) == snap_tree and cli.current_version() == "0.1.0", res)
else:
    print("SKIP locked-file scenario (Windows only)")

print("== new version does not work: automatic rollback ==")
for label, ver, flags, brk in [("smoke command fails (broken cli.py)", "0.9.1", (), True),
                               ("dashboard never answers", "0.9.2", ("silent.flag",), False),
                               ("dashboard crashes after migrating the database", "0.9.3", ("crash.flag", "migrate.flag"), False)]:
    build_release(ver, flags=flags, break_cli=brk)
    reset(); prepare(ver)
    snap_tree, snap_home = tree_hash(CODE), home_snapshot()
    pid = dummy_dashboard()
    o = options(pid=pid.pid, health_s=4)
    res = run_apply(ver, o)
    check("%s: update cancelled with a reason" % label, not res.get("ok") and res["reason"] == "unhealthy" and ver in res["message"], res)
    check("%s: code tree restored byte for byte" % label, tree_hash(CODE) == snap_tree and cli.current_version() == "0.1.0")
    check("%s: arti.db restored (no migrated row)" % label, db_rows() == ["orig"], db_rows())
    check("%s: other data untouched" % label, home_snapshot() == snap_home)
    check("%s: the old dashboard is running again" % label, ping(o["port"]) == "0.1.0", ping(o["port"]))
    check("%s: no rollback offered for the current version" % label, cli.list_backups() == [])
    check("%s: skill links back to the old state" % label, (CLAUDE_SKILLS / "ARTi-old" / "SKILL.md").read_text() == "old skill" and not os.path.lexists(CLAUDE_SKILLS / "ARTi-new"))

print("== CLI use (no dashboard) ==")
reset(); prepare("0.2.0")
cli.DASHBOARD_PING = "http://127.0.0.1:%d/api/ping" % start_stub_for_current()
time.sleep(1.5)
try:
    cli.apply("0.2.0"); check("CLI apply refuses while the dashboard answers", False)
except cli.UpdateFailure as e:
    check("CLI apply refuses while the dashboard answers", e.code == "dashboard_running", e.code)
for p in list(_stubs):
    quit_stub(p)
time.sleep(1.0)
class Buf(io.StringIO):
    def reconfigure(self, **k):
        pass


rc_out = Buf()
import contextlib
with contextlib.redirect_stdout(rc_out):
    rc = cli.main(["apply", "0.2.0"])
check("CLI apply works when no dashboard runs, and reports it", rc == 0 and "Updated from 0.1.0 to 0.2.0" in rc_out.getvalue() and cli.current_version() == "0.2.0", rc_out.getvalue())

# =================================================================================================================
print("== dashboard UI ==")
reset()
import server as dash
import update_check
dash.PORT = 4299
httpd = dash.create_server()
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:4299"
STOPPED = []
update_check.stop_process = lambda: STOPPED.append(time.time())
UI = {"pid": None, "opts": None}


def ui_options(pid=0):
    UI["opts"] = options(pid=UI["pid"].pid if UI["pid"] else 0, health_s=6)
    return UI["opts"]


update_check.arti_update.dashboard_options = ui_options
import urllib.request, urllib.error


def api(path, data=None):
    req = urllib.request.Request(BASE + path, data=None if data is None else json.dumps(data).encode(), headers={"Content-Type": "application/json"}, method="GET" if data is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


st, body = api("/api/update/apply", {"version": "0.2.0"})
check("API apply with nothing pending: 400 no_update", st == 400 and body.get("code") == "no_update", (st, body))
serve("0.2.0")
st, body = api("/api/update/check", {})
st, body = api("/api/update/apply", {"version": "0.2.0"})
check("API apply before 'I have read this': 400 not_acked", st == 400 and body.get("code") == "not_acked", (st, body))
check("status says can_apply and lists no backups yet", api("/api/update/status")[1]["can_apply"] is True and api("/api/update/status")[1]["backups"] == [])

from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path=BROWSER, headless=True)
    pg = br.new_page(viewport={"width": 1280, "height": 800})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    dialogs = []
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    pg.goto(BASE + "/"); time.sleep(1.2)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.8)
    check("UI: before acknowledging there is no Update now button", not pg.is_visible("#updApplyBtn") and pg.is_visible("#updAckBtn"))
    check("UI: no rollback row, no progress, no overlay, no banners at rest", not pg.is_visible("#updRollback") and not pg.is_visible("#updProgress") and not pg.is_visible("#updOverlay") and not pg.is_visible("#updResult") and not pg.is_visible("#updFail"))
    pg.screenshot(path=str(SHOTS / "a1-notes.png"))
    pg.click("#updAckBtn"); time.sleep(1.0)
    check("UI: after 'I have read this' the Update now button appears", pg.is_visible("#updApplyBtn") and not pg.is_visible("#updAckBtn"))
    check("UI: the old 'comes in a later version' text is gone", "later version" not in pg.inner_text("#updAfterAck") and "restarts by itself" in pg.inner_text("#updAfterAck"), pg.inner_text("#updAfterAck"))
    pg.screenshot(path=str(SHOTS / "a2-update-now.png"))

    # slow the download a little so the progress bar can be seen
    UI["pid"] = dummy_dashboard()
    W["drop_after"] = None
    orig = cli.download
    pg.click("#updApplyBtn")
    seen_progress = False
    for _ in range(60):
        time.sleep(0.15)
        if pg.is_visible("#updProgress") or pg.is_visible("#updOverlay"):
            seen_progress = True
            break
    check("UI: clicking Update now shows progress", seen_progress)
    deadline = time.time() + 40
    while time.time() < deadline and not pg.is_visible("#updOverlay"):
        time.sleep(0.25)
    check("UI: the restart overlay appears once the update is ready", pg.is_visible("#updOverlay") and "Updating" in pg.inner_text("#updOverlayTitle"))
    pg.screenshot(path=str(SHOTS / "a3-overlay.png"))
    deadline = time.time() + 40
    while time.time() < deadline and cli.read_result() is None:
        time.sleep(0.25)
    check("UI: the dashboard was asked to exit exactly when ready", len(STOPPED) == 1, STOPPED)
    check("UI: the update was applied by the updater", cli.current_version() == "0.2.0", cli.read_result())
    # the real process would have died here; the test 'restarts' it by resetting the in-memory state and reloading
    update_check.STATE.update(phase="idle", action=None, version=None, code=None, message=None)
    pg.reload(); time.sleep(1.5)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.8)
    txt = pg.inner_text("#updResultText") if pg.is_visible("#updResult") else ""
    check("UI: the result banner says updated from 0.1.0 to 0.2.0", "Updated from version 0.1.0 to version 0.2.0" in txt, txt)
    check("UI: a Roll back to v0.1.0 button is offered", pg.is_visible("#updRollback") and "v0.1.0" in pg.inner_text("#updRollbackBtn"), pg.inner_text("#updRollbackBtn"))
    check("UI: no overlay after the restart", not pg.is_visible("#updOverlay"))
    check("UI: the applied release is no longer offered (no stale Update now)", not pg.is_visible("#updBox") and not pg.is_visible("#updateCard") and not pg.is_visible("#updApplyBtn"))
    pg.screenshot(path=str(SHOTS / "a4-updated.png"))
    pg.reload(); time.sleep(1.2)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.6)
    check("UI: the result is shown once (gone after another reload)", not pg.is_visible("#updResult"))

    # a failing update shown as a cancelled banner, with the old version back
    reset()
    build_ok = "0.9.2"
    serve(build_ok)
    api("/api/update/check", {}); cli.ack(build_ok)
    UI["pid"] = dummy_dashboard()
    update_check.STATE.update(phase="idle", action=None, version=None, code=None, message=None)
    pg.reload(); time.sleep(1.2)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.8)
    check("UI: bad release shows Update now", pg.is_visible("#updApplyBtn"), pg.inner_text("#updBox"))
    STOPPED.clear()
    pg.click("#updApplyBtn")
    deadline = time.time() + 60
    while time.time() < deadline and cli.read_result() is None:
        time.sleep(0.3)
    res = cli.read_result()
    check("UI: bad release was rolled back automatically", res and not res["ok"] and res["reason"] == "unhealthy", res)
    update_check.STATE.update(phase="idle", action=None, version=None, code=None, message=None)
    pg.reload(); time.sleep(1.5)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.8)
    txt = pg.inner_text("#updResultText") if pg.is_visible("#updResult") else ""
    check("UI: the banner says the update was cancelled and 0.1.0 is back, with the reason", "cancelled" in txt and "0.1.0" in txt and "did not start" in txt, txt)
    check("UI: the banner is styled as a problem", "bad" in (pg.get_attribute("#updResult", "class") or ""))
    pg.screenshot(path=str(SHOTS / "a5-cancelled.png"))

    # a refusal while the dashboard stays alive: failure box, button usable again
    reset(); prepare("0.2.0")
    W["corrupt"] = True
    update_check.STATE.update(phase="idle", action=None, version=None, code=None, message=None)
    UI["pid"] = None
    pg.reload(); time.sleep(1.2)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.8)
    pg.click("#updApplyBtn"); time.sleep(5)
    check("UI: a corrupt download shows a failure box and the page stays usable", pg.is_visible("#updFail") and "did not match" in pg.inner_text("#updFailText") and not pg.is_visible("#updOverlay"), pg.inner_text("#updFailText") if pg.is_visible("#updFail") else "hidden")
    pg.screenshot(path=str(SHOTS / "a6-failed.png"))
    pg.click("#updFailClose"); time.sleep(0.5)
    check("UI: dismissing the failure box clears it and re-enables Update now", not pg.is_visible("#updFail") and pg.is_enabled("#updApplyBtn"))
    W["corrupt"] = False

    # manual rollback from the UI
    reset(); prepare("0.2.0")
    UI["pid"] = dummy_dashboard()
    res = run_apply("0.2.0", options(pid=UI["pid"].pid))
    cli.read_result(consume=True)
    update_check.STATE.update(phase="idle", action=None, version=None, code=None, message=None)
    STOPPED.clear()
    pg.reload(); time.sleep(1.5)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.8)
    UI["pid"] = dummy_dashboard()
    stop_stubs()
    dialogs.clear()
    pg.click("#updRollbackBtn")
    deadline = time.time() + 40
    while time.time() < deadline and cli.read_result() is None:
        time.sleep(0.3)
    res = cli.read_result()
    check("UI: Roll back asks first, then restores the earlier version", dialogs and "0.1.0" in dialogs[0] and res and res["ok"] and res["action"] == "rollback" and cli.current_version() == "0.1.0", (dialogs, res))
    update_check.STATE.update(phase="idle", action=None, version=None, code=None, message=None)
    pg.reload(); time.sleep(1.5)
    pg.click('.nav-item[data-view="settings"]'); pg.click('.settings-nav-item[data-cat="about"]'); time.sleep(0.8)
    check("UI: the rollback banner", "Rolled back" in (pg.inner_text("#updResultText") if pg.is_visible("#updResult") else ""))
    pg.screenshot(path=str(SHOTS / "a7-rolled-back.png"))

    # narrow width: no horizontal scroll
    pg.set_viewport_size({"width": 420, "height": 800}); time.sleep(0.5)
    sw = pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    check("UI: narrow width has no horizontal page scroll", sw)
    pg.screenshot(path=str(SHOTS / "a8-narrow.png"))
    check("UI: no page errors", not errors, errors)
    br.close()

print("== cleanup ==")
for p in list(_stubs):
    quit_stub(p)
for d in _dummies:
    try:
        d.kill()
    except OSError:
        pass
httpd.shutdown(); fake.shutdown()
check("the real ~/.claude/skills was never touched", (sorted(os.listdir(REAL_LINKS)) if REAL_LINKS.is_dir() else []) == LINKS_BEFORE)
print("\n%d checks, %d failed" % (len(results), results.count(False)))
for p in CLAUDE_SKILLS.iterdir():   # junctions first, so removing the tree can never follow one
    try:
        os.rmdir(p)
    except OSError:
        pass
time.sleep(2)   # let the stub dashboards and the dummy processes exit: they hold folders of the tree as their working directory
shutil.rmtree(ROOT, ignore_errors=True)
sys.exit(1 if False in results else 0)
