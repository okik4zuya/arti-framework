"""Check what is really INSIDE a built installer, not just what the source tree says.

    verify_payload.py <ArtiFrameworkSetup-x.y.z.exe> [--7z PATH] [--out DIR] [--keep]

Extracts the installer with 7-Zip (it reads NSIS archives) into a new empty folder, then compares it with the
working copy:
  * every git-tracked file of the update items (the same list as tools/arti-update/bundle.py) is present and
    byte-identical to the file on disk (CRLF checkouts are fine: NSIS packs the disk bytes);
  * nothing extra shipped inside those items (git-ignored runtime or example output must not travel);
  * tools/arti-update/updater.py: length and sha256 after CRLF normalisation (the fixed updater must be the
    one that ships, see release-checklist items 14-16);
  * python\\ carries the stamps INSTALLED_VERSION / REQUIREMENTS_SHA256 that match VERSION and
    tools/requirements.txt, so install.ps1 skips the download and pip;
  * bin\\ has poppler and tesseract; secrets and per-machine files (license.json, mcp-keys.json, memory, .update)
    are absent; VERSION in the installer equals VERSION on disk.
Exit code 0 only when everything passes. Run it with the vendored Python:  python\\python.exe installer\\verify_payload.py ...
"""
import argparse
import hashlib
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "arti-update"))
from bundle import UPDATE_ITEMS  # noqa: E402

FORBIDDEN = ("license.json", "license.revoked.json", ".license-check.json", "mcp-keys.json", "memory", ".update",
             ".backup", "inbox", "voice-profiles", "literature", "notes", ".side-note.md")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_hash(path):
    with open(path, "rb") as f:
        data = f.read().replace(b"\r\n", b"\n")
    return len(data), hashlib.sha256(data).hexdigest()


def tracked_files():
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "-z", "--", *UPDATE_ITEMS], capture_output=True, check=True).stdout
    return sorted(p for p in out.decode("utf-8").split("\0") if p)


def shipped_files(extracted):
    """Relative posix paths of every file under the update items in the extracted installer."""
    found = set()
    for item in UPDATE_ITEMS:
        p = os.path.join(extracted, item)
        if os.path.isfile(p):
            found.add(item)
        elif os.path.isdir(p):
            for d, dirs, files in os.walk(p):
                dirs[:] = [x for x in dirs if x != "__pycache__"]
                for f in files:
                    if f.endswith(".pyc"):
                        continue
                    found.add(os.path.relpath(os.path.join(d, f), extracted).replace(os.sep, "/"))
    return found


def unexpected_files(extracted, payload=os.path.join(HERE, "payload")):
    """Files in the extracted installer that are neither under an update item, nor in the staged python/ or bin/
    payload. Found 2026-10-17: `File /r "..\\tools"` made makensis pack every folder named tools or skills from the
    maintainer's vendored Python (fastmcp, mcp, pywin32, typer) and from installer\\payload itself; none of it sits
    under an update item, so the tracked-files comparison never saw it."""
    bad = []
    for d, dirs, files in os.walk(extracted):
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), extracted)
            top = rel.split(os.sep)[0]
            if top in UPDATE_ITEMS or rel == "Uninstall.exe":
                continue   # compare() covers the items; Uninstall.exe is written by the installer itself
            if top in ("python", "bin"):
                if not os.path.exists(os.path.join(payload, rel)):
                    bad.append(rel.replace(os.sep, "/"))
                continue
            bad.append(rel.replace(os.sep, "/"))
    return sorted(bad)


def compare(extracted, expected, root=ROOT):
    """Returns (missing, extra, different) lists for the update items. expected = tracked relative paths."""
    shipped = shipped_files(extracted)
    exp = set(expected)
    missing = sorted(exp - shipped)
    extra = sorted(shipped - exp)
    different = []
    for rel in sorted(exp & shipped):
        a, b = os.path.join(extracted, rel), os.path.join(root, rel)
        if os.path.getsize(a) != os.path.getsize(b) or sha256(a) != sha256(b):
            different.append(rel)
    return missing, extra, different


