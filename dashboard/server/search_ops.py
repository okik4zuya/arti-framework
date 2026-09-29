"""Ripgrep-backed content search for the dashboard Search panel.

Pure accelerant, never a hard dependency: chat.py's pure-Python file-walk +
substring scan (search_project_text) stays as the permanent fallback for any
machine without rg (e.g. install.ps1/install.sh installs, which don't vendor
~/.arti/bin/ripgrep the way the NSIS installer does). Callers check
rg_available() and catch RgSearchFailed to fall back -- rg never being present
is an expected, ordinary case, not an error condition.

Follows the same conventions as platform_ops.py: explicit timeouts,
capture_output=True, CREATE_NO_WINDOW on Windows, a dedicated exception for
"not usable" instead of a silent guess.
"""
import base64
import json
import os
import platform
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ARTI_HOME = Path(__file__).resolve().parent.parent.parent
if str(ARTI_HOME) not in sys.path:
    sys.path.insert(0, str(ARTI_HOME))

from tools._shared.paths import ripgrep_exe  # noqa: E402

RG_TIMEOUT = 15

_UNSET = object()
_rg_path = _UNSET


class RgSearchFailed(Exception):
    """Raised when an rg invocation fails for a reason other than "no matches"
    (exit 1) -- callers catch this and fall back to the pure-Python scan."""


def _find_rg():
    global _rg_path
    if _rg_path is not _UNSET:
        return _rg_path
    vendored = ripgrep_exe()
    _rg_path = vendored if os.path.isfile(vendored) else shutil.which("rg")
    return _rg_path


def rg_available():
    return _find_rg() is not None


def _ext_globs(extensions):
    return [f"*{ext}" for ext in extensions]


def _run_rg_for_term(rg_path, project_root, term_lower, ext_globs, max_file_bytes,
                      max_matches_per_file, timeout=RG_TIMEOUT):
    """Runs one rg process for a single (already-lowercased) fixed-string
    term, returns {rel_path: [(line_no, raw_line_text), ...]} for every
    matching line (up to max_matches_per_file per file). One process per term
    -- rg's -e flags always OR together, so AND-mode combination happens in
    Python by intersecting per-term file-result sets (see search_snippets_rg).

    The -m cap matters: without it, a common term (matching most lines of
    most files) makes rg emit -- and this module JSON-parse -- every matching
    line in the whole project, even though only max_snippets_per_file per
    file is ever kept downstream. That made the rg path measurably *slower*
    than the plain Python scan for common terms in benchmarking, since the
    Python path already short-circuits per file after max_snippets_per_file
    hits. The cap here is generous (well above max_snippets_per_file) so
    merging multiple terms' results still reproduces the same first-N-lines
    selection the unbounded scan would have picked."""
    cmd = [
        rg_path, "--json", "-i", "-F", "--no-ignore", "-e", term_lower,
        "-m", str(max_matches_per_file),
        *[arg for glob in ext_globs for arg in ("-g", glob)],
        "-g", "!.*", "-g", "!node_modules", "-g", "!__pycache__",
        "--max-filesize", str(max_file_bytes),
        "--", project_root,
    ]

    kwargs = {}
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout, **kwargs)
    except FileNotFoundError as exc:
        raise RgSearchFailed(f"rg not found: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RgSearchFailed(f"rg timed out: {exc}") from exc

    if proc.returncode not in (0, 1):  # 0 = matches found, 1 = no matches (not an error)
        raise RgSearchFailed(
            f"rg exited {proc.returncode}: {proc.stderr.decode('utf-8', errors='replace')}"
        )

    hits = {}
    for raw_line in proc.stdout.splitlines():
        if not raw_line:
            continue
        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if msg.get("type") != "match":
            continue
        data = msg["data"]
        abs_path = data.get("path", {}).get("text")
        if abs_path is None:
            continue
        lines = data.get("lines", {})
        if "text" in lines:
            line_text = lines["text"]
        elif "bytes" in lines:
            line_text = base64.b64decode(lines["bytes"]).decode("utf-8", errors="replace")
        else:
            continue
        rel_path = os.path.relpath(abs_path, project_root).replace("\\", "/")
        # rg reads raw bytes (no universal-newline translation the way
        # Path.read_text() does), so a CRLF file's line still ends in "\r"
        # after stripping "\n" -- strip both to match the Python path's lines.
        hits.setdefault(rel_path, []).append((data["line_number"], line_text.rstrip("\r\n")))
    return hits


def search_snippets_rg(project_path, terms_lower, mode, max_snippets_per_file,
                        max_total_snippets, include_lower, exclude_lower, timeout=RG_TIMEOUT):
    """rg-backed replacement for the snippet-scanning half of
    chat.search_project_text (file-list building via chat._search_filenames
    is untouched and stays in chat.py -- that stage was never the
    bottleneck). Returns (snippets_out, snippets_truncated) with the exact
    same snippet dict shape chat.py already produces, so the frontend needs
    no changes. Raises RgSearchFailed if rg isn't usable; callers fall back
    to chat's pure-Python scan."""
    import chat  # lazy import: chat imports this module lazily too, avoids a hard cycle

    rg_path = _find_rg()
    if rg_path is None:
        raise RgSearchFailed("rg not available")

    project_root = str(Path(project_path).resolve())
    ext_globs = _ext_globs(chat.SEARCH_TEXT_EXTENSIONS)
    max_matches_per_file = max(40, max_snippets_per_file * 8)

    with ThreadPoolExecutor(max_workers=min(8, len(terms_lower))) as pool:
        term_results = list(pool.map(
            lambda t: _run_rg_for_term(
                rg_path, project_root, t, ext_globs, chat.SEARCH_MAX_FILE_BYTES,
                max_matches_per_file, timeout,
            ),
            terms_lower,
        ))

    file_key_sets = [set(r.keys()) for r in term_results]
    if mode == "and":
        surviving = set.intersection(*file_key_sets) if file_key_sets else set()
    else:
        surviving = set.union(*file_key_sets) if file_key_sets else set()

    snippets_out = []
    snippets_truncated = False

    for rel_path in sorted(surviving):
        abs_path = os.path.join(project_root, *rel_path.split("/"))

        # A file survives the AND/OR gate above at the whole-file level; the
        # snippet lines shown are the union of every term's hit lines in it,
        # same as chat._build_snippet being called against every line with
        # the full term list regardless of which term(s) drove the gate.
        merged_lines = {}
        for term_result in term_results:
            for line_no, line_text in term_result.get(rel_path, []):
                merged_lines.setdefault(line_no, line_text)

        if include_lower or exclude_lower:
            text_lower = chat._read_text_lower_safe(abs_path)
            if not chat._passes_refinement(rel_path.lower(), text_lower, include_lower, exclude_lower):
                continue

        file_snippets = []
        for line_no in sorted(merged_lines):
            if len(file_snippets) >= max_snippets_per_file:
                break
            built = chat._build_snippet(merged_lines[line_no], terms_lower)
            if built is None:
                continue
            snippet, ranges = built
            file_snippets.append({
                "rel_path": rel_path,
                "abs_path": abs_path,
                "line_number": line_no,
                "snippet": snippet,
                "highlight_ranges": [list(r) for r in ranges],
            })

        if len(snippets_out) < max_total_snippets:
            remaining = max_total_snippets - len(snippets_out)
            snippets_out.extend(file_snippets[:remaining])
            if len(file_snippets) > remaining:
                snippets_truncated = True
        else:
            snippets_truncated = True

    return snippets_out, snippets_truncated
