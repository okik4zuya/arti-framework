"""WebView2 Runtime for the dashboard's native window (Windows): detection, a one-time background install when it is
missing, and the small state file behind the banner in the browser-tab fallback and the Settings > System line.

The install uses the same lock file as install.ps1 (%TEMP%\\arti-webview2.lock, a lock older than 20 minutes is dead),
so the installer's own background install and this one never run twice at the same time. After a failure the
dashboard does not try again by itself for 24 hours; the banner's Retry button (force=True) skips that wait but
still honours the lock. Everything that decides something is a plain function of its arguments (see
tests/webview2/test_webview2_runtime.py); the network and the registry are only touched in the thin wrappers.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ARTI_HOME = Path(__file__).resolve().parent.parent.parent
CLIENT_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
BOOTSTRAPPER_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
MANUAL_URL = BOOTSTRAPPER_URL
STATE_PATH = ARTI_HOME / ".cache" / "webview2.json"      # .cache is git-ignored, per machine
LOCK_NAME = "arti-webview2.lock"
RETRY_AFTER_FAILURE = 24 * 3600     # seconds before an automatic second try
STALE_AFTER = 20 * 60               # a lock or an "installing" mark older than this is dead (same as install.ps1)
INSTALL_TIMEOUT = 20 * 60


# ---- detection ------------------------------------------------------------------------------------

def registered_versions():
    """[(base_dir, version)] for every place the Evergreen Runtime's registry entry can point at."""
    if sys.platform != "win32":
        return []
    import winreg
    roots = (
        (winreg.HKEY_LOCAL_MACHINE, os.environ.get("ProgramFiles(x86)")),
        (winreg.HKEY_LOCAL_MACHINE, os.environ.get("ProgramFiles")),
        (winreg.HKEY_CURRENT_USER, os.environ.get("LocalAppData")),
    )
    subkeys = (r"SOFTWARE\Microsoft\EdgeUpdate\Clients\%s" % CLIENT_GUID,
               r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\%s" % CLIENT_GUID)
    found = []
    for hive, base_dir in roots:
        if not base_dir:
            continue
        for sub in subkeys:
            try:
                with winreg.OpenKey(hive, sub) as key:
                    version, _ = winreg.QueryValueEx(key, "pv")
            except OSError:
                continue
            if version:
                found.append((base_dir, version))
                break
    return found


def can_open(path):
    """True when the file can really be opened. Not Path.exists(): the Windows Sandbox base image lists a
    msedgewebview2.exe that exists in a directory listing but cannot be opened."""
    try:
        with open(path, "rb"):
            return True
    except OSError:
        return False


def runtime_present(registered=None, opener=can_open):
    """The registry alone is not enough (servicing metadata can outlive the binary): read the registered version,
    then confirm the binary at the version-specific path opens."""
    for base_dir, version in (registered_versions() if registered is None else registered):
        exe = Path(base_dir) / "Microsoft" / "EdgeWebView" / "Application" / version / "msedgewebview2.exe"
        if opener(exe):
            return True
    return False


# ---- state ----------------------------------------------------------------------------------------

def lock_path():
    return Path(os.environ.get("TEMP") or tempfile.gettempdir()) / LOCK_NAME


def lock_alive(path, now):
    try:
        return now - path.stat().st_mtime < STALE_AFTER
    except OSError:
        return False


def read_state(path=STATE_PATH):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(status, reason="", exit_code=None, now=None, path=STATE_PATH):
    state = {"status": status, "at": time.time() if now is None else now, "reason": reason, "exit_code": exit_code}
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        pass
    return state


def decide(state, now, present, lock_is_alive, force=False):
    """What to do about a missing runtime: 'present' (nothing), 'busy' (an install is running, ours or the
    installer's), 'wait' (it failed less than 24 hours ago and this is not a manual retry), or 'start'."""
    if present:
        return "present"
    if lock_is_alive:
        return "busy"
    state = state or {}
    age = now - float(state.get("at") or 0)
    if state.get("status") == "installing" and age < STALE_AFTER:
        return "busy"
    if state.get("status") == "failed" and not force and age < RETRY_AFTER_FAILURE:
        return "wait"
    return "start"


def describe(state, now, present, lock_is_alive, native):
    """What the banner and the Settings line show. status: ok | installing | failed | missing."""
    state = state or {}
    age = now - float(state.get("at") or 0)
    if present:
        if native:
            return {"status": "ok", "detail": "installed; the native window is in use"}
        return {"status": "ok", "detail": "installed; close ARTi and open it again to get the native window"}
    if lock_is_alive or (state.get("status") == "installing" and age < STALE_AFTER):
        return {"status": "installing", "detail": "downloading and installing (about 150 MB, a slow connection can take 10 minutes or more)"}
    if state.get("status") == "failed":
        reason = state.get("reason") or "unknown reason"
        wait = max(0, int(RETRY_AFTER_FAILURE - age))
        return {"status": "failed", "detail": "not installed: %s" % reason, "retry_in": wait}
    return {"status": "missing", "detail": "not installed"}


def status(now=None, native=False):
    now = time.time() if now is None else now
    present = runtime_present()
    out = describe(read_state(), now, present, lock_alive(lock_path(), now), native)
    out.update(present=present, native=bool(native), windows=sys.platform == "win32", manual_url=MANUAL_URL)
    return out


# ---- the install ----------------------------------------------------------------------------------

def _take_lock(path, now):
    """Create the lock exclusively; returns the open descriptor, or None when another install holds it."""
    for _ in range(2):
        try:
            return os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if lock_alive(path, now):
                return None
            try:
                os.remove(str(path))        # dead lock (older than 20 minutes)
            except OSError:
                return None
        except OSError:
            return None
    return None


def _download(url, dest):
    try:
        sys.path.insert(0, str(ARTI_HOME / "tools" / "_shared"))
        from tls import use_certifi_bundle
        use_certifi_bundle()
    except Exception:
        pass
    import urllib.request
    with urllib.request.urlopen(url, timeout=60) as resp, open(dest, "wb") as out:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)


def _run_install(url=BOOTSTRAPPER_URL):
    now = time.time()
    path = lock_path()
    fd = _take_lock(path, now)
    if fd is None:
        return
    exe = Path(os.environ.get("TEMP") or tempfile.gettempdir()) / "MicrosoftEdgeWebView2Setup.exe"
    try:
        write_state("installing")
        _download(url, exe)
        # No admin needed: the bootstrapper falls back to a per-user install by itself.
        proc = subprocess.run([str(exe), "/silent", "/install"], timeout=INSTALL_TIMEOUT,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if proc.returncode != 0:
            write_state("failed", "the Microsoft installer exited with code %s" % proc.returncode, proc.returncode)
        elif not runtime_present():
            write_state("failed", "the Microsoft installer finished, but the runtime is still not there", 0)
        else:
            write_state("ok")
    except Exception as e:      # offline, blocked, timed out ...
        write_state("failed", "%s: %s" % (type(e).__name__, e))
    finally:
        try:
            exe.unlink()
        except OSError:
            pass
        try:
            os.close(fd)
            os.remove(str(path))
        except OSError:
            pass


def maybe_start_install(force=False):
    """Start the background install when it is allowed (see decide). Returns the decision. Windows only."""
    if sys.platform != "win32":
        return "unsupported"
    now = time.time()
    verdict = decide(read_state(), now, runtime_present(), lock_alive(lock_path(), now), force)
    if verdict == "start":
        threading.Thread(target=_run_install, name="webview2-install", daemon=True).start()
    return verdict
