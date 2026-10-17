"""Schema changes must be additive: manual rollback puts old code on an already-migrated database.

Builds each store fresh from the working tree (tools/_shared/schema_snapshot.py) and compares it with
tests/licensing/schema_baseline.json, the schema of the last published release. After publishing a release run
`python tools/_shared/schema_snapshot.py --write` and commit the baseline. A deliberately breaking change needs
`requires_installer` for that release and a conscious baseline rewrite.
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _env import CODE  # noqa: E402

sys.path.insert(0, str(CODE / "tools" / "_shared"))
import schema_snapshot as ss  # noqa: E402

results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


base = json.loads(ss.BASELINE.read_text(encoding="utf-8"))
check("baseline covers the four stores", set(base) == set(ss.STORES), sorted(base))

now = ss.build_all()
for name in ss.STORES:
    bad = ss.compare(base[name], now[name])
    check(f"{name}: working tree is additive against the baseline", not bad, "; ".join(bad))
    check(f"{name}: building twice gives the same schema", ss.build_store(name) == now[name])

# The comparison itself: each kind of breaking change is caught, each additive change is allowed.
b = base["arti-lit"]
t = next(iter(b["tables"]))
col = next(c for c in b["tables"][t] if not b["tables"][t][c]["pk"])


def mutated(fn):
    c = copy.deepcopy(b)
    fn(c)
    return ss.compare(b, c)


check("catches a removed column", mutated(lambda c: c["tables"][t].pop(col)))
check("catches a removed table", mutated(lambda c: c["tables"].pop(t)))
check("catches a type change", mutated(lambda c: c["tables"][t][col].update(type="BLOB" if b["tables"][t][col]["type"] != "BLOB" else "TEXT")))
check("catches a lower user_version", mutated(lambda c: c.update(user_version=b["user_version"] - 1)))
check("catches a new NOT NULL column without default",
      mutated(lambda c: c["tables"][t].update(extra={"type": "TEXT", "notnull": 1, "default": None, "pk": 0})))
check("allows a new nullable column", not mutated(lambda c: c["tables"][t].update(extra={"type": "TEXT", "notnull": 0, "default": None, "pk": 0})))
check("allows a new NOT NULL column with a default", not mutated(lambda c: c["tables"][t].update(extra={"type": "TEXT", "notnull": 1, "default": "''", "pk": 0})))
check("allows a new table and a higher version", not mutated(lambda c: (c["tables"].update(extra_t={}), c.update(user_version=b["user_version"] + 1))))
j = base["jfinder-snapshot"]
if j["indexes"]:
    i = next(iter(j["indexes"]))
    cj = copy.deepcopy(j)
    cj["indexes"].pop(i)
    check("catches a removed index", ss.compare(j, cj))

print("\n%d checks, %d failed" % (len(results), results.count(False)))
sys.exit(0 if all(results) else 1)
