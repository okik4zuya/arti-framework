"""arti-update: look for a newer ARTi release (phase 3a: check, show the notes, record that they were read).

    cli.py check [--force]     ask the licensing server (at most once a day unless --force) and print the result
    cli.py status              print what the last check found (no network)
    cli.py ack VERSION         record that you read the release notes of VERSION

The server answers with the newest release this license may install (released on or before its
`updates_until`) as a document signed offline with the release key; this client verifies the signature
against tools/arti-license/pubkeys.json before believing a word of it. Nothing is downloaded or
changed on disk here: applying an update comes in a later phase. State lives in .update/state.json
under ARTI_HOME (git-ignored).
"""
import argparse
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "_shared"))
import license as lic  # noqa: E402

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
    return os.path.abspath(os.path.join(HERE, "..", ".."))


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
    return {k: manifest.get(k) for k in ("version", "released", "channel", "notes", "skills_changed",
                                          "min_client_version", "requires_installer", "download_page")}


def check(force=False, channel=None):
    """Ask the server and store the result. Returns the new state. Never raises on network trouble."""
    state = read_state()
    current = current_version()
    if not force and not is_due(state):
        return state
    same = state.get("current") == current
    new = {"checked_at": state.get("checked_at"), "attempted_at": now_iso(), "current": current,
           "available": state.get("available") if same else None,
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
    if new["error"] is None:
        new["checked_at"] = now_iso()
    if manifest is not None:
        newer = parse_version(manifest["version"]) > parse_version(current)
        new["available"] = summarize(manifest) if newer else None
        if newer and parse_version(manifest.get("min_client_version", "0.0.0")) > parse_version(current):
            new["available"]["requires_installer"] = True
    elif new["error"] is None:
        new["available"] = None
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
    elif state.get("locked_newer"):
        line = "You are up to date for your license (%s). Version %s exists but is after your updates end." % (cur, state["locked_newer"]["version"])
    else:
        line = "You are up to date (%s)." % cur
    return line + ("  Last checked %s." % state["checked_at"] if state.get("checked_at") else "")


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
    a = ap.parse_args(argv)
    if a.cmd == "check":
        st = check(force=a.force)
        print(describe(st))
        return 1 if st.get("error") else 0
    if a.cmd == "status":
        print(describe(read_state()))
        return 0
    ok, _ = ack(a.version)
    print("Recorded." if ok else "No pending update with that version.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
