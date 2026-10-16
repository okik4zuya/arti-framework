"""ARTi-demo preflight: what this machine has, in one table. Run with the vendored Python:

    python.exe scripts/preflight.py

Prints a table and a final `STATUS:` line. Exit 1 only when the demo cannot run at all (no vendored Python,
or OpenAlex unreachable, which usually means no internet); every other gap is a warning with the fallback the
runbook uses. Secrets are never printed: only the NAMES of configured keys.
"""
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import ARTI_HOME, TOOLS, read_json, run_json, tool_cmd  # noqa: E402

sys.path.insert(0, str(ARTI_HOME))
from tools._shared.browser import find_browser  # noqa: E402
from tools._shared.paths import poppler_bin_dir, tesseract_exe  # noqa: E402

rows = []   # (item, level, detail)  level: ok | warn | fail


def add(item, level, detail):
    rows.append((item, level, detail))


# vendored Python
py = Path(sys.executable)
vendored = (ARTI_HOME / "python") in py.parents
add("Python", "ok" if vendored else "warn", "%s (%s)" % (sys.version.split()[0], "vendored" if vendored else "not the vendored one: " + str(py)))

# tools and databases the demo uses
for tool in ("arti-search", "arti-lit", "arti-db", "arti-docx", "arti-table", "arti-compose", "arti-convert", "arti-jfinder", "citation-chase"):
    add("tool " + tool, "ok" if (TOOLS / tool).is_dir() else "fail", "present" if (TOOLS / tool).is_dir() else "missing")
jdb = TOOLS / "arti-jfinder" / "arti-jfinder.db"
add("Scimago database", "ok" if jdb.is_file() and jdb.stat().st_size > 1_000_000 else "warn",
    "%.1f MB" % (jdb.stat().st_size / 1e6) if jdb.is_file() else "missing: journal choice falls back to general knowledge")

# binaries
browser = find_browser()
add("Edge / Chrome", "ok" if browser else "warn", os.path.basename(browser) if browser else "not found: figures (arti-compose) cannot be rendered")
add("poppler", "ok" if os.path.isdir(poppler_bin_dir()) else "warn", "bin/poppler" if os.path.isdir(poppler_bin_dir()) else "absent: scanned PDFs cannot be OCR'd, text PDFs are fine")
add("tesseract", "ok" if os.path.exists(tesseract_exe()) else "warn", "bin/tesseract" if os.path.exists(tesseract_exe()) else "absent: only needed for scanned PDFs")
drawio = shutil.which("draw.io") or next((p for p in (r"C:\Program Files\draw.io\draw.io.exe",) if os.path.exists(p)), None)
add("draw.io desktop", "ok" if drawio else "warn", "found" if drawio else "absent (informational: the demo draws figures with arti-compose)")

# profiles (the licence is deliberately not looked at: skills and tools never depend on it)
add("Researcher profile", "ok" if (ARTI_HOME / "memory" / "researcher-profile.md").is_file() else "warn",
    "present" if (ARTI_HOME / "memory" / "researcher-profile.md").is_file() else "missing: seed_profiles.py installs the demo profile")
add("Voice profile demo-generic", "ok" if (ARTI_HOME / "voice-profiles" / "demo-generic.md").is_file() else "warn",
    "present" if (ARTI_HOME / "voice-profiles" / "demo-generic.md").is_file() else "missing: seed_profiles.py installs it")

# keys (names only)
keys = read_json(ARTI_HOME / "mcp-keys.json", {}) or {}
names = [n for n in ("OPENALEX_API_KEY", "SEMANTIC_SCHOLAR_API_KEY", "ARTI_REF_CONTACT_EMAIL") if keys.get(n) or os.environ.get(n)]
add("Optional keys", "ok", ", ".join(names) if names else "none set: anonymous pools and open-access links are used")

# live routes (also the internet check)
code, data, raw, err = run_json(tool_cmd("arti-search", "sources"), timeout=120)
if data and "openalex" in data:
    kw = data["openalex"].get("keyword", {})
    add("OpenAlex", "ok" if kw.get("reachable") else "fail", "keyword search reachable" if kw.get("reachable") else "unreachable: " + str(kw.get("detail", ""))[:120])
    s2 = data.get("semanticscholar", {})
    add("Semantic Scholar", "ok" if s2.get("key_configured") else "warn", "key set" if s2.get("key_configured") else "no key: s2-search is skipped, s2-recommend still works")
    gs = data.get("googlescholar", {})
    cd = gs.get("cooldown_remaining_s") or 0
    add("Google Scholar", "warn" if cd else "ok", "cooling down for %d s: skipped" % cd if cd else "available (scraping route, used sparingly)")
else:
    add("arti-search", "fail", "sources failed: " + (raw or err)[:160].replace("\n", " "))

width = max(len(r[0]) for r in rows)
mark = {"ok": "OK  ", "warn": "WARN", "fail": "FAIL"}
for item, level, detail in rows:
    print("%s  %-*s  %s" % (mark[level], width, item, detail))
fatal = [r for r in rows if r[1] == "fail" and r[0] in ("OpenAlex", "arti-search", "tool arti-search", "tool arti-lit", "tool arti-docx")]
status = "FATAL" if fatal else ("WARN" if any(r[1] in ("warn", "fail") for r in rows) else "OK")
print("\nSTATUS: " + status)
if fatal:
    print("The demo cannot run: " + "; ".join("%s (%s)" % (r[0], r[2]) for r in fatal))
sys.exit(1 if fatal else 0)
