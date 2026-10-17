"""arti-license: client side of ARTi licensing.

    cli.py activate KEY            bind this machine and write ~/.arti/license.json
    cli.py status [--refresh]      show the local license (--refresh re-validates online first)
    cli.py deactivate              free this machine's seat (a seat held by another computer is freed by support only)
    cli.py install-file PATH       install a signed license file (site / offline)
    cli.py verify [--file PATH] [--now ISO]   offline check; exit 0 valid/grace, 1 expired, 2 invalid

API base: ARTI_LICENSE_API, else config.json. A mistyped key is rejected locally (checksum) before
any network call. Offline checks never need the network; a Worker outage never stops a licensed install.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "_shared"))
import license as lic  # noqa: E402
try:  # the license check gates the dashboard: a missing TLS helper must not take it down
    from tls import use_certifi_bundle  # noqa: E402
    use_certifi_bundle()  # arti-update's download and update check call this module's post(), so they are covered too
except ImportError:
    pass

MESSAGES = {
    "seat_limit": "This key is already active on another computer and every seat is in use. Deactivate it on that computer "
                  "(Settings > License there), or contact support to move it.",
    "key_revoked": "This license was revoked. Contact support.",
    "expired": "This license has expired and is not renewed yet. Once your renewal is processed, refresh the status and the new "
               "date appears. Your data and installed version keep working.",
    "not_found": "No such license key, or this computer is not activated under it.",
    "not_entitled": "This computer is not activated under that license. Activate it with your key.",
    "rate_limited": "Too many requests. Wait a minute and try again.",
    "bad_checksum": "That key has a typo. Check it and try again.",
    "unreachable": "Cannot reach the licensing server. Check the internet connection. Existing licenses keep working offline.",
}
REVOKED_TEXT = ("REVOKED: this license was revoked. The dashboard is locked; skills, tools and Claude Code keep working. "
                "Contact support, or run 'activate' with a different key.")


def message_for(e):
    """Plain text for an ApiFailure. The server's own wording wins for rate_limited, because that one code
    covers both a request burst and the yearly self-service deactivation cap ("contact support")."""
    if e.code == "rate_limited" and str(e) and str(e) != "HTTP 429":
        text = str(e)
        return text[0].upper() + text[1:] + ("" if text.endswith(".") else ".")
    return MESSAGES.get(e.code, str(e))


def api_base():
    env = os.environ.get("ARTI_LICENSE_API")
    if env:
        return env.rstrip("/")
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        return json.load(f)["api_base"].rstrip("/")


class ApiFailure(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def post(path, body, timeout=15):
    req = urllib.request.Request(api_base() + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "arti-license/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e)
        except ValueError:
            err = {}
        raise ApiFailure(err.get("code", "server_error"), err.get("message", "HTTP %s" % e.code))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise ApiFailure("unreachable", "Cannot reach the licensing server (%s). Existing licenses keep working offline." % getattr(e, "reason", e))


def fail(e):
    print("error [%s]: %s" % (e.code, message_for(e)), file=sys.stderr)
    return 1


def need_key(raw):
    body = lic.check_key(raw)
    if body is None:
        print("error [bad_checksum]: %s" % MESSAGES["bad_checksum"], file=sys.stderr)
        return None
    return lic.format_key(body)


def describe(info):
    if info["state"] == "invalid":
        return "INVALID (%s)" % info["reason"]
    s = "%s  tier=%s  licensed to=%s  key_id=%s\n  expires %s, updates until %s" % (
        info["state"].upper(), info["tier"], info["name"], info["key_id"], info["expires"], info["updates_until"])
    if info["state"] == "grace":
        s += "\n  in offline grace until %s - renew or go online" % info["grace_ends"]
    if info["state"] == "expired":
        s += "\n  past grace: no updates, tools stay usable, data untouched"
    return s


def activate_key(raw_key):
    """Bind this machine to a key and write license.json. Returns the evaluated info.
    Raises ApiFailure (codes as in MESSAGES) - shared by the CLI and the dashboard server."""
    body = lic.check_key(raw_key)
    if body is None:
        raise ApiFailure("bad_checksum", MESSAGES["bad_checksum"])
    r = post("/activate", {"key": lic.format_key(body), "machine_hash": lic.machine_hash(), "label": lic.machine_label()})
    info = lic.evaluate(r["license"])
    if info["state"] == "invalid":
        raise ApiFailure("server_error", "The server returned a license this client rejects (%s)." % info["reason"])
    lic.write_license(r["license"])
    _clear_revoked()
    info["seats_used"] = r.get("seats_used")
    return info


def _clear_revoked():
    try:
        os.remove(lic.revoked_path())
    except FileNotFoundError:
        pass


def is_revoked():
    """True when no usable license.json exists but one was set aside as revoked."""
    return not os.path.exists(lic.license_path()) and os.path.exists(lic.revoked_path())


def mark_revoked():
    """The server said key_revoked: set license.json aside as license.revoked.json. The dashboard then shows
    'revoked' (locked) instead of 'missing', and nothing re-activates that key on its own. Skills and tools
    never read this file. The aside copy stays a valid signed credential, so recheck_revoked() can restore it
    if the server later undoes the revoke."""
    try:
        os.replace(lic.license_path(), lic.revoked_path())
    except FileNotFoundError:
        pass


def refresh_license(timeout=15):
    """Re-validate the local license online and store the renewed copy. Returns the evaluated info.
    Raises ApiFailure (e.g. unreachable, key_revoked); FileNotFoundError if nothing is installed.
    A key_revoked answer sets the license aside (mark_revoked) before it is raised."""
    cur = lic.read_license()
    try:
        r = post("/validate", {"license": cur, "machine_hash": lic.machine_hash()}, timeout=timeout)
    except ApiFailure as e:
        if e.code == "key_revoked":
            mark_revoked()
        raise
    info = lic.evaluate(r["license"])
    if info["state"] != "invalid":
        lic.write_license(r["license"])
    return info


def recheck_revoked():
    """Ask again about a license set aside as revoked. Restores it when the server no longer revokes it;
    raises ApiFailure(key_revoked) otherwise. FileNotFoundError if nothing was set aside."""
    cur = lic.read_license(lic.revoked_path())
    r = post("/validate", {"license": cur, "machine_hash": lic.machine_hash()})
    info = lic.evaluate(r["license"])
    if info["state"] == "invalid":
        raise ApiFailure("server_error", "The server returned a license this client rejects (%s)." % info["reason"])
    lic.write_license(r["license"])
    _clear_revoked()
    return info


def deactivate_local():
    """Free this machine's seat online, then delete the local license file."""
    cur = lic.read_license()
    post("/deactivate", {"machine_hash": lic.machine_hash(), "license": cur})
    try:
        os.remove(lic.license_path())
    except FileNotFoundError:
        pass


