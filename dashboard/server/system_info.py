"""Read-only facts for Settings -> System and About. Nothing here changes anything."""
import json
import os
import sys
from pathlib import Path

ARTI_HOME = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ARTI_HOME))
from tools._shared.paths import poppler_bin_dir, tesseract_exe, ripgrep_exe  # noqa: E402
from tools._shared.browser import find_browser  # noqa: E402

SKILLS_DIR = Path.home() / ".claude" / "skills"


def _item(name, ok, detail, fix=None):
    return {"name": name, "ok": bool(ok), "detail": detail, "fix": None if ok else fix}


def _skills():
    want = sorted(p.name for p in (ARTI_HOME / "skills").iterdir() if p.is_dir())
    linked = [n for n in want if (SKILLS_DIR / n).exists()]
    missing = [n for n in want if n not in linked]
    return _item("Skills in Claude Code", not missing, "%d of %d linked" % (len(linked), len(want)),
                 "Missing: %s. Run install.ps1 again." % ", ".join(missing))


def _search_tool():
    """The literature search is a CLI (tools/arti-search), so there is nothing to register: check the files
    and report which optional keys are set (names only, never values). No network call."""
    cli = ARTI_HOME / "tools" / "arti-search" / "cli.py"
    try:
        keys = json.loads((ARTI_HOME / "mcp-keys.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        keys = {}
    names = [("OpenAlex", "OPENALEX_API_KEY"), ("Semantic Scholar", "SEMANTIC_SCHOLAR_API_KEY")]
    have = [label for label, k in names if keys.get(k)]
    detail = "ready; keys: %s" % (", ".join(have) if have else "none (optional, anonymous pools are used)")
    return _item("Literature search (arti-search)", cli.is_file(), detail if cli.is_file() else "missing",
                 "tools/arti-search/cli.py is missing. Reinstall or update ARTi.")


def system_status():
    py = Path(sys.executable)
    vendored = (ARTI_HOME / "python") in py.parents
    browser = find_browser()
    items = [
        _item("Python", vendored, "%s (%s)" % (sys.version.split()[0], "vendored" if vendored else "system"),
              "Run install.ps1 to install the vendored Python in ~/.arti/python."),
        _item("Poppler (PDF to image)", os.path.isdir(poppler_bin_dir()), "~/.arti/bin/poppler",
              "Installed by the ARTi installer (.exe). Needed only for OCR of scanned PDFs."),
        _item("Tesseract (OCR)", os.path.exists(tesseract_exe()), "~/.arti/bin/tesseract",
              "Installed by the ARTi installer (.exe). Needed only for OCR of scanned PDFs."),
        _item("ripgrep (fast search)", os.path.exists(ripgrep_exe()), "~/.arti/bin/ripgrep",
              "Optional: the Search panel falls back to a slower built-in scan."),
        _item("Edge / Chrome (PDF export)", browser, os.path.basename(browser) if browser else "not found",
              "Install Microsoft Edge or Google Chrome to export PDFs and figures."),
        _skills(),
        _search_tool(),
    ]
    return {"items": items}


def _framework_version():
    try:
        for line in (ARTI_HOME / "VERSION").read_text(encoding="utf-8").splitlines():
            if line.startswith("FRAMEWORK_VERSION="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None


def about():
    return {"version": _framework_version(), "python": sys.version.split()[0],
            "home": str(ARTI_HOME), "platform": sys.platform}
