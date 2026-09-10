"""Dashboard-facing view over `project_index` -- the same SQLite table
tools/arti-db/db.py owns for the ARTi skills' cross-project tracking. The
dashboard used to keep a separate `launcher.db` file with its own `projects`
table; that has been retired (see the one-time migration in
tools/arti-db/db.py's init_db()) so there is exactly one project registry.
This module is a thin adapter: it aliases `project_index`'s `topic`/
`project_path` columns to the `name`/`path` keys the dashboard HTML/JS already
expects, and otherwise reads/writes the launcher-only columns
(category/tags/lifecycle/added_at/last_opened_at) that init_db() added to that
table.
"""
import importlib.util
import json
from pathlib import Path

ARTI_HOME = Path(__file__).resolve().parent.parent.parent

PROJECT_LIFECYCLES = ("active", "complete", "archived")


def _load_arti_db():
    """Loads tools/arti-db/db.py under its own module name -- a plain `import
    db` here would collide with this file's own module name if some other
    module imported both under the same name."""
    path = ARTI_HOME / "tools" / "arti-db" / "db.py"
    spec = importlib.util.spec_from_file_location("arti_db", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arti_db = _load_arti_db()


def init_db():
    arti_db.init_db()


def _to_dashboard_row(row):
    return {
        "id": row["id"],
        "name": row["topic"],
        "path": row["project_path"],
        "category": row["category"],
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "lifecycle": row["lifecycle"],
        "added_at": row["added_at"],
        "last_opened_at": row["last_opened_at"],
    }


def list_projects():
    rows = arti_db.project_list()
    rows.sort(key=lambda r: (r["topic"] or "").lower())
    return [_to_dashboard_row(r) for r in rows]


def find_project(path_str):
    row = arti_db.project_get(str(Path(path_str)))
    return _to_dashboard_row(row) if row else None


def upsert_project(path, name=None, category=None, tags=None, touch_opened=False):
    """Creates a project_index row for path if absent, otherwise updates only
    the launcher-owned fields passed. touch_opened bumps last_opened_at to
    now. Mirrors the old launcher.db upsert_project's create-or-update-by-path
    semantics, now against the shared table."""
    path_str = str(Path(path))
    now = arti_db._now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            row = conn.execute(
                "SELECT * FROM project_index WHERE project_path = ?", (path_str,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO project_index "
                    "(topic, project_path, stage, target_journal, status, summary, updated_at, created_at, "
                    "category, tags, lifecycle, added_at, last_opened_at) "
                    "VALUES (?, ?, 'N/A', NULL, NULL, NULL, ?, ?, ?, ?, 'active', ?, ?)",
                    (
                        name or Path(path_str).name, path_str, now, now,
                        category or "Other", json.dumps(tags or []),
                        now, now if touch_opened else None,
                    ),
                )
            else:
                entry = arti_db._row_to_dict(row)
                new_name = name if name is not None else entry["topic"]
                new_category = category if category is not None else entry["category"]
                new_tags = json.dumps(tags) if tags is not None else entry["tags"]
                new_last_opened = now if touch_opened else entry["last_opened_at"]
                conn.execute(
                    "UPDATE project_index SET topic=?, category=?, tags=?, last_opened_at=? "
                    "WHERE project_path=?",
                    (new_name, new_category, new_tags, new_last_opened, path_str),
                )
            conn.commit()
            result = arti_db._row_to_dict(
                conn.execute("SELECT * FROM project_index WHERE project_path = ?", (path_str,)).fetchone()
            )
        finally:
            conn.close()
    arti_db.project_export()
    return _to_dashboard_row(result)


def set_project_lifecycle(path, lifecycle):
    """Sets the active/complete/archived lifecycle on the project_index row
    for path, creating a bare entry (as upsert_project would) if none exists
    yet."""
    path_str = str(Path(path))
    now = arti_db._now()
    with arti_db._lock:
        conn = arti_db._connect()
        try:
            row = conn.execute(
                "SELECT * FROM project_index WHERE project_path = ?", (path_str,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO project_index "
                    "(topic, project_path, stage, target_journal, status, summary, updated_at, created_at, "
                    "category, tags, lifecycle, added_at, last_opened_at) "
                    "VALUES (?, ?, 'N/A', NULL, NULL, NULL, ?, ?, 'Other', '[]', ?, ?, NULL)",
                    (Path(path_str).name, path_str, now, now, lifecycle, now),
                )
            else:
                conn.execute(
                    "UPDATE project_index SET lifecycle=? WHERE project_path=?", (lifecycle, path_str)
                )
            conn.commit()
            result = arti_db._row_to_dict(
                conn.execute("SELECT * FROM project_index WHERE project_path = ?", (path_str,)).fetchone()
            )
        finally:
            conn.close()
    arti_db.project_export()
    return _to_dashboard_row(result)
