"""installer/verify_payload.py and the NSIS file list: what ships must be exactly what git tracks.

Found while preparing the 2026-10-16 installer rebuild: `File /r ..\\tools` packs the working folder, not git, so two
git-ignored render folders (tools/arti-compose/examples/out and panels, about 4 MB) would have travelled with the
installer while the update bundle (git ls-files) never carries them. Checks here:
  * every git-ignored entry inside a shipped folder is excluded by an /x in the matching `File /r` line;
  * verify_payload.compare() reports missing, extra and different files (synthetic trees, no 7-Zip needed);
  * the normalised updater hash ignores CRLF.
"""
import fnmatch
import importlib.util
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import CODE  # noqa: E402

results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


spec = importlib.util.spec_from_file_location("verify_payload", CODE / "installer" / "verify_payload.py")
vp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vp)

# ---- 1. the NSIS list excludes every git-ignored thing inside the shipped folders ----------------------------
nsi = (CODE / "installer" / "arti-installer.nsi").read_text(encoding="utf-8")
excludes = {}
for line in nsi.splitlines():
    m = re.match(r'\s*File /r (.*)"\.\.\\(\w+)"\s*$', line)
    if m:
        excludes[m.group(2)] = re.findall(r'/x "([^"]+)"', m.group(1))
check("the NSIS script packs tools, skills, dashboard and logo with File /r", set(excludes) == {"tools", "skills", "dashboard", "logo"}, sorted(excludes))

ignored = subprocess.run(["git", "-C", str(CODE), "ls-files", "--others", "--ignored", "--exclude-standard", "--directory", "-z", "--"]
                         + sorted(excludes), capture_output=True, check=True).stdout.decode("utf-8").split("\0")
unexcluded = []
for entry in (e for e in ignored if e):
    top = entry.split("/")[0]
    name = entry.rstrip("/").split("/")[-1]
    if not any(fnmatch.fnmatch(name, pat) for pat in excludes.get(top, [])):
        unexcluded.append(entry)
check("every git-ignored entry under a shipped folder is excluded by an /x", not unexcluded, unexcluded)
hidden = []
for p in subprocess.run(["git", "-C", str(CODE), "ls-files", "-z"], capture_output=True, check=True).stdout.decode("utf-8").split("\0"):
    parts = p.split("/")
    pats = [x for x in excludes.get(parts[0], []) if x not in ("__pycache__", "*.pyc", "server.log")]
    if p and any(fnmatch.fnmatch(part, pat) for part in parts[1:] for pat in pats):
        hidden.append(p)
check("exclusion names do not hide a tracked file or folder", not hidden, hidden[:5])

# ---- 2. compare() on synthetic trees ---------------------------------------------------------------------------
def write(root, rel, data):
    p = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as ext:
    tracked = ["tools/a.py", "tools/sub/b.py", "skills/s/SKILL.md", "VERSION"]
    for rel in tracked:
        write(src, rel, b"line 1\r\nline 2\r\n")
        write(ext, rel, b"line 1\r\nline 2\r\n")
    write(ext, "tools/__pycache__/a.cpython-311.pyc", b"x")          # never counted
    write(ext, "python/python.exe", b"MZ")                           # not an update item: ignored here
    missing, extra, different = vp.compare(ext, tracked, root=src)
    check("identical trees: nothing missing, extra or different", (missing, extra, different) == ([], [], []), (missing, extra, different))

    os.remove(os.path.join(ext, "tools", "sub", "b.py"))
    write(ext, "tools/arti-compose/examples/out/big.png", b"png")
    write(ext, "skills/s/SKILL.md", b"line 1\r\nline TWO\r\n")
    missing, extra, different = vp.compare(ext, tracked, root=src)
    check("a missing file is reported", missing == ["tools/sub/b.py"], missing)
    check("an extra (untracked) file is reported", extra == ["tools/arti-compose/examples/out/big.png"], extra)
    check("a changed file is reported", different == ["skills/s/SKILL.md"], different)

    write(src, "tools/crlf.py", b"a\r\nb\r\n")
    write(src, "tools/lf.py", b"a\nb\n")
    check("normalised hash ignores CRLF", vp.norm_hash(os.path.join(src, "tools", "crlf.py")) == vp.norm_hash(os.path.join(src, "tools", "lf.py")))
    check("tracked_files() lists the updater", "tools/arti-update/updater.py" in vp.tracked_files())

print("\n%d checks, %d failed" % (len(results), results.count(False)))
sys.exit(0 if all(results) else 1)
