"""ARTi Framework dashboard server -- plain stdlib http.server, no third-party
deps. Run via the vendored ~/.arti/python interpreter; see
../start-arti-dashboard.bat / ../start-arti-dashboard.sh.

The dashboard is launcher-only: its sole data source is db.py's view over
`project_index` (~/.arti/memory/arti.db), the same table the ARTi skills read
and write for cross-project memory lookup. It never reads project-index.md,
research-idea-bank.md, or workflow-sessions/ at request time -- those are
markdown exports the skills regenerate from the database, only as fresh as
whichever skill last remembered to upsert it, which is exactly the staleness
this dashboard used to inherit when it read them directly. scaffold_project()
writes to the same row through two field-scoped calls: arti_db.project_upsert
(loaded as the `arti_db` module below) for the skills' stage/status/topic
fields, and db.upsert_project for the launcher's category/tags/lifecycle
fields -- kept as two calls rather than one merged signature to minimize
churn on either call site.
"""
import json
import re
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import chat
import db
import db_ideas
import journals
import lit
import platform_ops

HOST = "127.0.0.1"
PORT = 4174

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
ARTI_HOME = DASHBOARD_DIR.parent

HTML_PATH = DASHBOARD_DIR / "arti-dashboard.html"


arti_db = db.arti_db


def _parse_journal_from_citation(citation):
    """Best-effort fallback for pre-migration rows: library_import_ris() formats
    citation as "{authors} ({year}). {title}. {journal}." -- take the last
    non-empty segment before the final period."""
    if not citation:
        return None
    segments = [s.strip() for s in citation.strip().rstrip(".").split(". ") if s.strip()]
    return segments[-1] if len(segments) >= 2 else None


CLAUDE_TEMPLATE_PATH = (
    ARTI_HOME / "skills" / "ARTi-setup" / "references" / "project-claude-template.md"
)

# Set by app.py once it creates the native window, so /api/focus (below) has
# something to bring forward. Stays None when server.py is run standalone
# (start-arti-dashboard.bat) -- /api/focus is then a no-op that still returns ok.
_window = None


def set_window(window):
    global _window
    _window = window


