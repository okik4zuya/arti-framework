"""Dashboard-facing adapter for the chat feature (ported from the standalone
`fine-ai-chat` project) -- CRUD over the chat_* tables in the shared
tools/arti-db/db.py store, plus the two AI-call paths: streaming chat and
one-shot PDF summarization. Follows the same thin-adapter convention as
db.py/db_ideas.py/journals.py/lit.py: load arti_db via
importlib.util.spec_from_file_location, use its _lock/_connect/_row_to_dict,
no ORM, no separate connection machinery.
"""
import base64
import importlib.util
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import platform_ops

ARTI_HOME = Path(__file__).resolve().parent.parent.parent
if str(ARTI_HOME) not in sys.path:
    sys.path.insert(0, str(ARTI_HOME))

from tools._shared.paths import poppler_bin_dir, tesseract_exe  # noqa: E402

DEFAULT_SYSTEM_ROLE = "You are a helpful assistant."
DEFAULT_PDF_SUMMARY_PROMPT = (
    "Summarize the following paper's full text. Cover the research question, "
    "method, key findings, and limitations in a few concise paragraphs."
)


def _extract_pdf_text(pdf_path):
    """Mirrors tools/arti-pdf-ingest/cli.py::extract_text_to_markdown -- pdfminer
    text layer, OCR fallback via pdf2image + pytesseract against the vendored
    ~/.arti/bin/{poppler,tesseract} binaries."""
    from pdfminer.high_level import extract_text
    text = extract_text(pdf_path)
    if not text.strip():
        from pdf2image import convert_from_path
        import pytesseract
        tess = tesseract_exe()
        if not os.path.exists(tess):
            raise RuntimeError("No text layer and Tesseract OCR isn't installed on this machine.")
        pytesseract.pytesseract.tesseract_cmd = tess
        pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_bin_dir())
        text = "\n".join(pytesseract.image_to_string(page) for page in pages)
    return "# Extracted PDF Content\n\n" + text


def _safe_model_slug(model_name):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", model_name).strip("-") or "model"


def _load_arti_db():
    path = ARTI_HOME / "tools" / "arti-db" / "db.py"
    spec = importlib.util.spec_from_file_location("arti_db", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_arti_pdf():
    path = ARTI_HOME / "tools" / "arti-pdf" / "render.py"
    spec = importlib.util.spec_from_file_location("arti_pdf", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arti_db = _load_arti_db()
arti_pdf = _load_arti_pdf()

_UNSET = object()


def _now():
    return datetime.now().isoformat()


# ---------------------------------------------------------------------------
# projects ("Folders" in the UI)
# ---------------------------------------------------------------------------

def list_projects():
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            rows = conn.execute("SELECT * FROM chat_projects ORDER BY name").fetchall()
            return [arti_db._row_to_dict(r) for r in rows]
        finally:
            conn.close()


def create_project(name, color=None):
    name = (name or "").strip()
    if not name:
        raise ValueError("Folder name is required")
    now = _now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            if conn.execute("SELECT id FROM chat_projects WHERE name = ?", (name,)).fetchone():
                raise ValueError("A folder with this name already exists")
            cur = conn.execute(
                "INSERT INTO chat_projects (name, color, created_at) VALUES (?, ?, ?)",
                (name, color or "#007bff", now),
            )
            conn.commit()
            return arti_db._row_to_dict(
                conn.execute("SELECT * FROM chat_projects WHERE id = ?", (cur.lastrowid,)).fetchone()
            )
        finally:
            conn.close()


def update_project(project_id, name=None, color=None):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            fields, values = [], []
            if name is not None:
                name = name.strip()
                if not name:
                    raise ValueError("Folder name cannot be empty")
                other = conn.execute(
                    "SELECT id FROM chat_projects WHERE name = ? AND id != ?", (name, project_id)
                ).fetchone()
                if other:
                    raise ValueError("A folder with this name already exists")
                fields.append("name = ?")
                values.append(name)
            if color is not None:
                fields.append("color = ?")
                values.append(color)
            if fields:
                values.append(project_id)
                conn.execute(f"UPDATE chat_projects SET {', '.join(fields)} WHERE id = ?", values)
                conn.commit()
            row = conn.execute("SELECT * FROM chat_projects WHERE id = ?", (project_id,)).fetchone()
            return arti_db._row_to_dict(row)
        finally:
            conn.close()


def delete_project(project_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM chat_sessions WHERE project_id = ?", (project_id,)
            ).fetchone()[0]
            if count > 0:
                raise ValueError(
                    f"Cannot delete folder with {count} session(s). Move or delete sessions first."
                )
            conn.execute("DELETE FROM chat_projects WHERE id = ?", (project_id,))
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# sessions
# ---------------------------------------------------------------------------

def list_sessions():
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            rows = conn.execute(
                "SELECT s.id, s.name, s.created_at, s.updated_at, s.system_role, s.temperature, "
                "s.project_id, s.linked_project_path, s.model_id, s.files_position, s.cross_session_position, "
                "p.name as project_name, "
                "p.color as project_color, m.name as model_name "
                "FROM chat_sessions s LEFT JOIN chat_projects p ON s.project_id = p.id "
                "LEFT JOIN chat_models m ON s.model_id = m.id "
                "ORDER BY s.updated_at DESC"
            ).fetchall()
            result = []
            for row in rows:
                d = arti_db._row_to_dict(row)
                count = conn.execute(
                    "SELECT COUNT(*) FROM chat_messages WHERE session_id = ? AND role = 'assistant'",
                    (d["id"],),
                ).fetchone()[0]
                d["messageCount"] = count
                result.append(d)
            return result
        finally:
            conn.close()


def create_session(name=None, project_id=None, linked_project_path=None, model_id=None):
    name = name or "New Session"
    now = _now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            if project_id and linked_project_path is None:
                folder = conn.execute(
                    "SELECT linked_project_path FROM chat_projects WHERE id = ?", (project_id,)
                ).fetchone()
                if folder and folder["linked_project_path"]:
                    linked_project_path = folder["linked_project_path"]
            default_role = conn.execute(
                "SELECT content FROM chat_system_roles WHERE is_default = 1 LIMIT 1"
            ).fetchone()
            system_role = default_role["content"] if default_role else DEFAULT_SYSTEM_ROLE
            cur = conn.execute(
                "INSERT INTO chat_sessions (name, created_at, updated_at, system_role, temperature, "
                "project_id, linked_project_path, model_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, now, now, system_role, 0.7, project_id, linked_project_path, model_id),
            )
            conn.commit()
            row = conn.execute(
                "SELECT s.id, s.name, s.created_at, s.updated_at, s.system_role, s.temperature, "
                "s.project_id, s.linked_project_path, s.model_id, s.files_position, s.cross_session_position, "
                "p.name as project_name, "
                "p.color as project_color, m.name as model_name "
                "FROM chat_sessions s LEFT JOIN chat_projects p ON s.project_id = p.id "
                "LEFT JOIN chat_models m ON s.model_id = m.id WHERE s.id = ?",
                (cur.lastrowid,),
            ).fetchone()
            d = arti_db._row_to_dict(row)
            d["messageCount"] = 0
            return d
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# project-scoped chat (sessions linked to a paper project's folder, with a
# file browser over that project's .md/.txt files for context attachment)
# ---------------------------------------------------------------------------

PROJECT_FILE_EXTENSIONS = (".md", ".txt", ".ris", ".bib", ".csv", ".tsv", ".json")
PROJECT_FILE_SKIP_DIRS = {".git", "node_modules", "__pycache__"}
PROJECT_FILE_PREVIEW_MAX_BYTES = 2 * 1024 * 1024

BINARY_PREVIEWABLE_EXTENSIONS = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
}


def _require_known_project_path(conn, project_path):
    row = conn.execute(
        "SELECT id FROM project_index WHERE project_path = ?", (project_path,)
    ).fetchone()
    if not row:
        raise ValueError("Unknown project path")


def _get_or_create_project_folder(conn, project_path, project_name):
    """One chat 'Folder' (chat_projects row) per paper project, keyed by path
    (not name) so a later project rename doesn't orphan the folder. Session
    grouping in the sidebar is driven by chat_sessions.project_id, which this
    folder's id feeds into -- distinct from linked_project_path, which drives
    the file-browser feature on the session itself."""
    row = conn.execute(
        "SELECT id FROM chat_projects WHERE linked_project_path = ?", (project_path,)
    ).fetchone()
    if row:
        return row["id"]
    base_name = (project_name or Path(project_path).name or "Project").strip() or "Project"
    name = base_name
    suffix = 2
    while conn.execute("SELECT id FROM chat_projects WHERE name = ?", (name,)).fetchone():
        name = f"{base_name} ({suffix})"
        suffix += 1
    cur = conn.execute(
        "INSERT INTO chat_projects (name, color, created_at, linked_project_path) VALUES (?, ?, ?, ?)",
        (name, "#2563eb", _now(), project_path),
    )
    return cur.lastrowid


def get_or_create_project_session(project_path, project_name):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
            folder_id = _get_or_create_project_folder(conn, project_path, project_name)
            conn.commit()
            row = conn.execute(
                "SELECT id, project_id FROM chat_sessions WHERE linked_project_path = ?", (project_path,)
            ).fetchone()
            if row:
                if row["project_id"] != folder_id:
                    conn.execute(
                        "UPDATE chat_sessions SET project_id = ? WHERE id = ?", (folder_id, row["id"])
                    )
                    conn.commit()
                return row["id"]
        finally:
            conn.close()
    session = create_session(name=project_name, project_id=folder_id, linked_project_path=project_path)
    return session["id"]


def list_project_files(project_path):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()

    root = Path(project_path)
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in PROJECT_FILE_SKIP_DIRS and not d.startswith(".")
        ]
        for fn in filenames:
            if fn.startswith("."):
                continue
            abs_path = Path(dirpath) / fn
            files.append({
                "rel_path": str(abs_path.relative_to(root)).replace("\\", "/"),
                "abs_path": str(abs_path),
            })
    files.sort(key=lambda f: f["rel_path"])
    return files


