"""ARTi Framework dashboard server -- plain stdlib http.server, no third-party
deps. Run via the vendored ~/.arti/python interpreter; see
../start-arti-dashboard.bat / ../start-arti-dashboard.sh.

progress-index.md and research-idea-bank.md are parsed fresh from disk on
every /api/data request, never cached. Both are read-only from here except
for the one dashboard-initiated write path, /api/idea-to-project, which
appends a pipeline row and removes the converted idea-bank entry -- everything
else about those files' upsert/change-log conventions still belongs to the
ARTi skills, not this dashboard.

launcher-projects.json (see load_registry/save_registry/upsert_registry_entry)
is the canonical index of every project's identity -- paper and general alike
-- keyed by path. progress-index.md stays a satellite "paper detail" table
joined by path at build_data() time; it is never written by anything in this
file except scaffold_project()/idea-to-project's _append_progress_row calls.
build_data() itself stays pure-read -- registry entries are only created or
touched by explicit write endpoints (register, new-project, open-folder,
open-vscode, projects/lifecycle), never as a side effect of GET /api/data.
"""
import json
import os
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import platform_ops

HOST = "127.0.0.1"
PORT = 4174

DASHBOARD_DIR = Path(__file__).resolve().parent.parent
ARTI_HOME = DASHBOARD_DIR.parent

PROGRESS_PATH = ARTI_HOME / "memory" / "progress-index.md"
IDEA_BANK_PATH = ARTI_HOME / "memory" / "research-idea-bank.md"
REGISTRY_PATH = ARTI_HOME / "memory" / "launcher-projects.json"
SESSIONS_DIR = ARTI_HOME / "workflow-sessions"
HTML_PATH = DASHBOARD_DIR / "arti-dashboard.html"
CLAUDE_TEMPLATE_PATH = (
    ARTI_HOME / "skills" / "ARTi-setup" / "references" / "project-claude-template.md"
)

_registry_lock = threading.Lock()

SESSIONS_LIMIT = 20

# Milestone order used by derive_substage(), from
# skills/ARTi-setup/references/project-scaffold-template.md. Each entry is a
# (label, glob-pattern relative to the project root) pair; the substage shown
# is the label of the *last* one in this list whose file exists on disk.
SUBSTAGE_MILESTONES = [
    ("Gap map", "idea/gap-map.md"),
    ("Idea canvas", "idea/idea-canvas.md"),
    ("Research design", "idea/research-design.*"),
    ("Journal target sheet", "idea/journal-target-sheet.md"),
    ("Idea handoff", "idea/handoff.md"),
    ("Journal profile", "writing/journal-profile_*.md"),
    ("Manuscript blueprint", "writing/manuscript-blueprint.md"),
    ("Scratchbook", "writing/scratchbook.md"),
    ("Manuscript draft", "writing/manuscript_draft*.md"),
    ("Completion plan", "writing/completion-plan.*"),
    ("Cover letter", "submission/cover-letter_*.md"),
]

TODO_MARKER_RE = re.compile(r"^- \[([ xX~])\]")


def progress_count(project_path):
    """Counts done vs. total checklist items in a project's
    memory/todo-list.md ('- [x]' vs. all of '- [ ]' / '- [x]' / '- [~]').
    Missing file or no matching lines -> (0, 0)."""
    todo_path = project_path / "memory" / "todo-list.md"
    if not todo_path.exists():
        return (0, 0)
    done = total = 0
    for line in todo_path.read_text(encoding="utf-8").splitlines():
        m = TODO_MARKER_RE.match(line.strip())
        if not m:
            continue
        total += 1
        if m.group(1) in ("x", "X"):
            done += 1
    return (done, total)


