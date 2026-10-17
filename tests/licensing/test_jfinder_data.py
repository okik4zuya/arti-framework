"""arti-jfinder keeps the Scimago snapshot (shipped, replaced by every update) apart from the scope cache
(written by the researcher's Claude, must survive updates).

Runs the real CLI in a throw-away ~/.arti (ARTI_HOME follows the file location), never the real memory folder.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import CODE  # noqa: E402

results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


SHIPPED = CODE / "tools" / "arti-jfinder" / "arti-jfinder.db"
con = sqlite3.connect(f"{SHIPPED.as_uri()}?mode=ro", uri=True)
tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
counts = [con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("journals", "journal_metrics", "journal_categories")]
years = con.execute("SELECT DISTINCT year FROM journal_metrics").fetchall()
ver = con.execute("PRAGMA user_version").fetchone()[0]
con.close()
check("shipped snapshot has no journal_scope table (no user data in a shipped file)", "journal_scope" not in tables, tables)
check("shipped snapshot: 32,193 journals, 2025 only", counts[:2] == [32193, 32193] and years == [(2025,)], (counts, years))
check("shipped snapshot is stamped with user_version 1", ver == 1, ver)

sys.path.insert(0, str(CODE / "tools" / "arti-update"))
import bundle  # noqa: E402
check("memory/ is not an update item (updates cannot reach the scope store)", "memory" not in bundle.UPDATE_ITEMS)

with tempfile.TemporaryDirectory(prefix="arti-jf-") as tmp:
    home = Path(tmp)
    (home / "tools").mkdir()
    shutil.copytree(CODE / "tools" / "_shared", home / "tools" / "_shared", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(CODE / "tools" / "arti-jfinder", home / "tools" / "arti-jfinder", ignore=shutil.ignore_patterns("__pycache__"))
    snap = home / "tools" / "arti-jfinder" / "arti-jfinder.db"
    store = home / "memory" / "jfinder-scope.db"

    def cli(*args):
        r = subprocess.run([sys.executable, str(home / "tools" / "arti-jfinder" / "cli.py"), *args],
                           cwd=tmp, capture_output=True, text=True, encoding="utf-8",
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        return json.loads(r.stdout)

    # An older install: the snapshot still carries a journal_scope table with one row.
    c = sqlite3.connect(snap)
    c.execute("PRAGMA journal_mode=DELETE")
    c.execute("CREATE TABLE journal_scope (journal_id INTEGER PRIMARY KEY, aims_scope_text TEXT NOT NULL, "
              "source_url TEXT, fetched_at TEXT NOT NULL)")
    c.execute("INSERT INTO journal_scope VALUES (17854, 'legacy text', 'https://x', '2026-01-01T00:00:00')")
    c.commit()
    c.close()
    before = sha(snap)

    r = cli("scope", "get", "--id", "17854")
    check("legacy row is imported on first use", r["ok"] and r["row"] and r["row"]["aims_scope_text"] == "legacy text", r)
    check("scope store lives under memory/", store.exists())
    check("importing did not modify the snapshot", sha(snap) == before)

    r = cli("scope", "set", "--id", "17854", "--text", "new text", "--source-url", "https://y")
    check("scope set returns the new row", r["ok"] and r["row"]["aims_scope_text"] == "new text", r)
    check("scope set did not modify the snapshot", sha(snap) == before)
    r = cli("scope", "get", "--id", "17854")
    check("a later run does not let the legacy row overwrite the newer one", r["row"]["aims_scope_text"] == "new text", r)
    r = cli("scope", "set", "--id", "999999999", "--text", "x")
    check("unknown sourceid is refused", not r["ok"] and "no journal with sourceid" in r["error"], r)
    r = cli("scope", "get", "--id", "21100810714")
    check("missing scope row reads as null", r["ok"] and r["row"] is None, r)

    # Simulated update: the snapshot file is replaced by the shipped one (no journal_scope table).
    shutil.copyfile(SHIPPED, snap)
    r = cli("scope", "get", "--id", "17854")
    check("scope row survives replacing the snapshot", r["ok"] and r["row"]["aims_scope_text"] == "new text", r)
    r = cli("journal", "search", "--keyword", "nature", "--limit", "2")
    check("journal search works after the replacement", r["ok"] and len(r["rows"]) == 2, r)
    c = sqlite3.connect(store)
    check("scope store is stamped with user_version 1", c.execute("PRAGMA user_version").fetchone()[0] == 1)
    c.close()

print("\n%d checks, %d failed" % (len(results), results.count(False)))
sys.exit(0 if all(results) else 1)