def _resolve_under_project(project_path, abs_path):
    """Validates abs_path resolves under project_path, rejecting any `..`
    escape; returns the resolved Path or raises ValueError."""
    root = Path(project_path).resolve()
    target = Path(abs_path).resolve()
    if root != target and root not in target.parents:
        raise ValueError("File path is outside the project folder")
    return target


def _sniff_is_text(path, sample_size=8192):
    """Content-based text/binary detection, same heuristic class as Notepad++
    or `file(1)`: no NUL bytes, and either a clean UTF-8 decode or a low
    enough ratio of non-printable bytes. Lets any text-based file be opened
    regardless of extension, instead of maintaining an allowlist."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
    except OSError:
        return False
    if not chunk:
        return True
    if b"\x00" in chunk:
        return False
    try:
        chunk.decode("utf-8")
        return True
    except UnicodeDecodeError:
        pass
    text_bytes = set(b"\t\n\r\x0c\x1b") | set(range(0x20, 0x100))
    nontext = sum(1 for b in chunk if b not in text_bytes)
    return (nontext / len(chunk)) < 0.30


def read_project_file(project_path, abs_path):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    stat = target.stat()
    if stat.st_size > PROJECT_FILE_PREVIEW_MAX_BYTES:
        raise ValueError("File is too large to preview")
    if not _sniff_is_text(target):
        raise ValueError("File does not appear to be text")
    return target.read_text(encoding="utf-8", errors="replace"), stat.st_mtime


def stat_project_file(project_path, abs_path):
    """Cheap mtime-only check for the preview panel's change-detection poll --
    no content is read, just a stat() call, so this stays fast even hit every
    few seconds while a file is open."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    return target.stat().st_mtime


def read_project_file_raw(project_path, abs_path):
    """Binary-safe counterpart to read_project_file, for previewing images and
    PDFs -- returns raw bytes plus the MIME type instead of decoding as text."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    mime = BINARY_PREVIEWABLE_EXTENSIONS.get(target.suffix.lower())
    if mime is None:
        raise ValueError("File type is not previewable")
    return target.read_bytes(), mime


def open_project_file(project_path, abs_path):
    """Launches abs_path in its OS-default application (the Files panel's
    three-dot "Open" action) -- for files with no inline preview."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    platform_ops.open_file_default(target)


def open_project_file_with_dialog(project_path, abs_path):
    """Same as open_project_file, but shows the OS's native "Open with..."
    application chooser instead of launching the default association."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    platform_ops.open_file_with_dialog(target)


def reveal_project_file(project_path, abs_path):
    """Opens abs_path's containing folder with it selected -- the Files
    panel's three-dot "Open file location" action."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    platform_ops.reveal_file_in_file_manager(target)


