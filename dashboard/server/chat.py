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
from datetime import datetime
from pathlib import Path

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


arti_db = _load_arti_db()

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


def read_project_file(project_path, abs_path):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    return target.read_text(encoding="utf-8", errors="replace")


def write_project_file(project_path, abs_path, content):
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            _require_known_project_path(conn, project_path)
        finally:
            conn.close()
    target = _resolve_under_project(project_path, abs_path)
    target.write_text(content, encoding="utf-8")


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