def read_pins(path):
    pins = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                pins[k] = v
    return pins


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--7z", dest="sevenzip", default=r"C:\Program Files\7-Zip\7z.exe")
    ap.add_argument("--out", help="extract here (must not exist or be empty); default: a new temp folder")
    ap.add_argument("--keep", action="store_true", help="keep the extracted folder")
    a = ap.parse_args()

    if not os.path.isfile(a.exe):
        sys.exit("installer not found: %s" % a.exe)
    if not os.path.isfile(a.sevenzip):
        sys.exit("7-Zip not found at %s (pass --7z)" % a.sevenzip)
    out = a.out or tempfile.mkdtemp(prefix="arti-payload-")
    if os.path.isdir(out) and os.listdir(out):
        sys.exit("output folder is not empty: %s" % out)
    os.makedirs(out, exist_ok=True)
    print("Extracting %s (%.0f MB) into %s ..." % (a.exe, os.path.getsize(a.exe) / 1048576, out))
    r = subprocess.run([a.sevenzip, "x", "-y", "-bso0", "-bsp0", "-o" + out, a.exe, "-x!$PLUGINSDIR", "-x!$PLUGINSDIR\\*"])
    if r.returncode not in (0, 1):   # 1 = warnings only
        sys.exit("7-Zip failed (exit %d)" % r.returncode)

    results = []

    def check(name, ok, detail=""):
        results.append(bool(ok))
        print(("PASS  " if ok else "FAIL  ") + name + (("   " + detail) if detail and not ok else ""))

    # 1. update items
    missing, extra, different = compare(out, tracked_files())
    check("every tracked file of the update items is in the installer", not missing, "missing: %s" % missing[:10])
    check("nothing but tracked files shipped inside the update items", not extra, "extra: %s" % extra[:10])
    check("every shipped file is byte-identical to the working copy", not different, "different: %s" % different[:10])

    stray = unexpected_files(out)
    check("every file outside the update items is part of the staged python/ or bin/ payload", not stray,
          "%d unexpected, for example %s" % (len(stray), stray[:6]))

    # 2. updater
    upd_rel = "tools/arti-update/updater.py"
    inst, disk = os.path.join(out, upd_rel), os.path.join(ROOT, upd_rel)
    if os.path.isfile(inst):
        li, hi = norm_hash(inst)
        ld, hd = norm_hash(disk)
        print("      updater.py in installer: len %d sha256 %s" % (li, hi))
        print("      updater.py on disk:      len %d sha256 %s" % (ld, hd))
        check("updater.py in the installer equals the one on disk (normalised)", (li, hi) == (ld, hd))
    else:
        check("updater.py is in the installer", False)

    # 3. python stamps
    pins = read_pins(os.path.join(ROOT, "VERSION"))
    pin = "%s/%s" % (pins["PYTHON_BUILD_TAG"], pins["PYTHON_VERSION"])
    py = os.path.join(out, "python")
    def stamp(n):
        try:
            with open(os.path.join(py, n), encoding="utf-8") as f:
                return f.read().strip()
        except OSError:
            return None
    req_hash = sha256(os.path.join(ROOT, "tools", "requirements.txt"))
    check("python\\python.exe and pythonw.exe are in the installer", all(os.path.isfile(os.path.join(py, n)) for n in ("python.exe", "pythonw.exe")))
    check("INSTALLED_VERSION stamp equals the pin in VERSION (%s)" % pin, stamp("INSTALLED_VERSION") == pin, "got %r" % stamp("INSTALLED_VERSION"))
    check("REQUIREMENTS_SHA256 stamp equals tools/requirements.txt", stamp("REQUIREMENTS_SHA256") == req_hash, "got %r" % stamp("REQUIREMENTS_SHA256"))
    check("packages are inside python\\ (site-packages has webview, pandas, cryptography)",
          all(os.path.isdir(os.path.join(py, "Lib", "site-packages", n)) for n in ("webview", "pandas", "cryptography")))
    # ARTi ships no MCP server since 2026-10-17; the `mcp` package must not travel (found 2026-10-17: three stray files
    # under site-packages\mcp\server\mcpserver\tools made `import mcp` succeed as an empty namespace package).
    sp = os.path.join(py, "Lib", "site-packages")
    stray = sorted(n for n in (os.listdir(sp) if os.path.isdir(sp) else []) if n.lower().split("-")[0] in ("mcp", "mcp_types"))
    check("no mcp package (or leftover folder) in site-packages", not stray, "found %r" % stray)

    # 4. bin
    check("bin\\poppler and bin\\tesseract\\tesseract.exe are in the installer",
          os.path.isdir(os.path.join(out, "bin", "poppler")) and os.path.isfile(os.path.join(out, "bin", "tesseract", "tesseract.exe")))
    print("      bin\\ripgrep\\rg.exe: %s (optional)" % ("present" if os.path.isfile(os.path.join(out, "bin", "ripgrep", "rg.exe")) else "absent"))

    # 5. nothing private
    leaked = [n for n in FORBIDDEN if os.path.exists(os.path.join(out, n))]
    check("no per-machine or private file at the install root", not leaked, "found: %s" % leaked)
    check("installer VERSION equals VERSION on disk", sha256(os.path.join(out, "VERSION")) == sha256(os.path.join(ROOT, "VERSION")))
    check("install.ps1 and install.bat are at the root", all(os.path.isfile(os.path.join(out, n)) for n in ("install.ps1", "install.bat")))

    total = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(out) for f in fs)
    print("\nExtracted size: %.0f MB. %d checks, %d failed." % (total / 1048576, len(results), results.count(False)))
    if not a.keep and not a.out:
        import shutil
        shutil.rmtree(out, ignore_errors=True)
    else:
        print("Kept: %s" % out)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
