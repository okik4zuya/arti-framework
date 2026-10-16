"""Stage a ready-to-ship Python (with every package installed) into installer\payload\python.

Run by build_installer.bat with the maintainer's ARTi Python. The NSIS installer then copies this folder instead of
downloading Python and running pip on the client's machine, which is the slow part of a Windows install.

    stage_python.py [--out DIR] [--cache DIR]

What it does:
  1. Reads PYTHON_BUILD_TAG / PYTHON_VERSION from ..\\VERSION (the same pins install.ps1 uses).
  2. Downloads that python-build-standalone archive into the cache (skipped when already cached).
  3. Unpacks it to a clean folder and installs tools\\requirements.txt plus pywebview and pythonnet into it with
     `python -s -m pip` (never the maintainer's own packages: playwright and friends stay out).
  4. Writes INSTALLED_VERSION and REQUIREMENTS_SHA256 stamps, the same ones install.ps1 reads, so on the client
     it sees "Python already installed" and "packages already installed" and does nothing.
It rebuilds only when a stamp no longer matches (new Python pin or changed requirements.txt).
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))


def read_pins():
    pins = {}
    with open(os.path.join(ROOT, "VERSION"), encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                pins[k] = v
    for key in ("PYTHON_BUILD_TAG", "PYTHON_VERSION"):
        if not pins.get(key):
            sys.exit("VERSION has no %s" % key)
    return pins["PYTHON_BUILD_TAG"], pins["PYTHON_VERSION"]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return None


def download(url, dest):
    print("Downloading %s" % url)
    tmp = dest + ".part"
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as out:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if total:
                sys.stdout.write("\r  %3d%%  (%.1f of %.1f MB)" % (done * 100 // total, done / 1048576, total / 1048576))
                sys.stdout.flush()
    print()
    os.replace(tmp, dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "payload", "python"))
    ap.add_argument("--cache", default=os.path.join(HERE, "payload", "cache"))
    a = ap.parse_args()

    tag, version = read_pins()
    req = os.path.join(ROOT, "tools", "requirements.txt")
    req_hash = sha256_file(req)
    pin = "%s/%s" % (tag, version)

    if read_text(os.path.join(a.out, "INSTALLED_VERSION")) == pin and read_text(os.path.join(a.out, "REQUIREMENTS_SHA256")) == req_hash:
        print("payload\\python is up to date (%s, requirements unchanged); nothing to do." % pin)
        return

    asset = "cpython-%s+%s-x86_64-pc-windows-msvc-install_only.tar.gz" % (version, tag)
    url = "https://github.com/astral-sh/python-build-standalone/releases/download/%s/%s" % (tag, asset)
    os.makedirs(a.cache, exist_ok=True)
    archive = os.path.join(a.cache, asset)
    if not os.path.isfile(archive):
        download(url, archive)

    if os.path.isdir(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    print("Unpacking Python %s ..." % version)
    # The archive's top-level folder is "python/": strip it while extracting, so no directory has to be renamed
    # afterwards (a rename of a freshly unpacked folder fails while antivirus is still scanning its files).
    with tarfile.open(archive) as tf:
        members = []
        for m in tf.getmembers():
            if m.name == "python":
                continue
            if not m.name.startswith("python/"):
                sys.exit("unexpected entry in the Python archive: %s" % m.name)
            m.name = m.name[len("python/"):]
            members.append(m)
        tf.extractall(a.out, members=members, filter="data")

    py = os.path.join(a.out, "python.exe")
    env = dict(os.environ, PYTHONNOUSERSITE="1")
    for args in (["-r", req], ["pywebview", "pythonnet"]):
        print("pip install %s ..." % " ".join(args))
        r = subprocess.run([py, "-s", "-m", "pip", "install", "--disable-pip-version-check", "--no-warn-script-location", *args], env=env)
        if r.returncode != 0:
            sys.exit("pip failed (exit %d); the payload was not stamped" % r.returncode)

    # The pieces the app imports at start: fail the build here, not on a client's machine.
    check = subprocess.run([py, "-s", "-c", "import cryptography, webview, docx, matplotlib, pandas, scipy, mcp, openai, tiktoken, requests, bs4"], env=env)
    if check.returncode != 0:
        sys.exit("the staged Python cannot import the app's packages; not stamped")

    for stamp, text in (("INSTALLED_VERSION", pin), ("REQUIREMENTS_SHA256", req_hash)):
        with open(os.path.join(a.out, stamp), "w", encoding="utf-8", newline="") as f:
            f.write(text)
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(a.out) for f in fs)
    print("payload\\python ready: %.0f MB" % (size / 1048576))


if __name__ == "__main__":
    main()
