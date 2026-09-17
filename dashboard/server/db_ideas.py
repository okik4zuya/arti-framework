"""Dashboard-facing read-only view over `idea_bank` -- the same SQLite table
tools/arti-db/db.py owns for the ARTi-idea skill's cross-project idea parking.
Mirrors db.py's `_load_arti_db()` pattern; no write path is exposed here since
the dashboard's Ideas panel is view-only for this pass.
"""
import importlib.util
from pathlib import Path

ARTI_HOME = Path(__file__).resolve().parent.parent.parent


def _load_arti_db():
    path = ARTI_HOME / "tools" / "arti-db" / "db.py"
    spec = importlib.util.spec_from_file_location("arti_db", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arti_db = _load_arti_db()


def list_ideas():
    return arti_db.idea_bank_list()