def is_stale(project_path, updated_str):
    """True when the child project's memory/todo-list.md has been modified
    more recently than progress-index.md's recorded 'Last updated' date for
    that row -- catches the case where a session changed project state but
    never upserted the pipeline row (see project-scaffold-template.md's
    session-end wrap-up ritual)."""
    todo_path = project_path / "memory" / "todo-list.md"
    if not todo_path.exists() or not updated_str:
        return False
    try:
        updated_date = datetime.strptime(updated_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return False
    mtime_date = datetime.fromtimestamp(todo_path.stat().st_mtime).date()
    return mtime_date > updated_date


def derive_substage(project_path):
    """Returns the label of the last milestone file (in SUBSTAGE_MILESTONES
    order) that exists on disk under project_path, or None if none do."""
    label = None
    for name, pattern in SUBSTAGE_MILESTONES:
        if list(project_path.glob(pattern)):
            label = name
    return label


def parse_pipeline():
    """Parses the pipeline table out of progress-index.md. Skips the header
    row, the '---' separator row, and any malformed row (fewer than 6 cells)
    rather than erroring the whole endpoint."""
    if not PROGRESS_PATH.exists():
        return []
    rows = []
    for line in PROGRESS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 6:
            continue
        if cells[0].lower().startswith("topic"):
            continue
        if all(re.fullmatch(r":?-+:?", c) for c in cells):
            continue
        project_path = Path(cells[1])
        done, total = progress_count(project_path)
        rows.append({
            "topic": cells[0],
            "path": cells[1],
            "stage": cells[2],
            "journal": cells[3],
            "status": cells[4],
            "updated": cells[5],
            "progress": {"done": done, "total": total},
            "substage": derive_substage(project_path) or "",
            "stale": is_stale(project_path, cells[5]),
        })
    return rows


def parse_idea_bank():
    """Parses '## Entry N: Title' blocks out of research-idea-bank.md. Any
    entry missing a field just gets an empty string for it, never an error."""
    if not IDEA_BANK_PATH.exists():
        return []
    text = IDEA_BANK_PATH.read_text(encoding="utf-8")
    blocks = re.split(r"\n(?=## Entry\s+\d+)", text)

    def field(block, name):
        m = re.search(r"\*\*" + re.escape(name) + r":\*\*\s*(.+?)(?=\n\*\*|\Z)", block, re.S)
        return m.group(1).strip() if m else ""

    entries = []
    for block in blocks:
        block = block.strip()
        if not block.startswith("## Entry"):
            continue
        title_m = re.match(r"## Entry\s+\d+:\s*(.+)", block)
        entries.append({
            "title": title_m.group(1).strip() if title_m else "",
            "ideaText": field(block, "Idea text"),
            "noveltyScore": field(block, "Novelty score"),
            "dateParked": field(block, "Date parked"),
            "source": field(block, "Source project/topic"),
            "reason": field(block, "Reason parked"),
            "notes": field(block, "Notes"),
        })
    return entries


def remove_idea_bank_entry(title):
    """Drops the first '## Entry N: <title>' block matching title from
    research-idea-bank.md and rewrites the file. Remaining '## Entry N'
    headers are display labels, not IDs referenced elsewhere, so they are
    not renumbered."""
    if not IDEA_BANK_PATH.exists():
        return False
    text = IDEA_BANK_PATH.read_text(encoding="utf-8")
    blocks = re.split(r"\n(?=## Entry\s+\d+)", text)
    for i, block in enumerate(blocks):
        stripped = block.strip()
        if not stripped.startswith("## Entry"):
            continue
        title_m = re.match(r"## Entry\s+\d+:\s*(.+)", stripped)
        if title_m and title_m.group(1).strip() == title:
            del blocks[i]
            IDEA_BANK_PATH.write_text("\n".join(blocks), encoding="utf-8")
            return True
    return False


def parse_sessions():
    if not SESSIONS_DIR.exists():
        return []
    try:
        files = sorted(SESSIONS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return []
    return [{"name": f.name, "mtime": f.stat().st_mtime} for f in files[:SESSIONS_LIMIT]]


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
                   "data", "figures", "submission", "wdyt/archive", "memory"):
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
        project_path / "wdyt" / "index.md",
        "# wdyt index\n\n| File | Tipe | Status | One-line hook | Dipakai di | Date added |\n"
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

    _append_progress_row(project_path, name, "Not started", "Scaffolded")


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
            "`memory/status.md`, `~/.arti/memory/working-preferences.md`, `wdyt/index.md`.\n\n"
            "> Canonical template missing at "
            f"`{CLAUDE_TEMPLATE_PATH}` -- regenerate this file once it is restored.\n\n"
            "<!-- arti: local additions below -- preserved on regeneration -->\n"
        )
    return tmpl.replace("{{PROJECT_NAME}}", name)


