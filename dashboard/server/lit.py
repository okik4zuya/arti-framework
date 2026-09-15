"""Dashboard-facing adapter over `arti-lit` (tools/arti-lit/db.py), the
per-project SQLite bibliography store. Loaded in-process via importlib, same
pattern as db.py's `_load_arti_db()` -- this is the same vendored interpreter
and a pure-stdlib module, so there is no reason to spawn a subprocess per
dashboard click or re-parse cli.py's JSON output (that CLI exists for
Claude/Bash-driven use, not this in-process path).
"""
import importlib.util
from pathlib import Path

ARTI_HOME = Path(__file__).resolve().parent.parent.parent


def _load_arti_lit():
    path = ARTI_HOME / "tools" / "arti-lit" / "db.py"
    spec = importlib.util.spec_from_file_location("arti_lit_db", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arti_lit = _load_arti_lit()


def list_references(project_path):
    arti_lit.init_db(project_path)
    return arti_lit.library_list(project_path)


def import_ris(project_path, file_paths):
    arti_lit.init_db(project_path)
    return arti_lit.library_import_ris(project_path, file_paths)