def _write_if_missing(path, content):
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def scaffold_project(project_path, name):
    """Creates the standard ARTi paper-project boilerplate (folders, memory
    scaffold, root CLAUDE.md) for a freshly-created project folder -- the same
    layout ARTi-setup's Workflow B produces, so a project created from the
    dashboard is immediately usable without a researcher running that skill
    by hand first. See skills/ARTi-setup/references/project-scaffold-template.md."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    today = datetime.now().strftime("%Y-%m-%d")

    for folder in ("idea", "writing", "literature/exports", "literature/fulltext",
                   "data", "figures", "submission", "inbox", "memory"):
        (project_path / folder).mkdir(parents=True, exist_ok=True)

    _write_if_missing(
        project_path / "literature" / "search-log.md",
        "# Search Log\n\n| Query | Date | Hits | Export file | Target claim/paragraph | Status |\n"
        "|---|---|---|---|---|---|\n",
    )
    _write_if_missing(
        project_path / "literature" / "library.md",
        "# Library\n\n| Key | Full citation | DOI | Local file path | Read status | Used in |\n"
        "|---|---|---|---|---|---|\n",
    )

    def frontmatter(slug, description, tier):
        return (
            "---\n"
            f"name: {slug}\n"
            f"description: {description}\n"
            "metadata:\n"
            "  type: project\n"
            f"  tier: {tier}\n"
            f"  created: {now}\n"
            f"  updated: {now}\n"
            "---\n\n"
        )

    _write_if_missing(
        project_path / "memory" / "MEMORY.md",
        frontmatter("memory-index", f"Index of {name}'s memory files", "T0")
        + "Pointers only -- one line per memory file, added as topic files are created.\n\n"
        "## Change log\n"
        f"- {today}: project scaffolded\n",
    )
    _write_if_missing(
        project_path / "memory" / "todo-list.md",
        frontmatter("todo-list", f"Checklist of outstanding tasks for {name}", "T0")
        + "- [ ] Run ARTi-idea to develop the research idea\n",
    )
    _write_if_missing(
        project_path / "memory" / "status.md",
        frontmatter("status", f"Living current-state pointer for {name}", "T0")
        + "## Current state\n"
        f"Project scaffolded {today}. No idea work started yet.\n",
    )

    _write_if_missing(project_path / "CLAUDE.md", _claude_md(name))

    arti_db.project_upsert(
        project_path=str(project_path), topic=name, stage="Not started", status="Scaffolded"
    )
    db.upsert_project(project_path, name=name, category="Paper", touch_opened=True)


def _claude_md(name):
    """Renders the project CLAUDE.md from the canonical template owned by
    ARTi-setup (Workflow B), so the skill and this scaffolder cannot drift
    apart. The inline fallback is deliberately minimal -- scaffolding must
    never hard-fail just because the template is missing."""
    try:
        tmpl = CLAUDE_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return (
            f"# {name} -- Project Instructions\n\n"
            "ARTi research-paper project. This project's `memory/` is the single source of "
            "truth -- never read or write the default `~/.claude/projects/.../memory/` for "
            "it.\n\n"
            "Read every session: `memory/MEMORY.md`, `memory/todo-list.md`, "
            "`memory/status.md`, `~/.arti/memory/working-preferences.md`. Glob `inbox/*.md` "
            "for anything sitting untriaged.\n\n"
            "> Canonical template missing at "
            f"`{CLAUDE_TEMPLATE_PATH}` -- regenerate this file once it is restored.\n\n"
            "<!-- arti: local additions below -- preserved on regeneration -->\n"
        )
    return tmpl.replace("{{PROJECT_NAME}}", name)


def _read_framework_version():
    version_file = ARTI_HOME / "VERSION"
    try:
        for line in version_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("FRAMEWORK_VERSION="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return None


def build_data():
    return {"projects": db.list_projects(), "frameworkVersion": _read_framework_version()}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send_json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _send_sse_headers(self):
        # Chunked transfer instead of a fixed Content-Length -- BaseHTTPRequestHandler's
        # wfile supports incremental writes/flushes, so this streams like Flask's
        # Response(generate(), mimetype='text/event-stream') did in fine-ai-chat,
        # without needing a second server or thread.
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

    def _send_sse_chunk(self, data_obj):
        payload = f"data: {json.dumps(data_obj)}\n\n".encode("utf-8")
        chunk = f"{len(payload):X}\r\n".encode("ascii") + payload + b"\r\n"
        self.wfile.write(chunk)
        self.wfile.flush()

    def _end_sse(self):
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()

    def _handle_api(self, pathname):
        method = self.command

        if pathname == "/api/ping" and method == "GET":
            return self._send_json(200, {"ok": True})

        if pathname == "/api/data" and method == "GET":
            return self._send_json(200, build_data())

        if pathname == "/api/ideas" and method == "GET":
            return self._send_json(200, {"ideas": db_ideas.list_ideas()})

        if pathname == "/api/browse-folder" and method == "POST":
            try:
                chosen = platform_ops.browse_folder()
            except platform_ops.NoPickerAvailable as e:
                return self._send_json(400, {"error": str(e)})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})
            return self._send_json(200, {"path": chosen})

        if pathname == "/api/new-project" and method == "POST":
            body = self._read_body()
            parent_path, name = body.get("parentPath"), body.get("name")
            category = body.get("category") or "Paper"
            tags = body.get("tags") or []
            if not parent_path or not name:
                return self._send_json(400, {"error": "parentPath and name required"})
            try:
                project_path = Path(parent_path) / name
                project_path.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                return self._send_json(400, {"error": "a folder with that name already exists there"})
            except OSError as e:
                return self._send_json(500, {"error": str(e)})
            if category == "Paper":
                try:
                    scaffold_project(project_path, name)
                except OSError as e:
                    return self._send_json(500, {"error": f"created folder but scaffolding failed: {e}"})
            else:
                db.upsert_project(project_path, name=name, category=category, tags=tags, touch_opened=True)
            platform_ops.open_in_vscode(project_path)
            return self._send_json(200, {"path": str(project_path)})

        if pathname == "/api/projects/register" and method == "POST":
            body = self._read_body()
            p = body.get("path")
            if not p:
                return self._send_json(400, {"error": "path required"})
            project_path = Path(p)
            if not project_path.is_dir():
                return self._send_json(400, {"error": "folder does not exist"})
            name = (body.get("name") or "").strip() or project_path.name
            category = body.get("category") or "Other"
            tags = body.get("tags") or []
            db.upsert_project(project_path, name=name, category=category, tags=tags, touch_opened=True)
            platform_ops.open_in_vscode(project_path)
            return self._send_json(200, {"path": str(project_path)})

        if pathname == "/api/projects/update" and method == "POST":
            body = self._read_body()
            p = body.get("path")
            if not p:
                return self._send_json(400, {"error": "path required"})
            name = (body.get("name") or "").strip() or None
            category = (body.get("category") or "").strip() or None
            entry = db.upsert_project(p, name=name, category=category)
            return self._send_json(200, {"ok": True, "project": entry})

        if pathname == "/api/projects/lifecycle" and method == "POST":
            body = self._read_body()
            p = body.get("path")
            lifecycle = body.get("lifecycle")
            if not p or lifecycle not in db.PROJECT_LIFECYCLES:
                return self._send_json(400, {"error": "path and lifecycle (active|complete|archived) required"})
            entry = db.set_project_lifecycle(p, lifecycle)
            return self._send_json(200, {"ok": True, "lifecycle": entry["lifecycle"]})

        if pathname == "/api/open-folder" and method == "POST":
            body = self._read_body()
            p = body.get("path")
            if not p:
                return self._send_json(400, {"error": "path required"})
            platform_ops.open_in_file_manager(p)
            db.upsert_project(p, touch_opened=True)
            return self._send_json(200, {"ok": True})

        if pathname == "/api/open-vscode" and method == "POST":
            body = self._read_body()
            p = body.get("path")
            if not p:
                return self._send_json(400, {"error": "path required"})
            platform_ops.open_in_vscode(p)
            db.upsert_project(p, touch_opened=True)
            return self._send_json(200, {"ok": True})

        if pathname == "/api/open-external" and method == "POST":
            body = self._read_body()
            url = body.get("url")
            if not url or not re.match(r"^https?://", url, re.IGNORECASE):
                return self._send_json(400, {"error": "a valid http(s) url is required"})
            platform_ops.open_file_default(url)
            return self._send_json(200, {"ok": True})

        if pathname == "/api/references/list" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            p = (query.get("path") or [None])[0]
            if not p:
                return self._send_json(400, {"error": "path required"})
            try:
                rows = lit.list_references(p)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})
            return self._send_json(200, {"rows": rows})

        if pathname == "/api/references/journal-metrics" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            issn = (query.get("issn") or [None])[0]
            journal_name = (query.get("journal_name") or [None])[0]
            citation = (query.get("citation") or [None])[0]
            title = journal_name or _parse_journal_from_citation(citation)
            if not issn and not title:
                return self._send_json(400, {"error": "issn, journal_name, or citation required"})
            try:
                metrics = journals.lookup(issn=issn, title=title)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})
            return self._send_json(200, {"journal_metrics": metrics})

        if pathname == "/api/references/import" and method == "POST":
            body = self._read_body()
            p = body.get("path")
            files = body.get("files") or []
            if not p or not files:
                return self._send_json(400, {"error": "path and files required"})
            try:
                result = lit.import_ris(p, files)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})
            return self._send_json(200, result)

        if pathname == "/api/browse-files" and method == "POST":
            try:
                chosen = platform_ops.browse_files()
            except platform_ops.NoPickerAvailable as e:
                return self._send_json(400, {"error": str(e)})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})
            return self._send_json(200, {"paths": chosen})

        if pathname == "/api/chat/projects" and method == "GET":
            return self._send_json(200, {"projects": chat.list_projects()})

        if pathname == "/api/chat/projects" and method == "POST":
            body = self._read_body()
            try:
                project = chat.create_project(body.get("name"), body.get("color"))
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            return self._send_json(200, project)

        if pathname == "/api/chat/projects/update" and method == "POST":
            body = self._read_body()
            pid = body.get("id")
            if not pid:
                return self._send_json(400, {"error": "id required"})
            try:
                project = chat.update_project(pid, body.get("name"), body.get("color"))
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            if project is None:
                return self._send_json(404, {"error": "Folder not found"})
            return self._send_json(200, project)

        if pathname == "/api/chat/projects/delete" and method == "POST":
            body = self._read_body()
            pid = body.get("id")
            if not pid:
                return self._send_json(400, {"error": "id required"})
            try:
                chat.delete_project(pid)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/sessions" and method == "GET":
            return self._send_json(200, {"sessions": chat.list_sessions()})

        if pathname == "/api/chat/sessions" and method == "POST":
            body = self._read_body()
            session = chat.create_session(body.get("name"), body.get("project_id"), model_id=body.get("model_id"))
            return self._send_json(200, session)

        if pathname == "/api/chat/sessions/update" and method == "POST":
            body = self._read_body()
            sid = body.get("id")
            if not sid:
                return self._send_json(400, {"error": "id required"})
            project_id = body["project_id"] if "project_id" in body else chat._UNSET
            model_id = body["model_id"] if "model_id" in body else chat._UNSET
            session = chat.update_session(
                sid, body.get("name"), body.get("system_role"), body.get("temperature"), project_id, model_id,
                files_position=body.get("files_position"), cross_session_position=body.get("cross_session_position"),
            )
            if session is None:
                return self._send_json(404, {"error": "Session not found"})
            return self._send_json(200, session)

        if pathname == "/api/chat/sessions/delete" and method == "POST":
            body = self._read_body()
            sid = body.get("id")
            if not sid:
                return self._send_json(400, {"error": "id required"})
            chat.delete_session(sid)
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/messages" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            sid = (query.get("session_id") or [None])[0]
            if not sid:
                return self._send_json(400, {"error": "session_id required"})
            return self._send_json(200, {"messages": chat.list_messages(sid)})

        if pathname == "/api/chat/messages" and method == "POST":
            body = self._read_body()
            sid = body.get("session_id")
            if not sid or "role" not in body or "content" not in body:
                return self._send_json(400, {"error": "session_id, role, content required"})
            message = chat.add_message(
                sid, body["role"], body["content"], body.get("is_context", 1), body.get("tokens_used", 0)
            )
            return self._send_json(200, message)

        if pathname == "/api/chat/messages/update" and method == "POST":
            body = self._read_body()
            mid = body.get("id")
            if not mid:
                return self._send_json(400, {"error": "id required"})
            message = chat.update_message(
                mid,
                body["content"] if "content" in body else None,
                body["is_context"] if "is_context" in body else None,
            )
            if message is None:
                return self._send_json(404, {"error": "Message not found"})
            return self._send_json(200, message)

        if pathname == "/api/chat/messages/delete" and method == "POST":
            body = self._read_body()
            mid = body.get("id")
            if not mid:
                return self._send_json(400, {"error": "id required"})
            chat.delete_message(mid)
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/messages/bulk" and method == "POST":
            body = self._read_body()
            sid = body.get("session_id")
            messages = body.get("messages") or []
            if not sid:
                return self._send_json(400, {"error": "session_id required"})
            count = chat.bulk_add_messages(sid, messages)
            return self._send_json(200, {"success": True, "count": count})

        if pathname == "/api/chat/messages/reorder" and method == "POST":
            body = self._read_body()
            sid = body.get("session_id")
            ordered_ids = body.get("ordered_ids") or []
            if not sid or not ordered_ids:
                return self._send_json(400, {"error": "session_id and ordered_ids required"})
            messages = chat.reorder_messages(sid, ordered_ids)
            if messages is None:
                return self._send_json(404, {"error": "One or more ids do not belong to this session"})
            return self._send_json(200, {"messages": messages})

        if pathname == "/api/chat/templates" and method == "GET":
            return self._send_json(200, {"templates": chat.list_templates()})

        if pathname == "/api/chat/templates" and method == "POST":
            body = self._read_body()
            try:
                template = chat.create_template(body.get("name"), body.get("content"))
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            return self._send_json(200, template)

        if pathname == "/api/chat/templates/update" and method == "POST":
            body = self._read_body()
            tid = body.get("id")
            if not tid:
                return self._send_json(400, {"error": "id required"})
            try:
                template = chat.update_template(tid, body.get("name"), body.get("content"))
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            if template is None:
                return self._send_json(404, {"error": "Template not found"})
            return self._send_json(200, template)

        if pathname == "/api/chat/templates/delete" and method == "POST":
            body = self._read_body()
            tid = body.get("id")
            if not tid:
                return self._send_json(400, {"error": "id required"})
            chat.delete_template(tid)
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/skills" and method == "GET":
            return self._send_json(200, {"skills": chat.list_skills()})

        if pathname == "/api/chat/skills" and method == "POST":
            body = self._read_body()
            try:
                skill = chat.create_skill(body.get("name"), body.get("description"), body.get("content"))
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            return self._send_json(200, skill)

        if pathname == "/api/chat/skills/update" and method == "POST":
            body = self._read_body()
            skill_id = body.get("id")
            if not skill_id:
                return self._send_json(400, {"error": "id required"})
            try:
                skill = chat.update_skill(
                    skill_id, body.get("name"), body.get("description"), body.get("content")
                )
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            if skill is None:
                return self._send_json(404, {"error": "Skill not found"})
            return self._send_json(200, skill)

        if pathname == "/api/chat/skills/delete" and method == "POST":
            body = self._read_body()
            skill_id = body.get("id")
            if not skill_id:
                return self._send_json(400, {"error": "id required"})
            chat.delete_skill(skill_id)
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/system-roles" and method == "GET":
            return self._send_json(200, {"system_roles": chat.list_system_roles()})

        if pathname == "/api/chat/system-roles" and method == "POST":
            body = self._read_body()
            try:
                role = chat.create_system_role(
                    body.get("name"), body.get("content"), body.get("is_default", 0)
                )
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            return self._send_json(200, role)

        if pathname == "/api/chat/system-roles/update" and method == "POST":
            body = self._read_body()
            rid = body.get("id")
            if not rid:
                return self._send_json(400, {"error": "id required"})
            try:
                role = chat.update_system_role(
                    rid, body.get("name"), body.get("content"),
                    body["is_default"] if "is_default" in body else None,
                )
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            if role is None:
                return self._send_json(404, {"error": "System role not found"})
            return self._send_json(200, role)

        if pathname == "/api/chat/system-roles/delete" and method == "POST":
            body = self._read_body()
            rid = body.get("id")
            if not rid:
                return self._send_json(400, {"error": "id required"})
            chat.delete_system_role(rid)
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/models" and method == "GET":
            return self._send_json(200, {"models": chat.list_models()})

        if pathname == "/api/chat/models" and method == "POST":
            body = self._read_body()
            try:
                model = chat.create_model(body.get("name"), body.get("api_key"), body.get("base_url"))
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            return self._send_json(200, model)

        if pathname == "/api/chat/models/update" and method == "POST":
            body = self._read_body()
            mid = body.get("id")
            if not mid:
                return self._send_json(400, {"error": "id required"})
            try:
                model = chat.update_model(mid, body.get("name"), body.get("api_key"), body.get("base_url"))
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            if model is None:
                return self._send_json(404, {"error": "Model not found"})
            return self._send_json(200, model)

        if pathname == "/api/chat/models/delete" and method == "POST":
            body = self._read_body()
            mid = body.get("id")
            if not mid:
                return self._send_json(400, {"error": "id required"})
            try:
                chat.delete_model(mid)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/settings" and method == "GET":
            return self._send_json(200, chat.get_settings())

        if pathname == "/api/chat/settings" and method == "POST":
            body = self._read_body()
            chat.update_settings(body)
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/tokens-estimate" and method == "POST":
            body = self._read_body()
            session_ids = body.get("session_ids") or []
            model = body.get("model")
            if not session_ids:
                return self._send_json(400, {"error": "session_ids required"})
            if not model:
                models = chat.list_models()
                model = models[0]["name"] if models else "gpt-4o"
            estimated = chat.estimate_tokens(session_ids, model)
            return self._send_json(
                200, {"estimated_tokens": estimated, "model": model, "session_count": len(session_ids)}
            )

        if pathname == "/api/chat/context-preview" and method == "POST":
            body = self._read_body()
            sid = body.get("session_id")
            context_session_ids = body.get("context_session_ids") or []
            if not sid:
                return self._send_json(400, {"error": "session_id required"})
            try:
                messages = chat.preview_context(sid, context_session_ids)
            except ValueError as e:
                return self._send_json(404, {"error": str(e)})
            return self._send_json(200, {"messages": messages})

        if pathname == "/api/chat/project-session" and method == "POST":
            body = self._read_body()
            project_path = body.get("project_path")
            if not project_path:
                return self._send_json(400, {"error": "project_path required"})
            try:
                session_id = chat.get_or_create_project_session(project_path, body.get("project_name"))
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            return self._send_json(200, {"session_id": session_id})

        if pathname == "/api/chat/project-files" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            project_path = (query.get("path") or [None])[0]
            if not project_path:
                return self._send_json(400, {"error": "path required"})
            try:
                files = chat.list_project_files(project_path)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            return self._send_json(200, {"files": files})

        if pathname == "/api/chat/project-files/read" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            project_path = (query.get("path") or [None])[0]
            file_path = (query.get("file") or [None])[0]
            if not project_path or not file_path:
                return self._send_json(400, {"error": "path and file required"})
            try:
                content, mtime = chat.read_project_file(project_path, file_path)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            except OSError as e:
                return self._send_json(404, {"error": str(e)})
            return self._send_json(200, {"content": content, "mtime": mtime})

        if pathname == "/api/chat/project-files/stat" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            project_path = (query.get("path") or [None])[0]
            file_path = (query.get("file") or [None])[0]
            if not project_path or not file_path:
                return self._send_json(400, {"error": "path and file required"})
            try:
                mtime = chat.stat_project_file(project_path, file_path)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            except OSError as e:
                return self._send_json(404, {"error": str(e)})
            return self._send_json(200, {"mtime": mtime})

        if pathname == "/api/chat/project-files/raw" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            project_path = (query.get("path") or [None])[0]
            file_path = (query.get("file") or [None])[0]
            if not project_path or not file_path:
                return self._send_json(400, {"error": "path and file required"})
            try:
                body, mime = chat.read_project_file_raw(project_path, file_path)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            except OSError as e:
                return self._send_json(404, {"error": str(e)})
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return None

        if pathname == "/api/chat/project-files/open" and method == "POST":
            body = self._read_body()
            project_path = body.get("path")
            file_path = body.get("file")
            if not project_path or not file_path:
                return self._send_json(400, {"error": "path and file required"})
            try:
                chat.open_project_file(project_path, file_path)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            except OSError as e:
                return self._send_json(404, {"error": str(e)})
            return self._send_json(200, {"ok": True})

        if pathname == "/api/chat/project-files/open-with" and method == "POST":
            body = self._read_body()
            project_path = body.get("path")
            file_path = body.get("file")
            if not project_path or not file_path:
                return self._send_json(400, {"error": "path and file required"})
            try:
                chat.open_project_file_with_dialog(project_path, file_path)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            except OSError as e:
                return self._send_json(404, {"error": str(e)})
            return self._send_json(200, {"ok": True})

        if pathname == "/api/chat/project-files/reveal" and method == "POST":
            body = self._read_body()
            project_path = body.get("path")
            file_path = body.get("file")
            if not project_path or not file_path:
                return self._send_json(400, {"error": "path and file required"})
            try:
                chat.reveal_project_file(project_path, file_path)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            except OSError as e:
                return self._send_json(404, {"error": str(e)})
            return self._send_json(200, {"ok": True})

        if pathname == "/api/chat/project-files/write" and method == "POST":
            body = self._read_body()
            project_path = body.get("path")
            file_path = body.get("file")
            content = body.get("content")
            if not project_path or not file_path or content is None:
                return self._send_json(400, {"error": "path, file, and content required"})
            try:
                mtime = chat.write_project_file(project_path, file_path, content)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            except OSError as e:
                return self._send_json(404, {"error": str(e)})
            return self._send_json(200, {"success": True, "mtime": mtime})

        if pathname == "/api/chat/project-files/create" and method == "POST":
            body = self._read_body()
            project_path = body.get("path")
            rel_path = body.get("file")
            content = body.get("content")
            encoding = body.get("encoding")
            if not project_path or not rel_path or content is None:
                return self._send_json(400, {"error": "path, file, and content required"})
            try:
                result = chat.create_project_file(project_path, rel_path, content, encoding=encoding)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            except OSError as e:
                return self._send_json(404, {"error": str(e)})
            return self._send_json(200, result)

        if pathname == "/api/chat/search" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            project_path = (query.get("path") or [None])[0]
            q = (query.get("q") or [""])[0]
            mode = (query.get("mode") or ["and"])[0]
            mode = mode if mode in ("and", "or") else "and"
            include_terms = chat._parse_search_terms((query.get("include") or [""])[0])
            exclude_terms = chat._parse_search_terms((query.get("exclude") or [""])[0])
            if not project_path:
                return self._send_json(400, {"error": "path required"})
            terms = chat._parse_search_terms(q)
            if not terms:
                return self._send_json(400, {"error": "q required"})
            try:
                result = chat.search_project_text(
                    project_path, terms, mode, include_terms=include_terms, exclude_terms=exclude_terms
                )
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            abstracts = chat.search_project_abstracts(
                project_path, terms, mode, include_terms=include_terms, exclude_terms=exclude_terms
            )
            result["abstracts_available"] = abstracts["available"]
            result["abstracts"] = abstracts["entries"]
            return self._send_json(200, result)

        if pathname == "/api/chat/search/all" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            q = (query.get("q") or [""])[0]
            mode = (query.get("mode") or ["and"])[0]
            mode = mode if mode in ("and", "or") else "and"
            include_terms = chat._parse_search_terms((query.get("include") or [""])[0])
            exclude_terms = chat._parse_search_terms((query.get("exclude") or [""])[0])
            terms = chat._parse_search_terms(q)
            if not terms:
                return self._send_json(400, {"error": "q required"})
            result = chat.search_all_projects_text(
                terms, mode, include_terms=include_terms, exclude_terms=exclude_terms
            )
            return self._send_json(200, result)

        if pathname == "/api/chat/attach-file" and method == "POST":
            body = self._read_body()
            sid = body.get("session_id")
            project_path = body.get("project_path")
            file_path = body.get("abs_path")
            if not sid or not project_path or not file_path:
                return self._send_json(400, {"error": "session_id, project_path, abs_path required"})
            try:
                message = chat.attach_file_as_context(sid, project_path, file_path)
            except ValueError as e:
                return self._send_json(400, {"error": str(e)})
            except OSError as e:
                return self._send_json(404, {"error": str(e)})
            return self._send_json(200, message)

        if pathname == "/api/chat/session-skills" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            sid = (query.get("session_id") or [None])[0]
            if not sid:
                return self._send_json(400, {"error": "session_id required"})
            return self._send_json(200, {"skills": chat.list_session_skills(sid)})

        if pathname == "/api/chat/session-skills/attach" and method == "POST":
            body = self._read_body()
            sid = body.get("session_id")
            skill_id = body.get("skill_id")
            if not sid or not skill_id:
                return self._send_json(400, {"error": "session_id and skill_id required"})
            chat.attach_skill_to_session(sid, skill_id)
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/session-skills/detach" and method == "POST":
            body = self._read_body()
            sid = body.get("session_id")
            skill_id = body.get("skill_id")
            if not sid or not skill_id:
                return self._send_json(400, {"error": "session_id and skill_id required"})
            chat.detach_skill_from_session(sid, skill_id)
            return self._send_json(200, {"success": True})

        if pathname == "/api/chat/save-message" and method == "POST":
            body = self._read_body()
            content = body.get("content", "")
            default_name = body.get("default_name") or "message.md"
            initial_dir = body.get("initial_dir")
            try:
                path = platform_ops.save_file(initial_dir, default_name)
            except platform_ops.NoPickerAvailable as e:
                return self._send_json(400, {"error": str(e)})
            except Exception as e:
                return self._send_json(500, {"error": str(e)})
            if not path:
                return self._send_json(200, {"cancelled": True})
            try:
                Path(path).write_text(content, encoding="utf-8")
            except Exception as e:
                return self._send_json(500, {"error": str(e)})
            return self._send_json(200, {"path": path})

        if pathname == "/api/chat/send" and method == "POST":
            body = self._read_body()
            sid = body.get("session_id")
            content = body.get("message", "")
            context_sessions = body.get("context_sessions") or []
            if not sid:
                return self._send_json(400, {"error": "session_id required"})
            self._send_sse_headers()
            try:
                for event_type, payload in chat.stream_chat(sid, content, context_sessions):
                    if event_type == "content":
                        self._send_sse_chunk({"content": payload})
                    elif event_type == "tokens_used":
                        self._send_sse_chunk({"tokens_used": payload})
                    elif event_type == "error":
                        self._send_sse_chunk({"error": payload})
                    elif event_type == "done":
                        pass
                self._send_sse_chunk({"done": True})
            except Exception as e:
                self._send_sse_chunk({"error": str(e)})
            self._end_sse()
            return

        if pathname == "/api/chat/bulk-summarize" and method == "POST":
            body = self._read_body()
            project_path = body.get("project_path")
            rel_paths = body.get("rel_paths") or []
            self._send_sse_headers()
            try:
                for event in chat.bulk_summarize_files(project_path, rel_paths):
                    self._send_sse_chunk(event)
            except Exception as e:
                self._send_sse_chunk({"type": "error", "message": str(e)})
            self._end_sse()
            return

        if pathname == "/api/chat/bulk-extract-pdf" and method == "POST":
            body = self._read_body()
            project_path = body.get("project_path")
            rel_paths = body.get("rel_paths") or []
            self._send_sse_headers()
            try:
                for event in chat.bulk_extract_pdfs(project_path, rel_paths):
                    self._send_sse_chunk(event)
            except Exception as e:
                self._send_sse_chunk({"type": "error", "message": str(e)})
            self._end_sse()
            return

        if pathname == "/api/pdf-summarize" and method == "POST":
            body = self._read_body()
            text = body.get("text")
            filename = body.get("filename")
            if not text:
                return self._send_json(400, {"error": "text required"})
            try:
                summary, tokens_used, model_name = chat.summarize_pdf_text(text, filename)
            except Exception as e:
                return self._send_json(500, {"error": str(e)})
            return self._send_json(200, {"summary": summary, "tokens_used": tokens_used, "model": model_name})

        if pathname == "/api/focus" and method == "POST":
            if _window is not None:
                try:
                    _window.restore()
                    _window.show()
                except Exception:
                    pass
            return self._send_json(200, {"ok": True})

        if pathname == "/api/shutdown" and method == "POST":
            self._send_json(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return

        return self._send_json(404, {"error": "not found"})

    def _route(self):
        parts = urlsplit(self.path)
        pathname = parts.path

        if pathname.startswith("/api/"):
            try:
                self._handle_api(pathname)
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        if self.command == "GET" and pathname.startswith("/lib/"):
            lib_path = (DASHBOARD_DIR / pathname.lstrip("/")).resolve()
            if DASHBOARD_DIR / "lib" not in lib_path.parents or not lib_path.is_file():
                return self._send_json(404, {"error": "not found"})
            content_type = {
                ".css": "text/css",
                ".js": "application/javascript",
                ".mjs": "application/javascript",
                ".woff2": "font/woff2",
                ".woff": "font/woff",
                ".ttf": "font/ttf",
            }.get(lib_path.suffix, "application/octet-stream")
            body = lib_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if self.command == "GET" and pathname in ("/", "/arti-dashboard.html"):
            html = HTML_PATH.read_text(encoding="utf-8")
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        body = b"not found"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = _route
    do_POST = _route


def create_server():
    # ThreadingHTTPServer, not HTTPServer: a plain HTTPServer handles one
    # connection at a time, and a browser tab left open holds its HTTP/1.1
    # keep-alive connection idle indefinitely -- that alone blocks every other
    # request (including /api/ping and /api/shutdown) until the tab closes.
    # Raises OSError if PORT is already bound -- callers (app.py) use that to
    # detect an already-running instance.
    db.init_db()
    return ThreadingHTTPServer((HOST, PORT), Handler)


def main():
    server = create_server()
    print(f"ARTi Framework dashboard running at http://{HOST}:{PORT}")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
