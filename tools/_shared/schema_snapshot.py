"""Schema fingerprints of ARTi's SQLite stores, and the additive-only comparison used before a release.

Why: manual rollback puts the previous code back on a database the newer code already migrated, and it never
restores the database (see memory release-checklist items 6 and 8). That only works if every schema change is
additive. `tests/licensing/test_schema_additive.py` compares the schema the working tree creates with
`tests/licensing/schema_baseline.json`, which is regenerated after each published release:

    "~/.arti/python/python.exe" tools/_shared/schema_snapshot.py --write

Each store is built fresh inside a throw-away copy of the tool (ARTI_HOME is derived from the file location, so
nothing under the real ~/.arti is touched). Stdlib only.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent.parent
BASELINE = CODE / "tests" / "licensing" / "schema_baseline.json"

# store name -> (tool folder, python snippet that creates the store inside the copy, db path inside the copy)
STORES = {
    "arti-db": ("arti-db", "import db; db.init_db()", "memory/arti.db"),
    "arti-lit": ("arti-lit", "import db, os; os.makedirs('proj', exist_ok=True); db.init_db('proj')",
                 "proj/literature/arti-lit.db"),
    "jfinder-snapshot": ("arti-jfinder", "import db; db.init_db()", "tools/arti-jfinder/arti-jfinder.db"),
    "jfinder-scope": ("arti-jfinder", "import db; db.init_db()", "memory/jfinder-scope.db"),
}


def fingerprint(conn):
    """tables -> columns (name, type, notnull, default, pk), indexes -> (unique, columns), plus user_version."""
    out = {"user_version": conn.execute("PRAGMA user_version").fetchone()[0], "tables": {}, "indexes": {}}
    names = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    for t in names:
        out["tables"][t] = {
            r[1]: {"type": (r[2] or "").upper(), "notnull": int(r[3]), "default": r[4], "pk": int(r[5])}
            for r in conn.execute(f'PRAGMA table_info("{t}")')}
        for idx in conn.execute(f'PRAGMA index_list("{t}")'):
            if idx[3] == "pk" or idx[1].startswith("sqlite_autoindex"):
                continue
            cols = [c[2] for c in conn.execute(f'PRAGMA index_info("{idx[1]}")')]
            out["indexes"][idx[1]] = {"table": t, "unique": int(idx[2]), "columns": cols}
    return out


def build_store(name):
    """Create the store fresh in a temp copy of its tool and return its fingerprint."""
    folder, snippet, rel = STORES[name]
    with tempfile.TemporaryDirectory(prefix="arti-schema-") as tmp:
        tmp = Path(tmp)
        (tmp / "tools").mkdir()
        shutil.copytree(CODE / "tools" / "_shared", tmp / "tools" / "_shared",
                        ignore=shutil.ignore_patterns("__pycache__"))
        dst = tmp / "tools" / folder
        shutil.copytree(CODE / "tools" / folder, dst,
                        ignore=shutil.ignore_patterns("__pycache__", "*.db", "*.db-wal", "*.db-shm"))
        env = dict(os.environ, ARTI_HOME=str(tmp), PYTHONDONTWRITEBYTECODE="1")
        code = f"import sys; sys.path.insert(0, {str(dst)!r}); {snippet}"
        r = subprocess.run([sys.executable, "-c", code], cwd=tmp, env=env, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"building {name} failed: {r.stderr.strip()[-600:]}")
        conn = sqlite3.connect(tmp / rel)
        try:
            return fingerprint(conn)
        finally:
            conn.close()


def build_all():
    return {name: build_store(name) for name in STORES}


def compare(baseline, current):
    """Violations of the additive-only rule (empty list = fine). New tables, columns and indexes are allowed."""
    bad = []
    if current["user_version"] < baseline["user_version"]:
        bad.append(f"user_version went down ({baseline['user_version']} -> {current['user_version']})")
    for t, cols in baseline["tables"].items():
        if t not in current["tables"]:
            bad.append(f"table {t} removed")
            continue
        for c, spec in cols.items():
            now = current["tables"][t].get(c)
            if now is None:
                bad.append(f"column {t}.{c} removed or renamed")
            elif now["type"] != spec["type"]:
                bad.append(f"column {t}.{c} type changed {spec['type']} -> {now['type']}")
            elif now["pk"] != spec["pk"]:
                bad.append(f"column {t}.{c} primary-key position changed")
            elif now["notnull"] and not spec["notnull"] and now["default"] is None:
                bad.append(f"column {t}.{c} became NOT NULL without a default")
        for c, now in current["tables"][t].items():
            if c not in cols and now["notnull"] and now["default"] is None and not now["pk"]:
                bad.append(f"new column {t}.{c} is NOT NULL without a default")
    for i, spec in baseline["indexes"].items():
        now = current["indexes"].get(i)
        if now is None:
            bad.append(f"index {i} removed")
        elif now["columns"] != spec["columns"] or now["unique"] != spec["unique"]:
            bad.append(f"index {i} changed")
    return bad


def main(argv):
    if "--write" in argv:
        data = build_all()
        BASELINE.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {BASELINE}")
        return 0
    data = build_all()
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    bad = [f"{n}: {m}" for n in base for m in compare(base[n], data[n])]
    print("\n".join(bad) if bad else "schema is additive against the baseline")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
