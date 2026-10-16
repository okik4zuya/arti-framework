"""tools/arti-search: the CLI, the persisted throttle state and the RIS writer (offline, no network).

Run with the vendored interpreter:  python\\python.exe tests\\search\\test_cli.py
Set ARTI_TEST_LIVE=1 to add three small live OpenAlex calls (anonymous pool).

Checks:
  * the Google Scholar cooldown written by one process is honoured by the next one, without a network call;
  * Semantic Scholar spacing persists (last_call is written after a call);
  * a corrupt or missing state file counts as "no state" and never raises;
  * --query-file (and stdin) read Boolean queries with quotes; --out writes the file and prints a summary;
    stdout is bounded by --max-chars; invalid choices are refused by argparse;
  * --no-keys hides keys that are set in the environment;
  * the RIS writer round-trips through `arti-lit library import-ris` (DOI dedup, abstract, journal).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CODE = Path(__file__).resolve().parents[2]
TOOL = CODE / "tools" / "arti-search"
sys.path.insert(0, str(TOOL))

results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)) if extra and not cond else ""))


TMP = Path(tempfile.mkdtemp(prefix="arti-search-test-"))
STATE = TMP / "state.json"
ENV = dict(os.environ, ARTI_SEARCH_STATE=str(STATE), OPENALEX_API_KEY="", SEMANTIC_SCHOLAR_API_KEY="")
os.environ["ARTI_SEARCH_STATE"] = str(STATE)


def cli(*args, stdin=None, env=None):
    p = subprocess.run([sys.executable, str(TOOL / "cli.py"), *args], capture_output=True, text=True,
                       input=stdin, env=env or ENV, timeout=120)
    try:
        out = json.loads(p.stdout) if p.stdout.strip() else None
    except ValueError:
        out = None
    return p.returncode, out, p.stdout, p.stderr


# ---- 1. Scholar cooldown persists across processes -------------------------------------------------------------
import state  # noqa: E402

state.save("googlescholar", {"cooldown_until": time.time() + 600, "consecutive_blocks": 2,
                             "last_call": time.time(), "paused": False})
t0 = time.time()
code, out, raw, err = cli("scholar", "--query", "anything")
check("scholar refuses during a persisted cooldown (exit 1)", code == 1 and out and "cooling down" in out.get("error", ""), raw + err)
check("the refusal needs no network (fast)", time.time() - t0 < 10, time.time() - t0)
check("the hint names the CLI routes, not MCP tools", out and "cli.py" in out.get("error", ""), out)
code, out, raw, _ = cli("sources")
check("sources reports the remaining cooldown", code == 0 and out["googlescholar"]["cooldown_remaining_s"] > 500, raw[:300])

# a block recorded by one process is visible to another
STATE.unlink()
subprocess.run([sys.executable, "-c",
                "import sys; sys.path.insert(0, %r); from sources.googlescholar import GoogleScholarSource as G; "
                "g = G(); g._begin_cooldown()" % str(TOOL)], env=ENV, check=True)
saved = state.load("googlescholar")
check("_begin_cooldown writes the state file", saved.get("cooldown_until", 0) > time.time() + 30 and saved.get("consecutive_blocks") == 1, saved)
code, out, raw, _ = cli("scholar", "--query", "anything")
check("a second process honours that cooldown", code == 1 and "cooling down" in (out or {}).get("error", ""), raw)

# ---- 2. Semantic Scholar spacing is persisted ------------------------------------------------------------------
STATE.unlink()
import sources.semanticscholar as s2  # noqa: E402

s2.get_json_with_retry = lambda *a, **k: {"data": []}
before = time.time()
s2._call("https://example.invalid/x")
last = state.load("semanticscholar").get("last_call", 0)
check("Semantic Scholar last_call is written after a call", before <= last <= time.time() + 1, last)

# ---- 3. corrupt / missing state never raises -------------------------------------------------------------------
STATE.write_text("{not json", encoding="utf-8")
check("a corrupt state file reads as empty", state.load("googlescholar") == {})
STATE.unlink()
check("a missing state file reads as empty", state.load("googlescholar") == {})
os.environ["ARTI_SEARCH_STATE"] = str(TMP / "no" / "such" / "dir" / "s.json")
state.save("x", {"a": 1})
check("saving into a new folder works", (TMP / "no" / "such" / "dir" / "s.json").exists())
os.environ["ARTI_SEARCH_STATE"] = str(STATE)

# ---- 4. query files, --out summary, --max-chars, validation ----------------------------------------------------
import cli as climod  # noqa: E402


class NS:
    def __init__(self, **kw):
        self.__dict__.update(dict(query=None, query_file=None, out=None, ris=None, snapshot=None, max_chars=24000))
        self.__dict__.update(kw)


qf = TMP / "q.txt"
qf.write_text('"literature screening"\n  AND (LLM OR "large language model")\n', encoding="utf-8")
check("--query-file keeps quotes and joins lines", climod.read_query(NS(query_file=str(qf))) == '"literature screening" AND (LLM OR "large language model")')
try:
    climod.read_query(NS())
    check("a missing query is an error", False)
except ValueError:
    check("a missing query is an error", True)

fake = {"meta": {"count": 3, "returned": 3, "cost_usd": 0.001, "oql": "get works"},
        "results": [{"paper_id": "W%d" % i, "title": "Paper %d" % i, "authors": ["Ann Lee", "Bo Chan"], "abstract": "A" * 400,
                     "doi": "10.1000/x%d" % i, "published_date": "2024-01-01T00:00:00", "url": "https://x/%d" % i,
                     "source": "openalex", "extra": {"type": "article", "year": 2024, "venue": "Journal of Tests"}}
                    for i in range(3)]}
outp = TMP / "res.json"
import io  # noqa: E402
import contextlib  # noqa: E402

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = climod.emit(fake, NS(out=str(outp), ris=str(TMP / "r.ris"), snapshot=str(TMP / "snap.json")))
summary = json.loads(buf.getvalue())
check("--out prints a summary, not the records", rc == 0 and summary["returned"] == 3 and "results" not in summary and summary["meta"]["count"] == 3, summary)
check("--out wrote the full result", json.loads(outp.read_text(encoding="utf-8"))["results"][2]["title"] == "Paper 2")
check("--snapshot wrote the raw JSON", (TMP / "snap.json").exists())

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    climod.emit(fake, NS(max_chars=600))
bounded = json.loads(buf.getvalue())
check("stdout is bounded by --max-chars (abstracts dropped)", len(buf.getvalue()) <= 700 and "truncated" in bounded, len(buf.getvalue()))

code, _, _, err = cli("count", "--group-by", "nonsense")
check("argparse refuses an invalid --group-by (exit 2)", code == 2, err[-200:])
code, out, _, _ = cli("fulltext", "--project", str(TMP))
check("fulltext without items is an error", code == 1 and "no items" in out["error"], out)
code, out, _, _ = cli("search", "--max", "1")
check("search with nothing to search is refused cleanly", code == 1 and out and "error" in out, out)

# ---- 5. --no-keys ---------------------------------------------------------------------------------------------------
import config  # noqa: E402

os.environ["OPENALEX_API_KEY"] = "secret-value"
check("a key set in the environment is visible", config.get_env("OPENALEX_API_KEY") == "secret-value")
config.ignore_keys()
check("--no-keys hides it", config.get_env("OPENALEX_API_KEY") is None)
os.environ["OPENALEX_API_KEY"] = ""

# ---- 6. RIS round trip through arti-lit ----------------------------------------------------------------------------
dup = json.loads(json.dumps(fake))
dup["results"].append(dict(dup["results"][0], paper_id="W99", title="Same paper, second source"))
ris = TMP / "round.ris"
ris.write_text(climod.to_ris(dup["results"]), encoding="utf-8")
proj = TMP / "project"
(proj / "literature").mkdir(parents=True)
p = subprocess.run([sys.executable, str(CODE / "tools" / "arti-lit" / "cli.py"), "library", "import-ris",
                    "--files", str(ris), "--project", str(proj)], capture_output=True, text=True, env=ENV)
res = json.loads(p.stdout)
check("import-ris accepts the generated RIS", res.get("ok") is True and res.get("imported") == 3, p.stdout[:300] + p.stderr[-200:])
check("a repeated DOI is skipped as a duplicate", len(res.get("skipped_duplicate", [])) == 1, res.get("skipped_duplicate"))
p = subprocess.run([sys.executable, str(CODE / "tools" / "arti-lit" / "cli.py"), "library", "get",
                    "--key", "lee-2024", "--project", str(proj)], capture_output=True, text=True, env=ENV)
row = json.loads(p.stdout).get("row", {})
check("keys follow surname-year", row.get("key") == "lee-2024", p.stdout[:300])
check("abstract and journal survive the round trip", (row.get("abstract") or "").startswith("AAAA") and row.get("journal_name") == "Journal of Tests", row)

# ---- 7. optional live calls ------------------------------------------------------------------------------------------
if os.environ.get("ARTI_TEST_LIVE") == "1":
    code, out, raw, _ = cli("count", "--query", "literature screening", "--group-by", "publication_year", "--no-keys")
    check("live: count by year", code == 0 and out["total"] > 0, raw[:200])
    code, out, raw, _ = cli("search", "--query", "literature screening", "--max", "2", "--no-abstracts", "--no-keys")
    check("live: search returns records with an oql", code == 0 and out["meta"]["oql"] and len(out["results"]) == 2, raw[:200])
    code, out, raw, _ = cli("sources", "--no-keys")
    check("live: sources reports OpenAlex reachable", code == 0 and out["openalex"]["keyword"]["reachable"] is True, raw[:200])

print("\n%d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
