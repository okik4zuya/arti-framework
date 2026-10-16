"""Update bundle rules shared by the release builder, the downloader and the updater (stdlib only).

A bundle is a zip of the tracked ARTi items (the code, never the researcher's data). The same list is in
TrackedItems of install.ps1 and TRACKED_ITEMS of install.sh and in the NSIS installer; tests/licensing/test_apply.py
checks that all of them agree.

Nothing here trusts a zip: names are checked before a single byte is written (no absolute paths, no `..`, no
backslashes or drive letters, no symlinks, only items from UPDATE_ITEMS, a size cap), and the files are written by
hand rather than with ZipFile.extractall.
"""
import hashlib
import os
import stat
import zipfile

UPDATE_ITEMS = ("tools", "skills", "dashboard", "logo", "CLAUDE.md", "CAPABILITIES.md", "LICENSE.txt", "README.md",
                "UPDATING.md", "prompt-templates.md", "install.ps1", "install.sh", "install.bat", "VERSION",
                ".gitignore", ".mcp.json")
# Swap order: `VERSION` is last, so an update that stops half way still reads as the old version.
SWAP_FIRST = ("tools", "skills", "dashboard", "logo")

MAX_TOTAL_BYTES = 400 * 1024 * 1024   # uncompressed
MAX_FILES = 20000


class BundleError(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def swap_order(items):
    """Items in the order they are put in place: directories first, VERSION last."""
    items = list(items)
    first = [i for i in SWAP_FIRST if i in items]
    last = [i for i in items if i == "VERSION"]
    mid = [i for i in items if i not in first and i not in last]
    return first + mid + last


def _check_name(name):
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        raise BundleError("bad entry name %r" % name)
    parts = name.rstrip("/").split("/")
    for p in parts:
        if p in ("", ".", "..") or ":" in p:
            raise BundleError("bad entry name %r" % name)
    if parts[0] not in UPDATE_ITEMS:
        raise BundleError("entry %r is not one of the update items" % name)
    return parts


def validate(zf, version=None):
    """Check a ZipFile before extracting. Returns the list of top-level items it contains. Raises BundleError."""
    infos = zf.infolist()
    if not infos:
        raise BundleError("the bundle is empty")
    if len(infos) > MAX_FILES:
        raise BundleError("the bundle has too many entries")
    total, seen, items = 0, set(), set()
    for info in infos:
        parts = _check_name(info.filename)
        mode = info.external_attr >> 16
        if mode and stat.S_ISLNK(mode):
            raise BundleError("entry %r is a symbolic link" % info.filename)
        key = info.filename.rstrip("/").lower()
        if key in seen:
            raise BundleError("entry %r appears twice" % info.filename)
        seen.add(key)
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise BundleError("the bundle is larger than allowed once unpacked")
        items.add(parts[0])
        if parts[0] in ("VERSION", "CLAUDE.md", "CAPABILITIES.md", "LICENSE.txt", "README.md", "UPDATING.md",
                        "prompt-templates.md", "install.ps1", "install.sh", "install.bat", ".gitignore",
                        ".mcp.json") and len(parts) != 1:
            raise BundleError("entry %r should be a single file" % info.filename)
    if "VERSION" not in items:
        raise BundleError("the bundle has no VERSION file")
    if version is not None:
        found = framework_version(zf.read("VERSION").decode("utf-8", "replace"))
        if found != version:
            raise BundleError("the bundle holds version %s, expected %s" % (found, version))
    return sorted(items)


def framework_version(text):
    for line in text.splitlines():
        if line.startswith("FRAMEWORK_VERSION="):
            return line.split("=", 1)[1].strip()
    return None


def extract(zf, dest):
    """Write the (already validated) entries under dest. Existing files are not expected."""
    dest = os.path.abspath(dest)
    for info in zf.infolist():
        target = os.path.abspath(os.path.join(dest, *info.filename.rstrip("/").split("/")))
        if os.path.commonpath([dest, target]) != dest:   # belt and braces after _check_name
            raise BundleError("entry %r escapes the target folder" % info.filename)
        if info.is_dir():
            os.makedirs(target, exist_ok=True)
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with zf.open(info) as src, open(target, "wb") as out:
            while True:
                chunk = src.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        mode = info.external_attr >> 16
        if mode & 0o111:
            os.chmod(target, 0o755)


def open_validated(path, version=None):
    """Open a bundle zip and validate it. Returns (ZipFile, items). Caller closes the ZipFile."""
    try:
        zf = zipfile.ZipFile(path)
    except (zipfile.BadZipFile, OSError) as e:
        raise BundleError("not a readable zip: %s" % e)
    try:
        return zf, validate(zf, version)
    except Exception:
        zf.close()
        raise