def _append_progress_row(project_path, name, stage, status):
    """Appends one row to progress-index.md, creating the file with its
    header if missing. Does not check for an existing row -- callers that
    care about duplicates should check _progress_row_exists first."""
    today = datetime.now().strftime("%Y-%m-%d")
    progress_line = f"| {name} | {project_path} | {stage} | — | {status} | {today} |\n"
    if PROGRESS_PATH.exists():
        text = PROGRESS_PATH.read_text(encoding="utf-8")
        if not text.endswith("\n"):
            text += "\n"
        text += progress_line
        PROGRESS_PATH.write_text(text, encoding="utf-8")
    else:
        PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "# Idea/Paper Progress Index\n\n"
            "| Topic / idea label | Project folder path | Current stage | Target journal | Status | Last updated |\n"
            "|---|---|---|---|---|---|\n"
        )
        PROGRESS_PATH.write_text(header + progress_line, encoding="utf-8")


def load_registry():
    """Loads launcher-projects.json, tolerating a missing or corrupt file by
    returning an empty registry rather than erroring."""
    if not REGISTRY_PATH.exists():
        return {"projects": []}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"projects": []}


def save_registry(registry):
    """Atomic write (temp file + os.replace) so a crash mid-write can't leave
    launcher-projects.json truncated/corrupt."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = REGISTRY_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    os.replace(tmp_path, REGISTRY_PATH)


def find_registry_entry(registry, path_str):
    for p in registry["projects"]:
        if p["path"] == path_str:
            return p
    return None


def upsert_registry_entry(path, name=None, category=None, tags=None, touch_opened=False):
    """Creates a registry entry for path if absent, otherwise updates only
    the fields passed. touch_opened bumps last_opened_at to now. Lock-protected
    read-modify-write since ThreadingHTTPServer serves requests concurrently."""
    path_str = str(Path(path))
    now = datetime.now().isoformat(timespec="seconds")
    with _registry_lock:
        registry = load_registry()
        entry = find_registry_entry(registry, path_str)
        if entry is None:
            entry = {
                "id": uuid.uuid4().hex,
                "name": name or Path(path_str).name,
                "path": path_str,
                "category": category or "Other",
                "tags": tags or [],
                "added_at": now,
                "last_opened_at": now if touch_opened else None,
                "lifecycle": "active",
            }
            registry["projects"].append(entry)
        else:
            if name is not None:
                entry["name"] = name
            if category is not None:
                entry["category"] = category
            if tags is not None:
                entry["tags"] = tags
            if touch_opened:
                entry["last_opened_at"] = now
            entry.setdefault("lifecycle", "active")
        save_registry(registry)
        return entry


PROJECT_LIFECYCLES = ("active", "complete", "archived")


def set_project_lifecycle(path, lifecycle):
    """Sets the active/complete/archived lifecycle on the registry entry for
    path, creating a bare entry (as upsert_registry_entry would) if none
    exists yet -- e.g. a Paper project that's never been opened via the
    dashboard and so has no registry row. Lock-protected like
    upsert_registry_entry."""
    path_str = str(Path(path))
    now = datetime.now().isoformat(timespec="seconds")
    with _registry_lock:
        registry = load_registry()
        entry = find_registry_entry(registry, path_str)
        if entry is None:
            entry = {
                "id": uuid.uuid4().hex,
                "name": Path(path_str).name,
                "path": path_str,
                "category": "Other",
                "tags": [],
                "added_at": now,
                "last_opened_at": None,
                "lifecycle": lifecycle,
            }
            registry["projects"].append(entry)
        else:
            entry["lifecycle"] = lifecycle
        save_registry(registry)
        return entry


def build_data():
    pipeline = parse_pipeline()
    idea_bank = parse_idea_bank()
    sessions = parse_sessions()
    registry = load_registry()
    reg_by_path = {p["path"]: p for p in registry["projects"]}

    projects = []
    paper_paths = set()
    for row in pipeline:
        path_str = str(Path(row["path"]))
        paper_paths.add(path_str)
        reg = reg_by_path.get(path_str)
        projects.append({
            "id": reg["id"] if reg else None,
            "name": row["topic"],
            "path": row["path"],
            "category": "Paper",
            "tags": reg["tags"] if reg else [],
            "stage": row["stage"],
            "journal": row["journal"],
            "status": row["status"],
            "updated": row["updated"],
            "progress": row["progress"],
            "substage": row["substage"],
            "stale": row["stale"],
            "addedAt": reg["added_at"] if reg else None,
            "lastOpenedAt": reg["last_opened_at"] if reg else None,
            "lifecycle": reg.get("lifecycle", "active") if reg else "active",
        })
    for path_str, reg in reg_by_path.items():
        if path_str in paper_paths:
            continue
        projects.append({
            "id": reg["id"],
            "name": reg["name"],
            "path": reg["path"],
            "category": reg["category"],
            "tags": reg.get("tags", []),
            "stage": None,
            "journal": None,
            "status": None,
            "updated": None,
            "progress": None,
            "substage": None,
            "stale": False,
            "addedAt": reg.get("added_at"),
            "lastOpenedAt": reg.get("last_opened_at"),
            "lifecycle": reg.get("lifecycle", "active"),
        })

    return {
        "stats": {
            "pipelineCount": len(pipeline),
            "ideaBankCount": len(idea_bank),
            "sessionsCount": len(sessions),
            "projectsCount": len(projects),
        },
        "projects": projects,
        "ideaBank": idea_bank,
        "sessions": sessions,
    }


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
                upsert_registry_entry(project_path, name=name, category=category, tags=tags, touch_opened=True)
            platform_ops.open_in_vscode(project_path)
            return self._send_json(200, {"path": str(project_path)})

        if pathname == "/api/idea-to-project" and method == "POST":
            body = self._read_body()
            parent_path, name, title = body.get("parentPath"), body.get("name"), body.get("title")
            if not parent_path or not name or not title:
                return self._send_json(400, {"error": "parentPath, name, and title required"})
            entry = next((e for e in parse_idea_bank() if e["title"] == title), None)
            if entry is None:
                return self._send_json(400, {"error": f"no idea-bank entry titled {title!r}"})
            try:
                project_path = Path(parent_path) / name
                project_path.mkdir(parents=True, exist_ok=False)
            except FileExistsError:
                return self._send_json(400, {"error": "a folder with that name already exists there"})
            except OSError as e:
                return self._send_json(500, {"error": str(e)})
            try:
                scaffold_project(project_path, name)
            except OSError as e:
                return self._send_json(500, {"error": f"created folder but scaffolding failed: {e}"})
            _write_if_missing(
                project_path / "idea" / "idea-bank-entry.md",
                f"# Idea bank entry: {entry['title']}\n\n"
                f"**Idea text:** {entry['ideaText']}\n"
                f"**Novelty score:** {entry['noveltyScore']}\n"
                f"**Date parked:** {entry['dateParked']}\n"
                f"**Source project/topic:** {entry['source']}\n"
                f"**Reason parked:** {entry['reason']}\n"
                f"**Notes:** {entry['notes']}\n",
            )
            remove_idea_bank_entry(title)
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
            upsert_registry_entry(project_path, name=name, category=category, tags=tags, touch_opened=True)
            platform_ops.open_in_vscode(project_path)
            return self._send_json(200, {"path": str(project_path)})

        if pathname == "/api/projects/lifecycle" and method == "POST":
            body = self._read_body()
            p = body.get("path")
            lifecycle = body.get("lifecycle")
            if not p or lifecycle not in PROJECT_LIFECYCLES:
                return self._send_json(400, {"error": "path and lifecycle (active|complete|archived) required"})
            entry = set_project_lifecycle(p, lifecycle)
            return self._send_json(200, {"ok": True, "lifecycle": entry["lifecycle"]})

        if pathname == "/api/open-folder" and method == "POST":
            body = self._read_body()
            p = body.get("path")
            if not p:
                return self._send_json(400, {"error": "path required"})
            platform_ops.open_in_file_manager(p)
            upsert_registry_entry(p, touch_opened=True)
            return self._send_json(200, {"ok": True})

        if pathname == "/api/open-vscode" and method == "POST":
            body = self._read_body()
            p = body.get("path")
            if not p:
                return self._send_json(400, {"error": "path required"})
            platform_ops.open_in_vscode(p)
            upsert_registry_entry(p, touch_opened=True)
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


def main():
    # ThreadingHTTPServer, not HTTPServer: a plain HTTPServer handles one
    # connection at a time, and a browser tab left open holds its HTTP/1.1
    # keep-alive connection idle indefinitely -- that alone blocks every other
    # request (including /api/ping and /api/shutdown) until the tab closes.
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"ARTi Framework dashboard running at http://{HOST}:{PORT}")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
