"""arti-update: look for a newer ARTi release, download it and put it in place (phase 3b), or go back.

    cli.py check [--force]     ask the licensing server (about every 2 days unless --force) and print the result
    cli.py status              print what the last check found (no network)
    cli.py ack VERSION         record that you read the release notes of VERSION
    cli.py download VERSION    fetch the bundle into .update/download (resumable; sha256 and size checked)
    cli.py apply VERSION       download if needed, then hand over to updater.py (needs ack; close the ARTi window first)
    cli.py rollback [VERSION]  put a saved earlier version back (default: the newest saved one)
    cli.py result [--clear]    print the outcome of the last apply/rollback

The server answers with the newest release this license may install (released on or before its
`updates_until`) as a document signed offline with the release key; this client verifies the signature
against tools/arti-license/pubkeys.json before believing a word of it. The bundle is only used when its
size and sha256 match that signed manifest, and updater.py checks everything again in its own process.
State lives in .update/ under ARTI_HOME (git-ignored); ARTI_CODE_HOME points the swap at another code tree
(tests only).
"""
import argparse
import http.client
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "_shared"))
import license as lic  # noqa: E402
sys.path.insert(0, HERE)
import bundle as bundle_rules  # noqa: E402

CHECK_EVERY_S = 2 * 24 * 3600   # the update check is also the license heartbeat (revoke, renewal), +-1 h jitter

# The license messages say "no such license key" for not_found, which is wrong for an update check.
UPDATE_MESSAGES = {
    "not_found": "The licensing server does not offer updates yet. Try again later.",
    "not_entitled": "This computer is not activated for this license. Activate it in Settings > License.",
}