def copy_project_files_to_clipboard(project_path, abs_paths):
    """Puts one or more project files onto the OS clipboard as real files
    (the Project Files panel's "Copy" row action and bulk "Copy files"
    action) -- so pasting into Explorer, WhatsApp Desktop, etc. pastes the
    files themselves, distinct from the client-side-only "Copy full path"
    action, which just puts the path string on the clipboard via
    navigator.clipboard and never reaches the server."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    if not abs_paths:
        raise ValueError("No files given")
    targets = [str(_resolve_under_project(project_path, p)) for p in abs_paths]
    platform_ops.copy_files_to_clipboard(targets)


def write_project_file(project_path, abs_path, content):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    target.write_text(content, encoding="utf-8")
    return target.stat().st_mtime


def export_project_file_pdf(project_path, abs_path, html):
    """Prints an already-rendered HTML document (built client-side from the
    same marked.js/KaTeX pipeline the preview panel uses) to PDF via the
    arti-pdf tool's headless-browser print step, writing the result directly
    next to the source file (same convention as the arti-pdf CLI) rather than
    streaming it back for a browser download -- the dashboard runs inside a
    pywebview/WebView2 shell where downloads are non-trivial (disabled by
    default, and even enabled, save to wherever the OS picks rather than the
    project folder). Scoped to a known project path the same way every other
    project-files call is, even though the file itself is never read
    server-side -- this stays "export a file that belongs to a known
    project", not an open HTML-to-PDF proxy."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    dest_pdf_path = target.with_suffix(".pdf")
    with tempfile.TemporaryDirectory() as tmp_dir:
        html_path = os.path.join(tmp_dir, "export.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        if not arti_pdf.html_to_pdf(html_path, str(dest_pdf_path)):
            raise RuntimeError("No headless Edge or Chrome found on this machine — cannot export to PDF.")
    return str(dest_pdf_path)


def create_project_file(project_path, rel_path, content, encoding=None):
    """Creates a new file under project_path (upload or paste-text flows in
    the Project Files panel) -- refuses to overwrite an existing file, unlike
    write_project_file which is used for in-place edits of a known file.

    `encoding="base64"` is the upload path (any filetype, including binary --
    the browser can't safely hand us binary content as a JSON string
    otherwise) and skips the text-extension allowlist below, which exists
    only for the plain-text "type a new file" authoring flow.
    """
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    rel_path = (rel_path or "").strip().lstrip("/\\")
    if not rel_path:
        raise ValueError("File name is required")
    if encoding != "base64" and not rel_path.lower().endswith(PROJECT_FILE_EXTENSIONS):
        raise ValueError(
            "Unsupported file type -- allowed: " + ", ".join(PROJECT_FILE_EXTENSIONS)
        )
    target = _resolve_under_project(project_path, str(Path(project_path) / rel_path))
    if target.exists():
        raise ValueError("A file with this name already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    if encoding == "base64":
        target.write_bytes(base64.b64decode(content or ""))
    else:
        target.write_text(content or "", encoding="utf-8")
    return {"rel_path": rel_path, "abs_path": str(target)}


def rename_project_file(project_path, abs_path, new_rel_path):
    """Renames/moves an existing project file to new_rel_path (relative to
    project_path). No extension allowlist here -- unlike create_project_file,
    this operates on files that already exist on disk (including binary
    types uploaded via the base64 path), so restricting extensions would
    block legitimate renames of e.g. images."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    source = _resolve_under_project(project_path, abs_path)
    if not source.exists():
        raise ValueError("File not found")
    new_rel_path = (new_rel_path or "").strip().lstrip("/\\")
    if not new_rel_path:
        raise ValueError("File name is required")
    target = _resolve_under_project(project_path, str(Path(project_path) / new_rel_path))
    if target.exists():
        raise ValueError("A file with this name already exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    return {"rel_path": new_rel_path, "abs_path": str(target)}


def delete_project_file(project_path, abs_path):
    """Deletes an existing project file. Confirmation is the client's
    responsibility (this performs the deletion unconditionally once called)."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    if not target.exists():
        raise ValueError("File not found")
    target.unlink()
    return {"deleted": True}


def attach_file_as_context(session_id, project_path, abs_path):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    text = target.read_text(encoding="utf-8", errors="replace")
    rel_path = str(target.relative_to(Path(project_path).resolve())).replace("\\", "/")
    content = f"# File: {rel_path}\n\n{text}"
    return add_message(session_id, role="system", content=content, is_context=1)


# ---------------------------------------------------------------------------
# cross-file content search (Search panel) -- greps a project's (or every
# registered project's) text files on demand, no persistent index
# ---------------------------------------------------------------------------

SEARCH_TEXT_EXTENSIONS = PROJECT_FILE_EXTENSIONS + (".yaml", ".yml", ".py", ".html", ".css", ".js")
SEARCH_MAX_FILE_BYTES = 2 * 1024 * 1024
SEARCH_SNIPPET_WORD_RADIUS = 30  # words kept before/after the first match -- ~60 words total


def _parse_search_terms(q):
    """Splits a raw query string on commas only -- spaces inside a term are
    literal, so a phrase like 'climate change' typed without a comma stays
    one term. Shared by the scoped and global search routes so term-parsing
    can't drift between them."""
    return [t.strip() for t in (q or "").split(",") if t.strip()]


def _iter_searchable_files(project_path, max_files_scanned=None):
    """Walks project_path directly (same skip-dir/dotfile rules as
    list_project_files) rather than going through that function's eager,
    fully-sorted list -- so a max_files_scanned cap can stop the walk itself
    early on a huge project, instead of only capping after an unbounded
    os.walk already paid for the full directory tree."""
    root = Path(project_path)
    yielded = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in PROJECT_FILE_SKIP_DIRS and not d.startswith(".")
        ]
        for fn in filenames:
            if fn.startswith("."):
                continue
            if not fn.lower().endswith(SEARCH_TEXT_EXTENSIONS):
                continue
            abs_path = Path(dirpath) / fn
            try:
                if os.path.getsize(abs_path) > SEARCH_MAX_FILE_BYTES:
                    continue
            except OSError:
                continue
            yield {
                "rel_path": str(abs_path.relative_to(root)).replace("\\", "/"),
                "abs_path": str(abs_path),
            }
            yielded += 1
            if max_files_scanned is not None and yielded >= max_files_scanned:
                return


def _merge_ranges(ranges):
    """Merges overlapping/adjacent [start, end) ranges so multi-term matches
    (e.g. 'cat' and 'category' hitting the same spot) don't produce malformed
    nested <mark> tags on the frontend."""
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [list(ranges[0])]
    for start, end in ranges[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [tuple(r) for r in merged]


def _find_all(haystack_lower, needle_lower):
    positions = []
    if not needle_lower:
        return positions
    start = 0
    while True:
        idx = haystack_lower.find(needle_lower, start)
        if idx == -1:
            break
        positions.append(idx)
        start = idx + len(needle_lower)
    return positions


def _build_snippet(line, terms_lower):
    """Builds one snippet of ~SEARCH_SNIPPET_WORD_RADIUS*2 words centered on
    the first matched term on this line (word-based, not char-based, so a
    reader gets enough surrounding sentence to understand the hit), with
    highlight_ranges as offsets into the *snippet* (not the original line)."""
    line_lower = line.lower()
    all_ranges = []
    first_start = None
    for term_lower in terms_lower:
        for pos in _find_all(line_lower, term_lower):
            all_ranges.append((pos, pos + len(term_lower)))
            if first_start is None or pos < first_start:
                first_start = pos
    if first_start is None:
        return None

    tokens = list(re.finditer(r"\S+", line))
    if not tokens:
        return None
    match_word_idx = next(
        (i for i, tok in enumerate(tokens) if tok.end() > first_start), len(tokens) - 1
    )
    start_word = max(0, match_word_idx - SEARCH_SNIPPET_WORD_RADIUS)
    end_word = min(len(tokens), match_word_idx + SEARCH_SNIPPET_WORD_RADIUS + 1)
    start = tokens[start_word].start()
    end = tokens[end_word - 1].end()

    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(line) else ""
    snippet = prefix + line[start:end] + suffix
    offset = start - len(prefix)
    ranges_in_snippet = []
    for r_start, r_end in all_ranges:
        s = r_start - offset
        e = r_end - offset
        if e <= 0 or s >= len(snippet):
            continue
        ranges_in_snippet.append((max(0, s), min(len(snippet), e)))
    return snippet, _merge_ranges(ranges_in_snippet)


def _passes_refinement(rel_path_lower, text_lower, include_lower, exclude_lower):
    """The include/exclude refinement fields apply on top of the main query,
    testing filename (full rel_path, not just the basename -- so excluding
    'drafts' can drop a whole subfolder) OR content. A file is dropped if any
    exclude term hits either; if include terms are given, every one of them
    must hit filename-or-content for the file to survive."""
    if exclude_lower and any(t in rel_path_lower or t in text_lower for t in exclude_lower):
        return False
    if include_lower and not all(t in rel_path_lower or t in text_lower for t in include_lower):
        return False
    return True


def _read_text_lower_safe(abs_path):
    try:
        return Path(abs_path).read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return ""


def _search_filenames(project_path, terms_lower, combine, max_file_results, include_lower, exclude_lower):
    """Files tab: matches the *filename* only (not content) against the main
    query terms -- cheap enough to run over every file in the project
    regardless of scope, no content read needed unless include/exclude terms
    are set, in which case only the already-name-matched candidates get their
    content read to test the refinement."""
    files_out = []
    files_truncated = False
    needs_content = bool(include_lower) or bool(exclude_lower)
    for f in list_project_files(project_path):
        rel_path_lower = f["rel_path"].lower()
        name_lower = Path(f["rel_path"]).name.lower()
        if not combine(term in name_lower for term in terms_lower):
            continue
        if needs_content:
            text_lower = _read_text_lower_safe(f["abs_path"])
            if not _passes_refinement(rel_path_lower, text_lower, include_lower, exclude_lower):
                continue
        if len(files_out) >= max_file_results:
            files_truncated = True
            break
        files_out.append({"rel_path": f["rel_path"], "abs_path": f["abs_path"]})
    return files_out, files_truncated


def search_project_text(project_path, terms, mode="and", max_file_results=200,
                         max_snippets_per_file=5, max_total_snippets=500, max_files_scanned=None,
                         include_terms=None, exclude_terms=None):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    if not terms:
        return {"files": [], "snippets": [], "files_truncated": False, "snippets_truncated": False}

    terms_lower = [t.lower() for t in terms]
    combine = all if mode == "and" else any
    include_lower = [t.lower() for t in (include_terms or [])]
    exclude_lower = [t.lower() for t in (exclude_terms or [])]

    files_out, files_truncated = _search_filenames(
        project_path, terms_lower, combine, max_file_results, include_lower, exclude_lower
    )

    snippets_out = []
    snippets_truncated = False
    scanned = 0

    for f in _iter_searchable_files(project_path, max_files_scanned=max_files_scanned):
        scanned += 1
        try:
            text = Path(f["abs_path"]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        text_lower = text.lower()
        if not combine(term in text_lower for term in terms_lower):
            continue
        if not _passes_refinement(f["rel_path"].lower(), text_lower, include_lower, exclude_lower):
            continue

        file_snippets = []
        for line_no, line in enumerate(text.split("\n"), start=1):
            if len(file_snippets) >= max_snippets_per_file:
                break
            built = _build_snippet(line, terms_lower)
            if built is None:
                continue
            snippet, ranges = built
            file_snippets.append({
                "rel_path": f["rel_path"],
                "abs_path": f["abs_path"],
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

    if max_files_scanned is not None and scanned >= max_files_scanned:
        snippets_truncated = True

    return {
        "files": files_out,
        "snippets": snippets_out,
        "files_truncated": files_truncated,
        "snippets_truncated": snippets_truncated,
    }


def _load_lit_module():
    """dashboard/server/lit.py, imported lazily (like search_all_projects_text
    does for db.py) to avoid a hard import-order dependency between sibling
    server modules."""
    import lit as dashboard_lit
    return dashboard_lit


def search_project_abstracts(project_path, terms, mode="and", include_terms=None, exclude_terms=None,
                              max_results=200):
    """Abstracts tab: searches a project's arti-lit.db bibliography (title/
    citation/journal/abstract text) -- but only reads it if the DB already
    exists. Deliberately does NOT call lit.list_references (which runs
    init_db() and would create literature/arti-lit.db as a side effect of
    merely searching) when the project has never used ARTi-ref/arti-lit."""
    db_path = Path(project_path) / "literature" / "arti-lit.db"
    if not db_path.exists():
        return {"available": False, "entries": []}

    terms_lower = [t.lower() for t in terms]
    combine = all if mode == "and" else any
    include_lower = [t.lower() for t in (include_terms or [])]
    exclude_lower = [t.lower() for t in (exclude_terms or [])]

    lit_mod = _load_lit_module()
    rows = lit_mod.list_references(project_path)

    entries_out = []
    for r in rows:
        haystack = " ".join(
            str(r.get(f) or "") for f in ("citation", "key", "abstract", "journal_name", "used_in")
        ).lower()
        if not combine(term in haystack for term in terms_lower):
            continue
        if not _passes_refinement(haystack, "", include_lower, exclude_lower):
            continue

        abstract_flat = " ".join((r.get("abstract") or "").split())
        built = _build_snippet(abstract_flat, terms_lower) if abstract_flat else None
        snippet, ranges = built if built else (None, [])
        entries_out.append({
            "key": r.get("key"),
            "citation": r.get("citation"),
            "doi": r.get("doi"),
            "journal_name": r.get("journal_name"),
            "read_status": r.get("read_status"),
            "local_file": r.get("local_file"),
            "abstract_snippet": snippet,
            "highlight_ranges": [list(x) for x in ranges] if ranges else [],
        })
        if len(entries_out) >= max_results:
            break

    return {"available": True, "entries": entries_out}


def search_all_projects_text(terms, mode="and", per_project_file_cap=50, per_project_snippet_cap=20,
                              global_file_cap=300, global_snippet_cap=300, per_project_scan_cap=60,
                              include_terms=None, exclude_terms=None):
    db = _load_arti_db_module_for_projects()
    projects = db.list_projects()

    files_out, snippets_out = [], []
    files_truncated = snippets_truncated = False

    for p in projects:
        if len(files_out) >= global_file_cap:
            files_truncated = True
            break
        project_path = p.get("path") or p.get("project_path")
        project_name = p.get("name") or p.get("topic")
        if not project_path:
            continue
        try:
            result = search_project_text(
                project_path, terms, mode,
                max_file_results=per_project_file_cap,
                max_snippets_per_file=5,
                max_total_snippets=per_project_snippet_cap,
                max_files_scanned=per_project_scan_cap,
                include_terms=include_terms,
                exclude_terms=exclude_terms,
            )
        except ValueError:
            continue

        for f in result["files"]:
            if len(files_out) >= global_file_cap:
                files_truncated = True
                break
            f = dict(f, project_path=project_path, project_name=project_name)
            files_out.append(f)
        for s in result["snippets"]:
            if len(snippets_out) >= global_snippet_cap:
                snippets_truncated = True
                break
            s = dict(s, project_path=project_path, project_name=project_name)
            snippets_out.append(s)
        files_truncated = files_truncated or result["files_truncated"]
        snippets_truncated = snippets_truncated or result["snippets_truncated"]

    return {
        "files": files_out,
        "snippets": snippets_out,
        "files_truncated": files_truncated,
        "snippets_truncated": snippets_truncated,
    }


def _load_arti_db_module_for_projects():
    """db.py (dashboard/server/db.py) owns list_projects(); imported lazily
    here to avoid a hard import-order dependency between the two sibling
    server modules."""
    import db as dashboard_db
    return dashboard_db


def update_session(session_id, name=None, system_role=None, temperature=None, project_id=_UNSET, model_id=_UNSET,
                    files_position=None, cross_session_position=None):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            fields, values = [], []
            if name is not None:
                fields.append("name = ?")
                values.append(name)
            if system_role is not None:
                fields.append("system_role = ?")
                values.append(system_role)
            if temperature is not None:
                fields.append("temperature = ?")
                values.append(temperature)
            if project_id is not _UNSET:
                fields.append("project_id = ?")
                values.append(project_id)
                folder = conn.execute(
                    "SELECT linked_project_path FROM chat_projects WHERE id = ?", (project_id,)
                ).fetchone() if project_id else None
                fields.append("linked_project_path = ?")
                values.append(folder["linked_project_path"] if folder else None)
            if model_id is not _UNSET:
                fields.append("model_id = ?")
                values.append(model_id)
            if files_position is not None:
                fields.append("files_position = ?")
                values.append(files_position)
            if cross_session_position is not None:
                fields.append("cross_session_position = ?")
                values.append(cross_session_position)
            if fields:
                fields.append("updated_at = ?")
                values.append(_now())
                values.append(session_id)
                conn.execute(f"UPDATE chat_sessions SET {', '.join(fields)} WHERE id = ?", values)
                conn.commit()
            row = conn.execute(
                "SELECT s.id, s.name, s.created_at, s.updated_at, s.system_role, s.temperature, "
                "s.project_id, s.linked_project_path, s.model_id, s.files_position, s.cross_session_position, "
                "p.name as project_name, "
                "p.color as project_color, m.name as model_name "
                "FROM chat_sessions s LEFT JOIN chat_projects p ON s.project_id = p.id "
                "LEFT JOIN chat_models m ON s.model_id = m.id WHERE s.id = ?",
                (session_id,),
            ).fetchone()
            return arti_db._row_to_dict(row)
        finally:
            conn.close()


def delete_session(session_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()


def _touch_session(conn, session_id):
    conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (_now(), session_id))


# ---------------------------------------------------------------------------
# messages
# ---------------------------------------------------------------------------

def list_messages(session_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            rows = conn.execute(
                "SELECT id, session_id, role, content, is_context, tokens_used, created_at, sort_order "
                "FROM chat_messages WHERE session_id = ? ORDER BY sort_order, created_at",
                (session_id,),
            ).fetchall()
            result = []
            for row in rows:
                d = arti_db._row_to_dict(row)
                try:
                    d["content"] = json.loads(d["content"])
                except (json.JSONDecodeError, TypeError):
                    pass
                result.append(d)
            return result
        finally:
            conn.close()


def _next_sort_order(conn, session_id):
    row = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) AS m FROM chat_messages WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row["m"] + 10


def add_message(session_id, role, content, is_context=1, tokens_used=0):
    content_json = json.dumps(content) if isinstance(content, (list, dict)) else content
    now = _now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            sort_order = _next_sort_order(conn, session_id)
            cur = conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, is_context, tokens_used, created_at, sort_order) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, role, content_json, is_context, tokens_used, now, sort_order),
            )
            _touch_session(conn, session_id)
            conn.commit()
            message_id = cur.lastrowid
        finally:
            conn.close()
    return {
        "id": message_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "is_context": is_context,
        "tokens_used": tokens_used,
        "created_at": now,
        "sort_order": sort_order,
    }


def update_message(message_id, content=None, is_context=None):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            fields, values = [], []
            if content is not None:
                content_json = json.dumps(content) if isinstance(content, (list, dict)) else content
                fields.append("content = ?")
                values.append(content_json)
            if is_context is not None:
                fields.append("is_context = ?")
                values.append(is_context)
            if fields:
                values.append(message_id)
                conn.execute(f"UPDATE chat_messages SET {', '.join(fields)} WHERE id = ?", values)
                conn.commit()
            row = conn.execute(
                "SELECT id, session_id, role, content, is_context, tokens_used, created_at, sort_order "
                "FROM chat_messages WHERE id = ?",
                (message_id,),
            ).fetchone()
            if row is None:
                return None
            d = arti_db._row_to_dict(row)
            try:
                d["content"] = json.loads(d["content"])
            except (json.JSONDecodeError, TypeError):
                pass
            return d
        finally:
            conn.close()


def delete_message(message_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            conn.execute("DELETE FROM chat_messages WHERE id = ?", (message_id,))
            conn.commit()
        finally:
            conn.close()


def bulk_add_messages(session_id, messages):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            sort_order = _next_sort_order(conn, session_id) - 10
            for msg in messages:
                content = msg.get("content", "")
                content_json = json.dumps(content) if isinstance(content, (list, dict)) else content
                sort_order += 10
                conn.execute(
                    "INSERT INTO chat_messages (session_id, role, content, is_context, tokens_used, created_at, sort_order) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (session_id, msg.get("role", "user"), content_json,
                     msg.get("is_context", 1), msg.get("tokens_used", 0), _now(), sort_order),
                )
            _touch_session(conn, session_id)
            conn.commit()
        finally:
            conn.close()
    return len(messages)


def reorder_messages(session_id, ordered_ids):
    """Renumbers the given message ids to 10, 20, 30, ... in the order given.
    Validates every id belongs to session_id; returns None on any mismatch
    (unknown id, or a session id missing from ordered_ids) without touching
    the table. Rows not included in ordered_ids are left untouched."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            existing_ids = {
                r["id"] for r in conn.execute(
                    "SELECT id FROM chat_messages WHERE session_id = ?", (session_id,)
                ).fetchall()
            }
            if not ordered_ids or set(ordered_ids) - existing_ids:
                return None
            for i, msg_id in enumerate(ordered_ids):
                conn.execute(
                    "UPDATE chat_messages SET sort_order = ? WHERE id = ? AND session_id = ?",
                    ((i + 1) * 10, msg_id, session_id),
                )
            _touch_session(conn, session_id)
            conn.commit()
        finally:
            conn.close()
    return list_messages(session_id)


# ---------------------------------------------------------------------------
# templates
# ---------------------------------------------------------------------------

def list_templates():
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            rows = conn.execute("SELECT * FROM chat_templates ORDER BY name").fetchall()
            return [arti_db._row_to_dict(r) for r in rows]
        finally:
            conn.close()


def create_template(name, content):
    name, content = (name or "").strip(), (content or "").strip()
    if not name:
        raise ValueError("Template name is required")
    if not content:
        raise ValueError("Template content is required")
    now = _now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            if conn.execute("SELECT id FROM chat_templates WHERE name = ?", (name,)).fetchone():
                raise ValueError("A template with this name already exists")
            cur = conn.execute(
                "INSERT INTO chat_templates (name, content, created_at) VALUES (?, ?, ?)",
                (name, content, now),
            )
            conn.commit()
            return arti_db._row_to_dict(
                conn.execute("SELECT * FROM chat_templates WHERE id = ?", (cur.lastrowid,)).fetchone()
            )
        finally:
            conn.close()


def update_template(template_id, name=None, content=None):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            fields, values = [], []
            if name is not None:
                name = name.strip()
                if not name:
                    raise ValueError("Template name cannot be empty")
                if conn.execute(
                    "SELECT id FROM chat_templates WHERE name = ? AND id != ?", (name, template_id)
                ).fetchone():
                    raise ValueError("A template with this name already exists")
                fields.append("name = ?")
                values.append(name)
            if content is not None:
                content = content.strip()
                if not content:
                    raise ValueError("Template content cannot be empty")
                fields.append("content = ?")
                values.append(content)
            if fields:
                values.append(template_id)
                conn.execute(f"UPDATE chat_templates SET {', '.join(fields)} WHERE id = ?", values)
                conn.commit()
            row = conn.execute("SELECT * FROM chat_templates WHERE id = ?", (template_id,)).fetchone()
            return arti_db._row_to_dict(row)
        finally:
            conn.close()


def delete_template(template_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            conn.execute("DELETE FROM chat_templates WHERE id = ?", (template_id,))
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# skills
# ---------------------------------------------------------------------------

def list_skills():
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            rows = conn.execute("SELECT * FROM chat_skills ORDER BY name").fetchall()
            return [arti_db._row_to_dict(r) for r in rows]
        finally:
            conn.close()


def create_skill(name, description, content):
    name, content = (name or "").strip(), (content or "").strip()
    description = (description or "").strip() or None
    if not name:
        raise ValueError("Skill name is required")
    if not content:
        raise ValueError("Skill content is required")
    now = _now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            if conn.execute("SELECT id FROM chat_skills WHERE name = ?", (name,)).fetchone():
                raise ValueError("A skill with this name already exists")
            cur = conn.execute(
                "INSERT INTO chat_skills (name, description, content, created_at) VALUES (?, ?, ?, ?)",
                (name, description, content, now),
            )
            conn.commit()
            return arti_db._row_to_dict(
                conn.execute("SELECT * FROM chat_skills WHERE id = ?", (cur.lastrowid,)).fetchone()
            )
        finally:
            conn.close()


def update_skill(skill_id, name=None, description=None, content=None):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            fields, values = [], []
            if name is not None:
                name = name.strip()
                if not name:
                    raise ValueError("Skill name cannot be empty")
                if conn.execute(
                    "SELECT id FROM chat_skills WHERE name = ? AND id != ?", (name, skill_id)
                ).fetchone():
                    raise ValueError("A skill with this name already exists")
                fields.append("name = ?")
                values.append(name)
            if description is not None:
                fields.append("description = ?")
                values.append(description.strip() or None)
            if content is not None:
                content = content.strip()
                if not content:
                    raise ValueError("Skill content cannot be empty")
                fields.append("content = ?")
                values.append(content)
            if fields:
                values.append(skill_id)
                conn.execute(f"UPDATE chat_skills SET {', '.join(fields)} WHERE id = ?", values)
                conn.commit()
            row = conn.execute("SELECT * FROM chat_skills WHERE id = ?", (skill_id,)).fetchone()
            return arti_db._row_to_dict(row)
        finally:
            conn.close()


def delete_skill(skill_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            conn.execute("DELETE FROM chat_session_skills WHERE skill_id = ?", (skill_id,))
            conn.execute("DELETE FROM chat_skills WHERE id = ?", (skill_id,))
            conn.commit()
        finally:
            conn.close()


def list_session_skills(session_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            rows = conn.execute(
                "SELECT s.* FROM chat_skills s "
                "JOIN chat_session_skills ss ON ss.skill_id = s.id "
                "WHERE ss.session_id = ? ORDER BY s.name",
                (session_id,),
            ).fetchall()
            return [arti_db._row_to_dict(r) for r in rows]
        finally:
            conn.close()


def attach_skill_to_session(session_id, skill_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO chat_session_skills (session_id, skill_id, created_at) "
                "VALUES (?, ?, ?)",
                (session_id, skill_id, _now()),
            )
            conn.commit()
        finally:
            conn.close()


def detach_skill_from_session(session_id, skill_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            conn.execute(
                "DELETE FROM chat_session_skills WHERE session_id = ? AND skill_id = ?",
                (session_id, skill_id),
            )
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# system roles
# ---------------------------------------------------------------------------

def list_system_roles():
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            rows = conn.execute("SELECT * FROM chat_system_roles ORDER BY name").fetchall()
            return [arti_db._row_to_dict(r) for r in rows]
        finally:
            conn.close()


def create_system_role(name, content, is_default=0):
    name, content = (name or "").strip(), (content or "").strip()
    if not name:
        raise ValueError("System role name is required")
    if not content:
        raise ValueError("System role content is required")
    now = _now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            if conn.execute("SELECT id FROM chat_system_roles WHERE name = ?", (name,)).fetchone():
                raise ValueError("A system role with this name already exists")
            if is_default:
                conn.execute("UPDATE chat_system_roles SET is_default = 0")
            cur = conn.execute(
                "INSERT INTO chat_system_roles (name, content, is_default, created_at) VALUES (?, ?, ?, ?)",
                (name, content, 1 if is_default else 0, now),
            )
            conn.commit()
            return arti_db._row_to_dict(
                conn.execute("SELECT * FROM chat_system_roles WHERE id = ?", (cur.lastrowid,)).fetchone()
            )
        finally:
            conn.close()


def update_system_role(role_id, name=None, content=None, is_default=None):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            fields, values = [], []
            if name is not None:
                name = name.strip()
                if not name:
                    raise ValueError("System role name cannot be empty")
                if conn.execute(
                    "SELECT id FROM chat_system_roles WHERE name = ? AND id != ?", (name, role_id)
                ).fetchone():
                    raise ValueError("A system role with this name already exists")
                fields.append("name = ?")
                values.append(name)
            if content is not None:
                content = content.strip()
                if not content:
                    raise ValueError("System role content cannot be empty")
                fields.append("content = ?")
                values.append(content)
            if is_default is not None:
                if is_default:
                    conn.execute("UPDATE chat_system_roles SET is_default = 0 WHERE id != ?", (role_id,))
                fields.append("is_default = ?")
                values.append(1 if is_default else 0)
            if fields:
                values.append(role_id)
                conn.execute(f"UPDATE chat_system_roles SET {', '.join(fields)} WHERE id = ?", values)
                conn.commit()
            row = conn.execute("SELECT * FROM chat_system_roles WHERE id = ?", (role_id,)).fetchone()
            return arti_db._row_to_dict(row)
        finally:
            conn.close()


def delete_system_role(role_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            conn.execute("DELETE FROM chat_system_roles WHERE id = ?", (role_id,))
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# models
# ---------------------------------------------------------------------------

def list_models():
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            rows = conn.execute("SELECT * FROM chat_models ORDER BY name").fetchall()
            return [arti_db._row_to_dict(r) for r in rows]
        finally:
            conn.close()


def create_model(name, api_key, base_url=None):
    name, api_key = (name or "").strip(), (api_key or "").strip()
    if not name:
        raise ValueError("Model name is required")
    if not api_key:
        raise ValueError("API key is required")
    base_url = (base_url or "").strip() or None
    now = _now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            if conn.execute("SELECT id FROM chat_models WHERE name = ?", (name,)).fetchone():
                raise ValueError("A model with this name already exists")
            cur = conn.execute(
                "INSERT INTO chat_models (name, api_key, base_url, created_at) VALUES (?, ?, ?, ?)",
                (name, api_key, base_url, now),
            )
            conn.commit()
            return arti_db._row_to_dict(
                conn.execute("SELECT * FROM chat_models WHERE id = ?", (cur.lastrowid,)).fetchone()
            )
        finally:
            conn.close()


def update_model(model_id, name=None, api_key=None, base_url=None):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            fields, values = [], []
            if name is not None:
                name = name.strip()
                if not name:
                    raise ValueError("Model name cannot be empty")
                if conn.execute(
                    "SELECT id FROM chat_models WHERE name = ? AND id != ?", (name, model_id)
                ).fetchone():
                    raise ValueError("A model with this name already exists")
                fields.append("name = ?")
                values.append(name)
            if api_key is not None:
                api_key = api_key.strip()
                if not api_key:
                    raise ValueError("API key cannot be empty")
                fields.append("api_key = ?")
                values.append(api_key)
            if base_url is not None:
                fields.append("base_url = ?")
                values.append(base_url.strip() or None)
            if fields:
                values.append(model_id)
                conn.execute(f"UPDATE chat_models SET {', '.join(fields)} WHERE id = ?", values)
                conn.commit()
            row = conn.execute("SELECT * FROM chat_models WHERE id = ?", (model_id,)).fetchone()
            return arti_db._row_to_dict(row)
        finally:
            conn.close()


def delete_model(model_id):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            current = conn.execute("SELECT value FROM chat_settings WHERE key = 'chat_model_id'").fetchone()
            if current and str(current["value"]) == str(model_id):
                raise ValueError("Cannot delete the model currently selected as default")
            conn.execute("DELETE FROM chat_models WHERE id = ?", (model_id,))
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# settings (chat_model_id, pdf_summary_prompt, ...)
# ---------------------------------------------------------------------------

def get_settings():
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            rows = conn.execute("SELECT key, value FROM chat_settings").fetchall()
            result = {r["key"]: r["value"] for r in rows}
        finally:
            conn.close()
    result.setdefault("pdf_summary_prompt", DEFAULT_PDF_SUMMARY_PROMPT)
    return result


def update_settings(data):
    now = _now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            for key, value in data.items():
                conn.execute(
                    "INSERT INTO chat_settings (key, value, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                    (key, str(value) if value is not None else None, now),
                )
            conn.commit()
        finally:
            conn.close()


def _get_default_model_row(conn):
    setting = conn.execute("SELECT value FROM chat_settings WHERE key = 'chat_model_id'").fetchone()
    if setting and setting["value"]:
        row = conn.execute("SELECT * FROM chat_models WHERE id = ?", (setting["value"],)).fetchone()
        if row:
            return row
    return conn.execute("SELECT * FROM chat_models ORDER BY id LIMIT 1").fetchone()


def _get_session_model_row(conn, session_model_id):
    """A session's own `model_id` (set via the session's Edit modal) overrides
    the app-wide default model, falling back to it when unset."""
    if session_model_id:
        row = conn.execute("SELECT * FROM chat_models WHERE id = ?", (session_model_id,)).fetchone()
        if row:
            return row
    return _get_default_model_row(conn)


def _make_client(model_row):
    from openai import OpenAI
    kwargs = {"api_key": model_row["api_key"]}
    if model_row["base_url"]:
        kwargs["base_url"] = model_row["base_url"]
    return OpenAI(**kwargs)


# ---------------------------------------------------------------------------
# token estimation
# ---------------------------------------------------------------------------

def estimate_tokens(session_ids, model):
    import tiktoken
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")

    total_tokens = 0
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            for session_id in session_ids:
                session = conn.execute(
                    "SELECT system_role FROM chat_sessions WHERE id = ?", (session_id,)
                ).fetchone()
                if session and session["system_role"]:
                    total_tokens += len(encoding.encode(session["system_role"]))
                messages = conn.execute(
                    "SELECT role, content FROM chat_messages WHERE session_id = ? AND is_context = 1 "
                    "ORDER BY created_at",
                    (session_id,),
                ).fetchall()
                for msg in messages:
                    total_tokens += len(encoding.encode(msg["content"])) + 4

            # Skills are a per-session toggle on the primary session only, never on
            # sessions merged in via context_session_ids -- session_ids[0] is always
            # the primary session (the frontend's only caller builds this list as
            # [chatCurrentSessionId].concat(chatContextSessionIds)).
            if session_ids:
                skill_rows = conn.execute(
                    "SELECT sk.name, sk.content FROM chat_skills sk "
                    "JOIN chat_session_skills ss ON ss.skill_id = sk.id "
                    "WHERE ss.session_id = ?",
                    (session_ids[0],),
                ).fetchall()
                for skill in skill_rows:
                    text = f"# Skill: {skill['name']}\n\n{skill['content']}"
                    total_tokens += len(encoding.encode(text)) + 4
        finally:
            conn.close()
    return total_tokens


# ---------------------------------------------------------------------------
# streaming chat
# ---------------------------------------------------------------------------

def _assemble_context_messages(conn, session_id, context_session_ids):
    """Builds the exact system+context message list that stream_chat() sends
    to the model (minus the trailing user message) -- shared with
    preview_context() so "Inspect context" shows the real thing, not a
    separate reimplementation that can drift out of sync."""
    session = conn.execute(
        "SELECT system_role, files_position, cross_session_position "
        "FROM chat_sessions WHERE id = ?",
        (session_id,),
    ).fetchone()
    if not session:
        return None
    system_role = session["system_role"] or DEFAULT_SYSTEM_ROLE
    files_position = session["files_position"] or "before"
    cross_session_position = session["cross_session_position"] or "before"

    # Skills attach only to the primary session being typed into, never to
    # sessions merged in via context_session_ids.
    skill_rows = conn.execute(
        "SELECT sk.name, sk.content FROM chat_skills sk "
        "JOIN chat_session_skills ss ON ss.skill_id = sk.id "
        "WHERE ss.session_id = ? ORDER BY sk.name",
        (session_id,),
    ).fetchall()

    own_rows = conn.execute(
        "SELECT role, content, created_at FROM chat_messages "
        "WHERE session_id = ? AND is_context = 1 ORDER BY sort_order, created_at",
        (session_id,),
    ).fetchall()
    main_rows = [r for r in own_rows if not r["content"].startswith("# File: ")]
    file_rows = [r for r in own_rows if r["content"].startswith("# File: ")]

    cross_rows = []
    for sid in context_session_ids:
        rows = conn.execute(
            "SELECT role, content, created_at FROM chat_messages "
            "WHERE session_id = ? AND is_context = 1 ORDER BY created_at",
            (sid,),
        ).fetchall()
        cross_rows.extend(rows)
    cross_rows.sort(key=lambda r: r["created_at"])

    def to_msgs(rows):
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    files_block = to_msgs(file_rows)
    cross_block = to_msgs(cross_rows)
    main_block = to_msgs(main_rows)

    # Fixed tie-break when both land on the same side: files before cross-session.
    before_blocks, after_blocks = [], []
    (before_blocks if files_position == "before" else after_blocks).append(files_block)
    (before_blocks if cross_session_position == "before" else after_blocks).append(cross_block)

    messages = [{"role": "system", "content": system_role}]
    for skill in skill_rows:
        messages.append({"role": "system", "content": f"# Skill: {skill['name']}\n\n{skill['content']}"})
    for block in before_blocks:
        messages.extend(block)
    messages.extend(main_block)
    for block in after_blocks:
        messages.extend(block)
    return messages


def preview_context(session_id, context_session_ids=None):
    """Returns the assembled system+context messages for inspection, without
    calling the model. Used by the chat UI's "Inspect context" button."""
    context_session_ids = context_session_ids or []
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            messages = _assemble_context_messages(conn, session_id, context_session_ids)
        finally:
            conn.close()
    if messages is None:
        raise ValueError("Session not found")
    return messages


def stream_chat(session_id, content, context_session_ids=None):
    """Generator yielding (event_type, payload) tuples: 'content' (str chunk),
    'tokens_used' (int), 'error' (str), 'done' (None). Ports fine-ai-chat's
    server.py chat()/generate() context-assembly + streaming call, but yields
    structured events instead of writing SSE strings -- the caller (server.py's
    HTTP handler) controls the wire format."""
    context_session_ids = context_session_ids or []
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            session = conn.execute(
                "SELECT system_role, temperature, model_id FROM chat_sessions WHERE id = ?", (session_id,)
            ).fetchone()
            if not session:
                yield ("error", "Session not found")
                return
            temperature = session["temperature"] if session["temperature"] is not None else 0.7

            model_row = _get_session_model_row(conn, session["model_id"])
            if not model_row:
                yield ("error", "No chat model configured. Add one in Settings.")
                return

            messages = _assemble_context_messages(conn, session_id, context_session_ids)
        finally:
            conn.close()

    messages.append({"role": "user", "content": content})

    model_name = model_row["name"]
    temperature = 1.0 if model_name.startswith("gpt-5") else temperature

    try:
        client = _make_client(model_row)
    except Exception as e:
        yield ("error", f"Failed to configure model client: {e}")
        return

    try:
        response = client.chat.completions.create(
            model=model_name, messages=messages, stream=True, temperature=temperature
        )
    except Exception as e:
        yield ("error", f"API call failed: {e}")
        return

    full_content = ""
    tokens_used = 0
    try:
        for chunk in response:
            if getattr(chunk, "choices", None):
                delta = chunk.choices[0].delta
                part = getattr(delta, "content", None)
                if part:
                    full_content += part
                    yield ("content", part)
            usage = getattr(chunk, "usage", None)
            if usage:
                tokens_used = getattr(usage, "total_tokens", tokens_used)
    except Exception as e:
        yield ("error", f"Streaming error: {e}")
        return

    yield ("tokens_used", tokens_used)
    yield ("done", None)

    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _touch_session(conn, session_id)
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# PDF summarization (non-streaming, one shot -- called by ArtiPDF's
# "Summarize with AI" context-menu tool over HTTP)
# ---------------------------------------------------------------------------

def _run_summary_completion(client, model_name, prompt, text):
    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": text}]
    response = client.chat.completions.create(
        model=model_name, messages=messages, stream=False, temperature=0.7
    )
    summary = response.choices[0].message.content
    tokens_used = response.usage.total_tokens if getattr(response, "usage", None) else 0
    return summary, tokens_used


def summarize_pdf_text(text, filename=None):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            model_row = _get_default_model_row(conn)
            prompt_setting = conn.execute(
                "SELECT value FROM chat_settings WHERE key = 'pdf_summary_prompt'"
            ).fetchone()
        finally:
            conn.close()

    if not model_row:
        raise RuntimeError("No chat model configured. Add one in the dashboard's Settings panel.")

    prompt = (prompt_setting["value"] if prompt_setting and prompt_setting["value"] else DEFAULT_PDF_SUMMARY_PROMPT)

    client = _make_client(model_row)
    summary, tokens_used = _run_summary_completion(client, model_row["name"], prompt, text)
    return summary, tokens_used, model_row["name"]


# ---------------------------------------------------------------------------
# bulk PDF extraction / summarization (Project Files panel bulk actions)
# ---------------------------------------------------------------------------

def _ensure_extracted_markdown(pdf_abs_path):
    """Returns (markdown_path, was_cached). Writes <stem>.md next to the PDF if it
    doesn't already exist; reuses it otherwise instead of re-running OCR/pdfminer."""
    md_path = pdf_abs_path.with_suffix(".md")
    if md_path.exists():
        return md_path, True
    text = _extract_pdf_text(str(pdf_abs_path))
    md_path.write_text(text, encoding="utf-8")
    return md_path, False


def bulk_extract_pdfs(project_path, rel_paths):
    """Generator yielding ready-made SSE event dicts. Extraction only -- no
    summarization/model call. Never aborts the whole batch on a per-file error."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()

    root = Path(project_path)
    for rel_path in rel_paths:
        if not rel_path.lower().endswith(".pdf"):
            yield {"type": "file_error", "rel_path": rel_path, "error": "Not a PDF -- skipped"}
            continue
        try:
            abs_path = _resolve_under_project(project_path, str(root / rel_path))
            yield {"type": "log", "message": f"Extracting {rel_path}..."}
            md_path, was_cached = _ensure_extracted_markdown(abs_path)
            if was_cached:
                yield {"type": "log", "message": f"Using existing extracted text for {rel_path}"}
            output_rel = str(md_path.relative_to(root.resolve())).replace("\\", "/")
            yield {"type": "file_done", "rel_path": rel_path, "output": output_rel}
        except Exception as e:
            yield {"type": "file_error", "rel_path": rel_path, "error": str(e)}
    yield {"type": "done"}


def bulk_summarize_files(project_path, rel_paths):
    """Generator yielding ready-made SSE event dicts, same shape convention as
    bulk_extract_pdfs. Summarizes each selected .pdf/.md file, extracting the
    PDF to markdown first (reusing a cached extraction) when needed."""
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
            model_row = _get_default_model_row(conn)
            prompt_setting = conn.execute(
                "SELECT value FROM chat_settings WHERE key = 'pdf_summary_prompt'"
            ).fetchone()
        finally:
            conn.close()

    if not model_row:
        yield {"type": "error", "message": "No chat model configured. Add one in Settings."}
        return

    prompt = prompt_setting["value"] if prompt_setting and prompt_setting["value"] else DEFAULT_PDF_SUMMARY_PROMPT
    model_name = model_row["name"]
    client = _make_client(model_row)

    root = Path(project_path)
    for rel_path in rel_paths:
        lower = rel_path.lower()
        if not (lower.endswith(".pdf") or lower.endswith(".md")):
            yield {"type": "file_error", "rel_path": rel_path, "error": "Unsupported file type -- skipped"}
            continue
        try:
            abs_path = _resolve_under_project(project_path, str(root / rel_path))
            yield {"type": "log", "message": f"Starting {rel_path}"}
            if lower.endswith(".pdf"):
                md_path, was_cached = _ensure_extracted_markdown(abs_path)
                if was_cached:
                    yield {"type": "log", "message": f"Using existing extracted text for {rel_path}"}
                else:
                    yield {"type": "log", "message": f"Extracted text from {rel_path}"}
                text = md_path.read_text(encoding="utf-8", errors="replace")
            else:
                text = abs_path.read_text(encoding="utf-8", errors="replace")

            yield {"type": "log", "message": f"Summarizing {rel_path} with {model_name}..."}
            summary, tokens_used = _run_summary_completion(client, model_name, prompt, text)
            summary_path = abs_path.with_name(
                abs_path.stem + "_summary_" + _safe_model_slug(model_name) + ".md"
            )
            summary_path.write_text(summary, encoding="utf-8")
            output_rel = str(summary_path.relative_to(root.resolve())).replace("\\", "/")
            yield {"type": "file_done", "rel_path": rel_path, "output": output_rel, "model": model_name}
        except Exception as e:
            yield {"type": "file_error", "rel_path": rel_path, "error": str(e)}
    yield {"type": "done"}
