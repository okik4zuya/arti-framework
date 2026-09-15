"""Dashboard-facing adapter over `arti-jfinder` (tools/arti-jfinder/db.py), the
cross-project Scimago journal-metrics singleton. Loaded in-process via
importlib, same pattern as lit.py's `_load_arti_lit()` -- pure-stdlib module,
no reason to spawn a subprocess per dashboard row.
"""
import importlib.util
from pathlib import Path

ARTI_HOME = Path(__file__).resolve().parent.parent.parent


def _load_arti_jfinder():
    path = ARTI_HOME / "tools" / "arti-jfinder" / "db.py"
    spec = importlib.util.spec_from_file_location("arti_jfinder_db", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arti_jfinder = _load_arti_jfinder()


def lookup(issn=None, title=None):
    return arti_jfinder.journal_lookup(issn=issn, title=title)
