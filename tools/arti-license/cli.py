"""arti-license: client side of ARTi licensing.

    cli.py activate KEY            bind this machine and write ~/.arti/license.json
    cli.py status [--refresh]      show the local license (--refresh re-validates online first)
    cli.py deactivate [--key KEY --machine HASH]   free this machine's seat (or another one, with the key)
    cli.py activations KEY         list the seats of a key
    cli.py trial EMAIL             ask for a trial key by email
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

MESSAGES = {
    "seat_limit": "All seats of this key are in use. Run 'arti-license deactivate' on an old machine, or use --key to free one remotely.",
    "key_revoked": "This license was revoked. Contact support.",
    "expired": "This license has expired. Renew it to keep receiving updates; your data and installed version keep working.",
    "not_found": "No such license key (or machine not activated).",
    "not_entitled": "This machine is not entitled under that license.",
    "rate_limited": "Too many requests or deactivation limit reached. Try later or contact support.",
    "bad_checksum": "That key has a typo. Check it and try again.",
    "trial_used": "A trial was already used for this email or machine.",
}


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


def post(path, body):
    req = urllib.request.Request(api_base() + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "arti-license/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
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
    print("error [%s]: %s" % (e.code, MESSAGES.get(e.code, str(e))), file=sys.stderr)
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
    print("Activated (%s seat(s) used).\n%s" % (r.get("seats_used"), describe(info)))
    return 0


def cmd_status(a):
    try:
        cur = lic.read_license()
    except FileNotFoundError:
        print("No license installed. Run 'arti-license activate KEY' or 'arti-license trial EMAIL'.")
        return 1
    if a.refresh:
        try:
            r = post("/validate", {"license": cur, "machine_hash": lic.machine_hash()})
            if lic.evaluate(r["license"])["state"] != "invalid":
                lic.write_license(r["license"])
                cur = r["license"]
                print("(refreshed online)")
        except ApiFailure as e:
            print("(could not refresh: [%s] %s)" % (e.code, MESSAGES.get(e.code, e)), file=sys.stderr)
    info = lic.evaluate(cur)
    print(describe(info))
    return 0 if info["state"] in ("valid", "grace") else (1 if info["state"] == "expired" else 2)


def cmd_deactivate(a):
    body = {"machine_hash": a.machine or lic.machine_hash()}
    if a.key:
        key = need_key(a.key)
        if key is None:
            return 1
        body["key"] = key
    else:
        try:
            body["license"] = lic.read_license()
        except FileNotFoundError:
            print("No local license to deactivate; use --key.", file=sys.stderr)
            return 1
    try:
        post("/deactivate", body)
    except ApiFailure as e:
        return fail(e)
    if not a.machine:
        try:
            os.remove(lic.license_path())
        except FileNotFoundError:
            pass
    print("Deactivated.")
    return 0


def cmd_activations(a):
    key = need_key(a.key)
    if key is None:
        return 1
    try:
        r = post("/activations", {"key": key})
    except ApiFailure as e:
        return fail(e)
    print("%s  seats=%s  status=%s  expires=%s" % (r["key_id"], r["seats"], r["status"], r["expires"]))
    for x in r["activations"]:
        print("  %s  %-30s last seen %s%s" % (x["machine_hash"][:12], x["label"], x["last_seen"], "  (deactivated)" if x["deactivated"] else ""))
    return 0


def cmd_trial(a):
    try:
        r = post("/trial", {"email": a.email})
    except ApiFailure as e:
        return fail(e)
    print(r["message"] + ". Then run: arti-license activate KEY")
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
    p = sub.add_parser("deactivate"); p.add_argument("--key"); p.add_argument("--machine", help="64-hex machine hash of another seat (needs --key)")
    p = sub.add_parser("activations"); p.add_argument("key")
    p = sub.add_parser("trial"); p.add_argument("email")
    p = sub.add_parser("install-file"); p.add_argument("path")
    p = sub.add_parser("verify"); p.add_argument("--file"); p.add_argument("--now", help="ISO UTC time, e.g. 2027-01-01T00:00:00Z")
    a = ap.parse_args(argv)
    return globals()["cmd_" + a.cmd.replace("-", "_")](a)


if __name__ == "__main__":
    sys.exit(main())
