"""License verification shared by the dashboard server, ARTi-setup and tools/arti-license.

Offline only: key checksum, machine hash, canonical JSON, Ed25519 verify, expiry/grace, kid
lookup. Network calls live in tools/arti-license/cli.py. The Worker (arti-services, not shipped)
must produce byte-identical canonical JSON and checksums - see tools/arti-license/README.md.

License file: ~/.arti/license.json = {"payload": {...}, "sig": base64, "kid": str}.
"""

import base64
import datetime
import hashlib
import json
import os
import platform
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import ARTI_HOME  # noqa: E402

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32: no I, L, O, U
KEY_BODY_LEN = 16  # 15 random chars + 1 checksum char
PUBKEYS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "arti-license", "pubkeys.json")
TIERS = ("trial", "individual", "lab", "academic", "site")


def license_path():
    return os.path.join(ARTI_HOME, "license.json")


def revoked_path():
    """Where a license the server reported as revoked is set aside (see arti-license cli.mark_revoked)."""
    return os.path.join(ARTI_HOME, "license.revoked.json")


# ---- online-check bookkeeping (per machine, git-ignored) ------------------------------------------

def check_path():
    return os.path.join(ARTI_HOME, ".license-check.json")


def read_check():
    try:
        with open(check_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_check(**fields):
    """attempted_at: last online attempt (throttle). confirmed_at: last time a server answer confirmed the
    license (validate or the update heartbeat), epoch seconds."""
    data = read_check()
    data.update(fields)
    try:
        with open(check_path(), "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass


def last_confirmed():
    """Epoch seconds of the freshest sign that the server still stands behind this license."""
    try:
        mtime = os.path.getmtime(license_path())
    except OSError:
        return 0.0
    try:
        return max(mtime, float(read_check().get("confirmed_at", 0)))
    except (TypeError, ValueError):
        return mtime


def jittered(seconds, spread=3600):
    """An interval with a random +-spread, so a fleet of machines does not call in lockstep."""
    import random
    return seconds + random.uniform(-spread, spread)


# ---- key checksum -------------------------------------------------------------------------

def normalize_key(key):
    """'arti-ab12-...' -> 16-char body, or None. Folds I/L->1 and O->0 (Crockford)."""
    s = re.sub(r"[\s-]", "", str(key or "")).upper()
    if s.startswith("ARTI"):
        s = s[4:]
    s = s.replace("I", "1").replace("L", "1").replace("O", "0")
    if len(s) != KEY_BODY_LEN or any(c not in ALPHABET for c in s):
        return None
    return s


def checksum_char(body15):
    # odd weights are invertible mod 32, so every single-character typo changes the sum
    total = sum(ALPHABET.index(c) * (2 * i + 1) for i, c in enumerate(body15))
    return ALPHABET[total % 32]


def check_key(key):
    """Return the normalized body if format and checksum are right, else None."""
    body = normalize_key(key)
    if body is None or checksum_char(body[:-1]) != body[-1]:
        return None
    return body


def format_key(body):
    return "ARTI-" + "-".join(body[i:i + 4] for i in range(0, KEY_BODY_LEN, 4))


# ---- machine hash -------------------------------------------------------------------------

def _platform_id():
    override = os.environ.get("ARTI_MACHINE_ID")  # test hook: simulate several machines
    if override:
        return override
    if sys.platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            return winreg.QueryValueEx(k, "MachineGuid")[0]
    if sys.platform == "darwin":
        out = subprocess.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True, text=True).stdout
        m = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
        if m:
            return m.group(1)
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(p, encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            pass
    raise RuntimeError("cannot read a platform machine id")


def machine_hash():
    """sha256('arti-v1' + platform id); the raw id never leaves the machine."""
    return hashlib.sha256(("arti-v1" + _platform_id()).encode("utf-8")).hexdigest()


def machine_label():
    return "%s %s" % (platform.system(), platform.node())


# ---- canonical JSON + signature -----------------------------------------------------------

def canonical_json(obj):
    """Sorted keys, no whitespace, UTF-8 unescaped: matches JS JSON.stringify on sorted keys."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_pubkeys(path=None):
    with open(path or PUBKEYS_PATH, encoding="utf-8") as f:
        return json.load(f)


def verify_signature(payload, sig_b64, public_b64):
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64)).verify(
            base64.b64decode(sig_b64), canonical_json(payload))
        return True
    except (InvalidSignature, ValueError):
        return False


# ---- time + evaluation --------------------------------------------------------------------

def parse_time(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def evaluate(lic, now=None, local_machine=None, pubkeys=None):
    """Judge a license dict. Returns {state, reason, ...}.

    state: valid | grace | expired | invalid. expired/grace mean the signature and machine are
    fine but the term has lapsed: callers degrade to no-updates / read-only, never delete data.
    """
    now = now or utcnow()
    try:
        payload, sig, kid = lic["payload"], lic["sig"], lic["kid"]
        pk = (pubkeys or load_pubkeys()).get("license", {}).get(kid)
        if pk is None:
            return {"state": "invalid", "reason": "unknown_kid"}
        if not verify_signature(payload, sig, pk):
            return {"state": "invalid", "reason": "bad_signature"}
        if payload["tier"] not in TIERS:
            return {"state": "invalid", "reason": "bad_tier"}
        if payload.get("machine_hash") is None:
            if payload["tier"] != "site":
                return {"state": "invalid", "reason": "unbound_license"}
        elif payload["machine_hash"] != (local_machine or machine_hash()):
            return {"state": "invalid", "reason": "wrong_machine"}
        expires = parse_time(payload["expires"])
        grace = datetime.timedelta(days=int(payload.get("grace_days", 0)))
        issued = parse_time(payload["issued"]) if payload.get("issued") else None
    except (KeyError, TypeError, ValueError, AttributeError):
        return {"state": "invalid", "reason": "malformed"}
    # Clock rollback: `issued` is signed by the server at the last activate/validate, so the real time
    # cannot be earlier than that. Judge the term from the later of the two. A gap over a day is reported
    # (clock_behind) so the UI can ask for the date to be fixed; it is never a lock on its own.
    clock_behind = False
    if issued is not None and now < issued:
        clock_behind = (issued - now) > datetime.timedelta(days=1)
        now = issued
    info = {"tier": payload["tier"], "name": payload.get("name"), "key_id": payload.get("key_id"),
            "seats": payload.get("seats"), "expires": payload["expires"],
            "updates_until": payload.get("updates_until"), "kid": kid}
    if clock_behind:
        info["clock_behind"] = True
    if now <= expires:
        info.update(state="valid", reason="ok")
    elif now <= expires + grace:
        info.update(state="grace", reason="expired_in_grace", grace_ends=(expires + grace).strftime("%Y-%m-%dT%H:%M:%SZ"))
    else:
        info.update(state="expired", reason="past_grace")
    return info


def entitled_to_release(info, released):
    """True if the license may install a release dated `released` (ISO string)."""
    if info.get("state") not in ("valid", "grace", "expired") or not info.get("updates_until"):
        return False
    return parse_time(released) <= parse_time(info["updates_until"])


def read_license(path=None):
    with open(path or license_path(), encoding="utf-8") as f:
        return json.load(f)


def write_license(lic, path=None):
    path = path or license_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(lic, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
