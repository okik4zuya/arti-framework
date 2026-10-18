"""dashboard/server/webview2_runtime.py: detection, the status/retry rules and the lock (offline, no install is started).

Run with the vendored interpreter:  python\\python.exe -I tests\\webview2\\test_webview2_runtime.py

Checks:
  * a runtime whose binary opens is present; a missing binary, a directory in its place and (Windows) a file that
    exists but cannot be opened (the Sandbox's phantom msedgewebview2.exe) are not;
  * decide(): present -> nothing, a live lock or a fresh "installing" mark -> busy, a failure under 24 hours old ->
    wait unless forced, a stale lock/mark or an old failure -> start;
  * describe(): the text states for ok / installing / failed / missing, native or not;
  * the state file round-trips and a corrupt or missing file counts as "no state";
  * the lock file is exclusive, honours a live lock and replaces a dead one (older than 20 minutes);
  * maybe_start_install() starts nothing when the verdict is not "start", and starts exactly one thread when it is.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

CODE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CODE / "dashboard" / "server"))
import webview2_runtime as wr  # noqa: E402

results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


TMP = Path(tempfile.mkdtemp(prefix="arti-wv2-test-"))
NOW = 1_000_000.0


def make_exe(base, version):
    exe = Path(base) / "Microsoft" / "EdgeWebView" / "Application" / version / "msedgewebview2.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    return exe


# ---- detection -------------------------------------------------------------------------------------
good = make_exe(TMP / "good", "1.2.3.4")
good.write_bytes(b"MZ")
check("binary that opens -> present", wr.runtime_present([(str(TMP / "good"), "1.2.3.4")]))
check("registry lists a version, binary missing -> absent", not wr.runtime_present([(str(TMP / "none"), "9.9")]))
check("no registry entry at all -> absent", not wr.runtime_present([]))

as_dir = make_exe(TMP / "dir", "1.2.3.4")
as_dir.mkdir()
check("a directory where the binary should be -> absent", as_dir.exists() and not wr.runtime_present([(str(TMP / "dir"), "1.2.3.4")]))

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    ghost = make_exe(TMP / "ghost", "1.2.3.4")
    ghost.write_bytes(b"MZ")
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateFileW.restype = wintypes.HANDLE
    k32.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
                                wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    handle = k32.CreateFileW(str(ghost), 0x80000000, 0, None, 3, 0x80, None)   # read, share mode 0 = exclusive
    try:
        check("locked file exists but cannot be opened -> absent (phantom entry)",
              handle not in (None, wintypes.HANDLE(-1).value) and ghost.exists()
              and not wr.runtime_present([(str(TMP / "ghost"), "1.2.3.4")]))
    finally:
        k32.CloseHandle(handle)
else:
    print("SKIP locked-file case (Windows only)")

# ---- decide ----------------------------------------------------------------------------------------
fresh_fail = {"status": "failed", "at": NOW - 3600}
old_fail = {"status": "failed", "at": NOW - 25 * 3600}
check("present wins over everything", wr.decide(fresh_fail, NOW, True, True) == "present")
check("live lock -> busy", wr.decide(None, NOW, False, True) == "busy")
check("fresh installing mark -> busy", wr.decide({"status": "installing", "at": NOW - 60}, NOW, False, False) == "busy")
check("stale installing mark -> start", wr.decide({"status": "installing", "at": NOW - 21 * 60}, NOW, False, False) == "start")
check("no state -> start", wr.decide({}, NOW, False, False) == "start")
check("failure 1 hour ago -> wait", wr.decide(fresh_fail, NOW, False, False) == "wait")
check("failure 1 hour ago, manual retry -> start", wr.decide(fresh_fail, NOW, False, False, force=True) == "start")
check("failure 25 hours ago -> start", wr.decide(old_fail, NOW, False, False) == "start")
check("manual retry still honours a live lock", wr.decide(fresh_fail, NOW, False, True, force=True) == "busy")

# ---- describe --------------------------------------------------------------------------------------
check("describe present + native", wr.describe({}, NOW, True, False, True)["status"] == "ok")
check("describe present, tab -> says to restart", "again" in wr.describe({}, NOW, True, False, False)["detail"])
check("describe lock alive -> installing", wr.describe({}, NOW, False, True, False)["status"] == "installing")
d = wr.describe({"status": "failed", "at": NOW - 3600, "reason": "URLError: offline"}, NOW, False, False, False)
check("describe failed carries the reason and a wait", d["status"] == "failed" and "offline" in d["detail"] and d["retry_in"] == 23 * 3600, d)
check("describe empty state -> missing", wr.describe({}, NOW, False, False, False)["status"] == "missing")

# ---- state file ------------------------------------------------------------------------------------
sp = TMP / "cache" / "webview2.json"
check("missing state file -> {}", wr.read_state(sp) == {})
wr.write_state("failed", "boom", 7, now=NOW, path=sp)
st = wr.read_state(sp)
check("state round-trips", st["status"] == "failed" and st["reason"] == "boom" and st["exit_code"] == 7 and st["at"] == NOW, st)
sp.write_text("{not json", encoding="utf-8")
check("corrupt state file -> {}", wr.read_state(sp) == {})
sp.write_text("[1, 2]", encoding="utf-8")
check("state file with the wrong shape -> {}", wr.read_state(sp) == {})

# ---- lock ------------------------------------------------------------------------------------------
lk = TMP / "arti-webview2.lock"
check("no lock file -> not alive", not wr.lock_alive(lk, time.time()))
fd1 = wr._take_lock(lk, time.time())
check("first taker gets the lock", fd1 is not None and lk.exists())
check("second taker is refused while it is alive", wr._take_lock(lk, time.time()) is None)
os.close(fd1)
old = time.time() - 21 * 60
os.utime(lk, (old, old))
check("a lock older than 20 minutes is dead", not wr.lock_alive(lk, time.time()))
fd2 = wr._take_lock(lk, time.time())
check("a dead lock is replaced", fd2 is not None)
os.close(fd2)
lk.unlink()

# ---- maybe_start_install -----------------------------------------------------------------------------
started = []


class FakeThread:
    def __init__(self, target=None, name=None, daemon=None):
        started.append(name)

    def start(self):
        pass


real = (wr.threading.Thread, wr.runtime_present, wr.read_state, wr.lock_alive)
wr.threading.Thread = FakeThread
try:
    wr.lock_alive = lambda path, now: False
    wr.runtime_present = lambda *a, **k: True
    wr.read_state = lambda *a, **k: {}
    v = wr.maybe_start_install() if sys.platform == "win32" else "unsupported"
    check("present -> nothing started", started == [] and v in ("present", "unsupported"), (v, started))
    if sys.platform == "win32":
        wr.runtime_present = lambda *a, **k: False
        wr.read_state = lambda *a, **k: {"status": "failed", "at": time.time() - 60}
        v = wr.maybe_start_install()
        check("recent failure -> wait, nothing started", v == "wait" and started == [], (v, started))
        v = wr.maybe_start_install(force=True)
        check("manual retry -> exactly one install thread", v == "start" and started == ["webview2-install"], (v, started))
finally:
    wr.threading.Thread, wr.runtime_present, wr.read_state, wr.lock_alive = real

print("\n%d of %d checks passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
