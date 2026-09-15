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
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import db
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
                   "data", "figures", "submission", "inbox/archive", "memory"):
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
    _write_if_missing(
        project_path / "inbox" / "index.md",
        "# inbox index\n\n| File | Tipe | Status | One-line hook | Dipakai di | Date added |\n"
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
        + "- [ ] Run ARTi-idea to develop the research idea\n\n"
        "## Change log\n"
        f"- {today}: project scaffolded\n",
    )
    _write_if_missing(
        project_path / "memory" / "status.md",
        frontmatter("status", f"Living current-state narrative for {name}", "T0")
        + "## Current state\n"
        f"Project scaffolded {today}. No idea work started yet.\n\n"
        "## Archive\n\n"
        "## Change log\n"
        f"- {today}: project scaffolded\n",
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
            "`memory/status.md`, `~/.arti/memory/working-preferences.md`, `inbox/index.md`.\n\n"
            "> Canonical template missing at "
            f"`{CLAUDE_TEMPLATE_PATH}` -- regenerate this file once it is restored.\n\n"
            "<!-- arti: local additions below -- preserved on regeneration -->\n"
        )
    return tmpl.replace("{{PROJECT_NAME}}", name)


def build_data():
    return {"projects": db.list_projects()}


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

    def _handle_api(self, pathname):
        method = self.command

        if pathname == "/api/ping" and method == "GET":
            return self._send_json(200, {"ok": True})

        if pathname == "/api/data" and method == "GET":
            return self._send_json(200, build_data())

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