def cmd_activate(a):
    key = need_key(a.key)
    if key is None:
        return 1
    try:
        r = post("/activate", {"key": key, "machine_hash": lic.machine_hash(), "label": lic.machine_label()})
    except ApiFailure as e:
        return fail(e)
    info = lic.evaluate(r["license"])
    if info["state"] == "invalid":
        print("error: server returned a license this client rejects (%s)" % info["reason"], file=sys.stderr)
        return 2
    lic.write_license(r["license"])
    _clear_revoked()
    print("Activated (%s seat(s) used).\n%s" % (r.get("seats_used"), describe(info)))
    return 0


def cmd_status(a):
    try:
        cur = lic.read_license()
    except FileNotFoundError:
        if is_revoked():
            print(REVOKED_TEXT)
            return 2
        print("No license installed. Run 'arti-license activate KEY'.")
        return 1
    if a.refresh:
        try:
            refresh_license()
            cur = lic.read_license()
            print("(refreshed online)")
        except ApiFailure as e:
            print("(could not refresh: [%s] %s)" % (e.code, message_for(e)), file=sys.stderr)
            if e.code == "key_revoked":
                print(REVOKED_TEXT)
                return 2
    info = lic.evaluate(cur)
    print(describe(info))
    return 0 if info["state"] in ("valid", "grace") else (1 if info["state"] == "expired" else 2)


def cmd_deactivate(a):
    try:
        cur = lic.read_license()
    except FileNotFoundError:
        print("No local license to deactivate.", file=sys.stderr)
        return 1
    try:
        post("/deactivate", {"machine_hash": lic.machine_hash(), "license": cur})
    except ApiFailure as e:
        return fail(e)
    try:
        os.remove(lic.license_path())
    except FileNotFoundError:
        pass
    print("Deactivated.")
    return 0


def cmd_install_file(a):
    with open(a.path, encoding="utf-8") as f:
        new = json.load(f)
    info = lic.evaluate(new)
    if info["state"] == "invalid":
        print("Rejected: %s" % describe(info), file=sys.stderr)
        return 2
    lic.write_license(new)
    print("Installed.\n" + describe(info))
    return 0


def cmd_verify(a):
    now = lic.parse_time(a.now) if a.now else None
    if not a.file and is_revoked():
        print(REVOKED_TEXT)
        return 2
    try:
        cur = lic.read_license(a.file)
    except (OSError, ValueError) as e:
        print("INVALID (unreadable: %s)" % e)
        return 2
    info = lic.evaluate(cur, now=now)
    print(describe(info))
    return {"valid": 0, "grace": 0, "expired": 1}.get(info["state"], 2)


def main(argv=None):
    for st in (sys.stdout, sys.stderr):
        st.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(prog="arti-license")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("activate"); p.add_argument("key")
    p = sub.add_parser("status"); p.add_argument("--refresh", action="store_true")
    sub.add_parser("deactivate")
    p = sub.add_parser("install-file"); p.add_argument("path")
    p = sub.add_parser("verify"); p.add_argument("--file"); p.add_argument("--now", help="ISO UTC time, e.g. 2027-01-01T00:00:00Z")
    a = ap.parse_args(argv)
    return globals()["cmd_" + a.cmd.replace("-", "_")](a)


if __name__ == "__main__":
    sys.exit(main())