def _license_cli():
    spec = importlib.util.spec_from_file_location("arti_license_cli", os.path.join(HERE, "..", "arti-license", "cli.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def code_home():
    return os.path.abspath(os.environ.get("ARTI_CODE_HOME") or os.path.join(HERE, "..", ".."))


def state_path():
    return os.path.join(lic.ARTI_HOME, ".update", "state.json")


def current_version():
    try:
        with open(os.path.join(code_home(), "VERSION"), encoding="utf-8") as f:
            for line in f:
                if line.startswith("FRAMEWORK_VERSION="):
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return "0.0.0"


def parse_version(s):
    try:
        return tuple(int(p) for p in str(s).split("."))
    except ValueError:
        return (0,)


def now_iso():
    return lic.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def read_state():
    try:
        with open(state_path(), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def write_state(state):
    path = state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def is_due(state=None):
    state = read_state() if state is None else state
    try:
        age = (lic.utcnow() - lic.parse_time(state["checked_at"])).total_seconds()
    except (KeyError, ValueError, TypeError):
        return True
    return age >= lic.jittered(CHECK_EVERY_S) or state.get("current") != current_version()


def verify_release(doc):
    """Return the manifest if the document is signed by a known release key and well formed, else None."""
    try:
        manifest, sig, kid = doc["manifest"], doc["sig"], doc["kid"]
        pub = lic.load_pubkeys().get("release", {}).get(kid)
        if pub is None or not lic.verify_signature(manifest, sig, pub):
            return None
        if not isinstance(manifest["version"], str) or not isinstance(manifest["notes"], str):
            return None
        return manifest
    except (KeyError, TypeError):
        return None


def summarize(manifest):
    out = {k: manifest.get(k) for k in ("version", "released", "channel", "notes", "skills_changed",
                                         "min_client_version", "requires_installer", "download_page", "packs")}
    b = manifest.get("bundle")
    out["bundle"] = {"size": b.get("size"), "sha256": b.get("sha256"), "items": b.get("items")} if isinstance(b, dict) else None
    return out


def check(force=False, channel=None):
    """Ask the server and store the result. Returns the new state. Never raises on network trouble."""
    state = read_state()
    current = current_version()
    if not force and not is_due(state):
        return state
    same = state.get("current") == current
    new = {"checked_at": state.get("checked_at"), "attempted_at": now_iso(), "current": current,
           "available": state.get("available") if same else None,
           "available_doc": state.get("available_doc") if same else None,   # the signed document, kept for download/apply
           "locked_newer": state.get("locked_newer") if same else None,
           "acked": state.get("acked"), "error": None}
    cli = _license_cli()
    try:
        cur = lic.read_license()
    except (OSError, ValueError):
        new["error"] = {"code": "not_activated", "message": "No license is installed on this computer."}
        write_state(new)
        return new
    channel = channel or os.environ.get("ARTI_UPDATE_CHANNEL") or "stable"
    try:
        r = cli.post("/update", {"license": cur, "machine_hash": lic.machine_hash(), "channel": channel, "version": current})
    except cli.ApiFailure as e:
        if e.code == "key_revoked":
            cli.mark_revoked()  # the update check is a free second signal that the license was revoked
        new["error"] = {"code": e.code, "message": UPDATE_MESSAGES.get(e.code) or cli.message_for(e)}
        write_state(new)
        return new
    if r.get("license"):  # a renewal: the server's dates changed, so the answer carries the new signed license
        renewed = lic.evaluate(r["license"])
        if renewed["state"] != "invalid":
            lic.write_license(r["license"])
    lic.write_check(confirmed_at=time.time())  # the server stands behind this license (not revoked)
    manifest = None
    if r.get("release"):
        manifest = verify_release(r["release"])
        if manifest is None:
            new["error"] = {"code": "bad_manifest", "message": "The update information could not be verified and was ignored."}
            new["available"] = None
            new["available_doc"] = None
    if new["error"] is None:
        new["checked_at"] = now_iso()
    if manifest is not None:
        newer = parse_version(manifest["version"]) > parse_version(current)
        new["available"] = summarize(manifest) if newer else None
        new["available_doc"] = r["release"] if newer else None
        if newer and parse_version(manifest.get("min_client_version", "0.0.0")) > parse_version(current):
            new["available"]["requires_installer"] = True
    elif new["error"] is None:
        new["available"] = None
        new["available_doc"] = None
    locked = r.get("locked_newer")
    new["locked_newer"] = locked if locked and parse_version(locked.get("version")) > parse_version(current) else None
    write_state(new)
    return new


def ack(version):
    """Record that the notes of `version` were read. Returns (ok, state). The server copy is best effort."""
    state = read_state()
    avail = state.get("available") or {}
    if avail.get("version") != version:
        return False, state
    state["acked"] = version
    write_state(state)
    try:
        cli = _license_cli()
        cli.post("/ack", {"license": lic.read_license(), "machine_hash": lic.machine_hash(), "version": version})
    except Exception:
        pass
    return True, state


# ---- phase 3b: download, apply, rollback ----------------------------------------------------------

DASHBOARD_PING = "http://127.0.0.1:4174/api/ping"
APPLY_MESSAGES = {
    "not_acked": "Confirm that you read the release notes first.",
    "no_update": "There is no pending update with that version.",
    "requires_installer": "This release changes the runtime and needs the full installer.",
    "no_bundle": "This release has no in-app update. Use the installer.",
    "bad_manifest": "The update information could not be verified and was ignored.",
    "revoked": "This license was revoked. Updates are off.",
    "license": "The license on this computer is not valid, so updates are off.",
    "not_entitled": "Your license does not cover this release.",
    "dashboard_running": "The ARTi window is open. Close it first, or use Update now inside it.",
    "bad_download": "The download did not match the signed release and was thrown away. Nothing was changed.",
    "unreachable": "Cannot reach the licensing server. Check the internet connection and try again.",
    "busy": "An update is already running.",
    "no_backup": "There is no saved earlier version to go back to.",
}


class UpdateFailure(Exception):
    def __init__(self, code, message=None):
        super().__init__(message or APPLY_MESSAGES.get(code, code))
        self.code = code


def home():
    return lic.ARTI_HOME


def update_dir(*p):
    return os.path.join(home(), ".update", *p)


def backup_dir():
    return os.path.join(home(), ".backup")


def list_backups():
    """Saved earlier versions (newest first), each a folder .backup/<version>/ made by updater.py."""
    try:
        names = [d for d in os.listdir(backup_dir()) if os.path.isdir(os.path.join(backup_dir(), d))
                 and parse_version(d) != (0,) and d != current_version()]
    except OSError:
        return []
    return sorted(names, key=parse_version, reverse=True)


def read_result(consume=False):
    path = update_dir("result.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if consume:
        try:
            os.remove(path)
        except OSError:
            pass
    return data


def read_progress():
    try:
        with open(update_dir("progress.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _manifest_for(state, version):
    """The verified manifest of the pending release `version`, or an UpdateFailure."""
    avail = state.get("available") or {}
    if avail.get("version") != version:
        raise UpdateFailure("no_update")
    manifest = verify_release(state.get("available_doc") or {})
    if manifest is None or manifest.get("version") != version:
        raise UpdateFailure("bad_manifest")
    return manifest


def _check_bundle(manifest):
    b = manifest.get("bundle")
    if (not isinstance(b, dict) or not isinstance(b.get("sha256"), str) or not isinstance(b.get("size"), int)
            or not isinstance(b.get("items"), list) or not b.get("r2_key")
            or not set(b["items"]) <= set(bundle_rules.UPDATE_ITEMS) or "VERSION" not in b["items"]):
        raise UpdateFailure("no_bundle")


def preflight(version, state=None):
    """Everything that must be true before anything is downloaded or changed. Returns the verified manifest."""
    state = read_state() if state is None else state
    manifest = _manifest_for(state, version)
    if manifest.get("requires_installer") or (state.get("available") or {}).get("requires_installer"):
        raise UpdateFailure("requires_installer")
    _check_bundle(manifest)
    if state.get("acked") != version:
        raise UpdateFailure("not_acked")
    if parse_version(version) <= parse_version(current_version()):
        raise UpdateFailure("no_update")
    cli = _license_cli()
    try:
        cur = lic.read_license()
    except FileNotFoundError:
        raise UpdateFailure("revoked" if cli.is_revoked() else "license")
    except (OSError, ValueError):
        raise UpdateFailure("license")
    info = lic.evaluate(cur)
    if info["state"] == "invalid":
        raise UpdateFailure("license")
    if not lic.entitled_to_release(info, manifest["released"]):
        raise UpdateFailure("not_entitled")
    return manifest


def _api_error(cli, e):
    if e.code == "key_revoked":
        cli.mark_revoked()
        return UpdateFailure("revoked")
    return UpdateFailure(e.code, UPDATE_MESSAGES.get(e.code) or cli.message_for(e))


def download(version, progress=None, attempts=3, retry_wait=2.0, timeout=30):
    """Fetch the bundle of the pending release into .update/download. Resumes a partial file with a Range request,
    retries a dropped connection, and only keeps the file when its size and sha256 equal the signed manifest.
    progress(done, total) is called as bytes arrive. Returns the path."""
    manifest = preflight(version)
    b = manifest["bundle"]
    folder = update_dir("download")
    os.makedirs(folder, exist_ok=True)
    final = os.path.join(folder, "arti-%s.zip" % version)
    part = final + ".part"
    if os.path.isfile(final):
        if os.path.getsize(final) == b["size"] and bundle_rules.sha256_file(final) == b["sha256"]:
            if progress:
                progress(b["size"], b["size"])
            return final
        os.remove(final)
    cli = _license_cli()
    body = json.dumps({"license": lic.read_license(), "machine_hash": lic.machine_hash(), "version": version}).encode()
    last = None
    for attempt in range(attempts):
        have = os.path.getsize(part) if os.path.exists(part) else 0
        if have > b["size"]:
            os.remove(part)
            have = 0
        if have < b["size"]:
            headers = {"Content-Type": "application/json", "User-Agent": "arti-update/1.0"}
            if have:
                headers["Range"] = "bytes=%d-" % have
            req = urllib.request.Request(cli.api_base() + "/download", data=body, method="POST", headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 206:
                        start = int((resp.headers.get("Content-Range") or "bytes 0-").split()[-1].split("-")[0])
                        if start != have:
                            raise OSError("server resumed at the wrong byte")
                        mode = "ab"
                    else:
                        have, mode = 0, "wb"
                    with open(part, mode) as out:
                        while True:
                            chunk = resp.read(64 * 1024)
                            if not chunk:
                                break
                            out.write(chunk)
                            have += len(chunk)
                            if progress:
                                progress(have, b["size"])
            except urllib.error.HTTPError as e:
                try:
                    err = json.load(e)
                except ValueError:
                    err = {}
                code = err.get("code", "server_error")
                if e.code == 416 and have:   # the partial file does not fit the object any more: start over
                    os.remove(part)
                    continue
                if e.code < 500:
                    raise _api_error(cli, cli.ApiFailure(code, err.get("message", "HTTP %s" % e.code)))
                last = UpdateFailure(code, err.get("message", "The server had a problem."))
            except (urllib.error.URLError, http.client.HTTPException, OSError, TimeoutError) as e:
                last = UpdateFailure("unreachable", "%s (%s)" % (APPLY_MESSAGES["unreachable"], getattr(e, "reason", e)))
        if os.path.exists(part) and os.path.getsize(part) == b["size"]:
            break
        if attempt + 1 < attempts:
            time.sleep(retry_wait)
    if not os.path.exists(part) or os.path.getsize(part) != b["size"]:
        raise last or UpdateFailure("unreachable")
    if bundle_rules.sha256_file(part) != b["sha256"]:
        os.remove(part)
        raise UpdateFailure("bad_download")
    os.replace(part, final)
    return final


def _python_exe():
    exe = sys.executable
    if os.path.basename(exe).lower() == "pythonw.exe":
        sibling = os.path.join(os.path.dirname(exe), "python.exe")
        if os.path.exists(sibling):
            return sibling
    return exe


def dashboard_options(pid=0):
    """How updater.py should stop and start the dashboard. pid 0: nothing to stop or restart (CLI use)."""
    code = code_home()
    opts = {"pid": pid, "smoke": [_python_exe(), os.path.join(code, "tools", "arti-update", "cli.py"), "status"]}
    if pid:
        if sys.platform == "win32":
            pyw = os.path.join(code, "python", "pythonw.exe")
            opts["relaunch"] = [pyw if os.path.exists(pyw) else sys.executable, os.path.join(code, "dashboard", "app.py")]
        else:
            opts["relaunch"] = ["bash", os.path.join(code, "dashboard", "start-arti-framework-hidden.sh")]
        opts["relaunch_cwd"] = os.path.join(code, "dashboard")
        opts["ping_url"] = DASHBOARD_PING
    return opts


def _spawn_updater(args, opts):
    """Copy the updater and what it imports to .update/run and start it as a detached process."""
    run = update_dir("run")
    shutil.rmtree(run, ignore_errors=True)
    os.makedirs(run)
    for src in (os.path.join(HERE, "updater.py"), os.path.join(HERE, "bundle.py"),
                os.path.join(HERE, "..", "_shared", "license.py"), os.path.join(HERE, "..", "_shared", "paths.py")):
        shutil.copy2(src, run)
    shutil.copyfile(lic.PUBKEYS_PATH, os.path.join(run, "pubkeys.json"))
    for stale in ("progress.json", "result.json"):
        try:
            os.remove(update_dir(stale))
        except OSError:
            pass
    cmd = [_python_exe(), os.path.join(run, "updater.py"), "--home", home(), "--code", code_home()] + args
    if opts.get("pid"):
        cmd += ["--pid", str(opts["pid"])]
    if opts.get("relaunch"):
        cmd += ["--relaunch-json", json.dumps(opts["relaunch"]), "--relaunch-cwd", opts.get("relaunch_cwd") or ""]
    for key, flag in (("ping_url", "--ping-url"), ("claude_skills", "--claude-skills")):
        if opts.get(key):
            cmd += [flag, opts[key]]
    if opts.get("smoke"):
        cmd += ["--smoke-json", json.dumps(opts["smoke"])]
    for key, flag in (("wait_s", "--wait-s"), ("health_s", "--health-s")):
        if opts.get(key) is not None:
            cmd += [flag, str(opts[key])]
    kw = {}
    if sys.platform == "win32":
        base = 0x00000008 | 0x00000200 | 0x08000000   # DETACHED_PROCESS | NEW_PROCESS_GROUP | NO_WINDOW
        kw["creationflags"] = base | 0x01000000      # CREATE_BREAKAWAY_FROM_JOB: survive the dashboard's job object
    else:
        kw["start_new_session"] = True
    log_path = update_dir("updater.out")
    out = open(log_path, "ab")
    try:
        try:
            return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=out, close_fds=True, **kw)
        except OSError:
            if sys.platform == "win32":   # the job does not allow breakaway: run without it
                kw["creationflags"] = base
                return subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=out, close_fds=True, **kw)
            raise
    finally:
        out.close()


def apply(version, opts=None, progress=None):
    """Download if needed and hand over to updater.py. Returns the started process; the outcome is in
    .update/result.json. Raises UpdateFailure before anything on disk changes."""
    manifest = preflight(version)
    opts = dashboard_options() if opts is None else opts
    if not opts.get("pid"):
        try:
            with urllib.request.urlopen(DASHBOARD_PING, timeout=1):
                raise UpdateFailure("dashboard_running")
        except (urllib.error.URLError, OSError, ValueError):
            pass
    zip_path = download(version, progress=progress)
    doc_path = update_dir("download", "arti-%s.manifest.json" % version)
    with open(doc_path, "w", encoding="utf-8") as f:
        json.dump(read_state()["available_doc"], f)
    return _spawn_updater(["--zip", zip_path, "--doc", doc_path, "--version", version, "--from", current_version()], opts)


def rollback(version=None, opts=None):
    """Put a saved earlier version back (code only; the database is not touched). Returns the started process."""
    saved = list_backups()
    version = version or (saved[0] if saved else None)
    if version is None or version not in saved:
        raise UpdateFailure("no_backup")
    opts = dashboard_options() if opts is None else opts
    if not opts.get("pid"):
        try:
            with urllib.request.urlopen(DASHBOARD_PING, timeout=1):
                raise UpdateFailure("dashboard_running")
        except (urllib.error.URLError, OSError, ValueError):
            pass
    return _spawn_updater(["--rollback", version], opts)


def wait_for_result(proc, timeout=300, say=print):
    """CLI helper: follow progress.json until the updater has written its result."""
    last = None
    deadline = time.time() + timeout
    while time.time() < deadline:
        prog = read_progress() or {}
        if prog.get("phase") != last and prog.get("phase"):
            last = prog["phase"]
            say("  ... " + last)
        res = read_result()
        if res is not None and proc.poll() is not None:
            return res
        if proc.poll() is not None and res is None:
            time.sleep(0.5)
            res = read_result()
            return res or {"ok": False, "reason": "error", "message": "The updater stopped without a result. See .update/updater.log."}
        time.sleep(0.4)
    return {"ok": False, "reason": "timeout", "message": "The updater is still running. See .update/updater.log."}


def describe(state):
    if not state:
        return "No check has run yet."
    cur = state.get("current")
    if state.get("error"):
        line = "Could not check [%s]: %s" % (state["error"]["code"], state["error"]["message"])
    elif state.get("available"):
        a = state["available"]
        line = "Version %s is available (you have %s), released %s." % (a["version"], cur, a["released"][:10])
        if a.get("requires_installer"):
            line += " It needs the full installer."
        elif a.get("bundle"):
            line += " It can be updated in place."
    elif state.get("locked_newer"):
        line = "You are up to date for your license (%s). Version %s exists but is after your updates end." % (cur, state["locked_newer"]["version"])
    else:
        line = "You are up to date (%s)." % cur
    return line + ("  Last checked %s." % state["checked_at"] if state.get("checked_at") else "")


def _print_progress(done, total):
    if total:
        sys.stdout.write("\r  downloading %3d%%  (%.1f of %.1f MB)" % (done * 100 // total, done / 1048576, total / 1048576))
        sys.stdout.flush()


def _report(res):
    if res.get("ok"):
        if res.get("action") == "rollback":
            print("Rolled back from %s to %s." % (res.get("from"), res.get("to")))
        else:
            print("Updated from %s to %s." % (res.get("from"), res.get("to")))
        return 0
    print("Not applied: %s" % res.get("message"), file=sys.stderr)
    return 1


def main(argv=None):
    for st in (sys.stdout, sys.stderr):
        st.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="arti-update")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check")
    p.add_argument("--force", action="store_true")
    sub.add_parser("status")
    p = sub.add_parser("ack")
    p.add_argument("version")
    p = sub.add_parser("download")
    p.add_argument("version")
    p = sub.add_parser("apply")
    p.add_argument("version")
    p = sub.add_parser("rollback")
    p.add_argument("version", nargs="?")
    p = sub.add_parser("result")
    p.add_argument("--clear", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "check":
        st = check(force=a.force)
        print(describe(st))
        return 1 if st.get("error") else 0
    if a.cmd == "status":
        print(describe(read_state()))
        return 0
    if a.cmd == "ack":
        ok, _ = ack(a.version)
        print("Recorded." if ok else "No pending update with that version.")
        return 0 if ok else 1
    if a.cmd == "result":
        res = read_result(consume=a.clear)
        print(json.dumps(res, indent=2) if res else "No result recorded.")
        return 0 if res and res.get("ok") else 1
    try:
        if a.cmd == "download":
            path = download(a.version, progress=_print_progress)
            print("\nSaved %s" % path)
            return 0
        proc = apply(a.version, progress=_print_progress) if a.cmd == "apply" else rollback(a.version)
    except UpdateFailure as e:
        print("Not applied [%s]: %s" % (e.code, e), file=sys.stderr)
        return 1
    print("\nHanded over to the updater.")
    return _report(wait_for_result(proc))


if __name__ == "__main__":
    sys.exit(main())
