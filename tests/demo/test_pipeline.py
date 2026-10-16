"""ARTi-demo scripts end to end on synthetic data (no network unless ARTI_TEST_LIVE=1).

Run with the vendored interpreter:  python\\python.exe tests\\demo\\test_pipeline.py

Builds a throwaway paper project, imports 40 synthetic records through the real arti-lit, screens and classifies them with
screen.py, aggregates, renders the figures and tables, writes the run log and the scoreboard, and checks a real .docx.
Needs Edge or Chrome for the arti-compose figures (those checks are skipped, loudly, when no browser is found).
ARTI_TEST_LIVE=1 adds the Zotero round trip (Crossref lookups for two real DOIs).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

CODE = Path(__file__).resolve().parents[2]
SK = CODE / "skills" / "ARTi-demo"
SCRIPTS = SK / "scripts"
sys.path.insert(0, str(CODE))
sys.path.insert(0, str(CODE / "tools" / "arti-search"))

results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print(("PASS " if cond else "FAIL ") + name + (("  " + str(extra)[:400]) if extra and not cond else ""))


def run(script, *args, env=None, expect_ok=True):
    p = subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True,
                       encoding="utf-8", env=env or os.environ.copy(), timeout=300)
    return p.returncode, p.stdout, p.stderr


def jrun(script, *args, **kw):
    code, out, err = run(script, *args, **kw)
    try:
        return code, json.loads(out.strip().splitlines()[-1] if out.strip().startswith("{") is False else out), err
    except ValueError:
        return code, None, out + err


from tools._shared.browser import find_browser  # noqa: E402

BROWSER = find_browser()
TMP = Path(tempfile.mkdtemp(prefix="arti-demo-test-"))
PROJ = TMP / "project"

# ---- 1. scaffold -----------------------------------------------------------------------------------------------
code, out, err = run("scaffold_project.py", "--path", PROJ, "--name", "Demo test", "--no-register")
data = json.loads(out)
check("scaffold creates the standard folders", data.get("ok") and {"idea", "writing", "literature", "data", "figures", "submission", "memory"} <= set(data["folders"]), out)
check("scaffold writes the root CLAUDE.md", (PROJ / "CLAUDE.md").is_file())

# ---- 2. synthetic corpus -> RIS -> arti-lit ---------------------------------------------------------------------
import cli as searchcli  # noqa: E402

TASKS = ["title and abstract screening", "data extraction", "risk-of-bias appraisal", "search strategy"]
METHODS = ["large language model", "classical machine learning", "rule-based", "hybrid"]
FIELDS = ["medicine", "software engineering", "education"]
EVID = ["benchmark evaluation", "case study", "review", "tool description"]
recs = []
for i in range(40):
    year = 2021 + i % 6
    recs.append({"paper_id": "W%d" % i, "title": "Synthetic study number %d on screening" % i, "authors": ["Ana Surname%d" % i, "Bo Other"],
                 "abstract": "This synthetic abstract number %d describes a method and a result." % i, "doi": "10.9999/synthetic.%d" % i,
                 "published_date": "%d-01-01T00:00:00" % year, "url": "https://example.org/%d" % i, "source": "openalex",
                 "extra": {"type": "article", "year": year, "venue": "Journal of Synthetic %d" % (i % 3)}})
(PROJ / "literature" / "exports").mkdir(parents=True, exist_ok=True)
ris = PROJ / "literature" / "exports" / "synthetic.ris"
ris.write_text(searchcli.to_ris(recs), encoding="utf-8")
p = subprocess.run([sys.executable, str(CODE / "tools" / "arti-lit" / "cli.py"), "library", "import-ris", "--files", str(ris), "--project", str(PROJ)],
                   capture_output=True, text=True, encoding="utf-8")
imp = json.loads(p.stdout)
check("import-ris loads 40 records", imp.get("imported") == 40, p.stdout[:200])

# ---- 3. screening ------------------------------------------------------------------------------------------------
out_md = PROJ / "data" / "batch.md"
code, out, err = run("screen.py", "dump", "--project", PROJ, "--out", out_md, "--limit", 10)
check("dump writes a compact batch file", out_md.is_file() and "## surname0-2021" in out_md.read_text(encoding="utf-8") and "DOI: yes" in out_md.read_text(encoding="utf-8"), err)

keys = []
for r in json.loads(subprocess.run([sys.executable, str(CODE / "tools" / "arti-lit" / "cli.py"), "library", "list", "--project", str(PROJ)],
                                   capture_output=True, text=True, encoding="utf-8").stdout)["rows"]:
    keys.append(r["key"])
keys.sort()
rows = ["key,stage,reason,search_source,task,method,field,evidence"]
for i, k in enumerate(keys):
    if i < 30:
        rows.append("%s,included,,DB:openalex,%s,%s,%s,%s" % (k, TASKS[i % 4], METHODS[i % 4], FIELDS[i % 3], EVID[i % 4]))
    elif i < 36:
        rows.append("%s,excluded_title_abstract,E1: off topic,DB:openalex,,,," % k)
    else:
        rows.append("%s,excluded_eligibility,E2: no method described,DB:openalex,,,," % k)
dec = PROJ / "data" / "decisions.csv"
dec.write_text("\n".join(rows) + "\n", encoding="utf-8")
code, out, err = run("screen.py", "apply", "--project", PROJ, "--decisions", dec)
res = json.loads(out)
check("apply records 30 included, 6 + 4 excluded", res.get("applied") == {"included": 30, "excluded_title_abstract": 6, "excluded_eligibility": 4}, out)
bad = PROJ / "data" / "bad.csv"
bad.write_text("key,stage\nnot-a-key,included\n%s,maybe\n" % keys[0], encoding="utf-8")
code, out, err = run("screen.py", "apply", "--project", PROJ, "--decisions", bad)
res = json.loads(out)
check("apply refuses an unknown key and an unknown stage (exit 1)", code == 1 and res["unknown_keys"] == ["not-a-key"] and res["bad_stage"][0]["stage"] == "maybe", out)

# six included sources "read at full text"
for k in keys[:6]:
    subprocess.run([sys.executable, str(CODE / "tools" / "arti-lit" / "cli.py"), "library", "update", "--key", k, "--status", "fulltext", "--project", str(PROJ)],
                   capture_output=True, text=True)
code, out, err = run("screen.py", "counts", "--project", PROJ, "--out", PROJ / "data" / "prisma-counts.json", "--identified", "openalex=45", "--identified", "s2=5", "--dups", 10)
c = json.loads(out)
check("PRISMA counts add up", c["screened"] == 40 and c["excluded_title_abstract"] == 6 and c["assessed_for_eligibility"] == 34
      and c["excluded_eligibility"] == 4 and c["included"] == 30 and c["unfinished_rows"] == 0, out)
check("full text versus abstract-only split", c["included_fulltext"] == 6 and c["included_abstract_only"] == 24, out)
check("identified total comes from the sources", c["identified_total"] == 50 and c["duplicates_removed"] == 10, out)
check("exclusion reasons are counted per stage", c["top_exclusion_reasons_title_abstract"] == [["E1", 6]] and c["top_exclusion_reasons_eligibility"] == [["E2", 4]], c)

# ---- 4. aggregation ------------------------------------------------------------------------------------------------
(PROJ / "data" / "openalex-year.json").write_text(json.dumps({"total": 600, "groups": [{"key": str(y), "label": str(y), "count": 50 * (y - 2018)} for y in range(2019, 2027)]}), encoding="utf-8")
(PROJ / "data" / "openalex-oa.json").write_text(json.dumps({"groups": [{"key": "gold", "label": "gold", "count": 300}, {"key": "closed", "label": "closed", "count": 200}, {"key": "green", "label": "green", "count": 100}]}), encoding="utf-8")
(PROJ / "data" / "openalex-source.json").write_text(json.dumps({"groups": [{"key": "S%d" % i, "label": "Journal of Synthetic %d" % i, "count": 100 - 9 * i} for i in range(8)]}), encoding="utf-8")
code, out, err = run("aggregate.py", "--project", PROJ)
agg = json.loads(out)
check("aggregate reports the corpus", agg.get("ok") and agg["included"] == 30 and agg["fulltext"] == 6 and agg["abstract_only"] == 24, out + err)
for f in ("trend-year.csv", "method-by-year.csv", "task-counts.csv", "task-method.csv", "top-journals.csv", "coverage.csv", "landscape-year.csv", "landscape-oa.csv", "landscape-source.csv"):
    check("data/%s exists" % f, (PROJ / "data" / f).is_file())
cov = (PROJ / "data" / "coverage.csv").read_text(encoding="utf-8").strip().splitlines()
check("coverage ends with the All-included row", cov[-1].startswith("All included,30,6,24,20"), cov[-1])
t1 = json.loads((PROJ / "figures" / "Table 1.json").read_text(encoding="utf-8"))
check("Table 1 lists the 6 full-text sources", len(t1["rows"]) == 6 and t1["columns"][0] == "Source")
p = subprocess.run([sys.executable, str(CODE / "tools" / "arti-table" / "render.py"), "--spec", str(PROJ / "figures" / "Table 2.json"), "--out-dir", str(PROJ / "figures")],
                   capture_output=True, text=True)
tmd = (PROJ / "figures" / "Table 2.md").read_text(encoding="utf-8")
check("arti-table renders Table 2 with a caption arti-docx will treat as one", tmd.startswith("**Table 2.**") and "| All included" in tmd, tmd[:120])

# ---- 5. figures -----------------------------------------------------------------------------------------------------
code, out, err = run("build_fig_classification.py", "--project", PROJ)
check("classification figures are written", (PROJ / "figures" / "Fig_3_classification.png").stat().st_size > 20000 and (PROJ / "figures" / "Fig_4_evidence-map.png").is_file(), out + err)
if BROWSER:
    code, out, err = run("build_fig_prisma.py", "--project", PROJ)
    check("PRISMA flow renders through arti-compose", (PROJ / "figures" / "Fig_1.png").is_file() and (PROJ / "figures" / "Fig_1.pdf").is_file(), out + err)
    check("PRISMA flow: compose reports 0 fail and 0 warn", ", 0 warn, 0 fail" in out, out)
    html = (PROJ / "figures" / "src" / "Fig_1.html").read_text(encoding="utf-8")
    check("PRISMA flow carries the counts", "=&nbsp;50" in html and "=&nbsp;30" in html and "{{" not in html.split("</style>")[1])
    code, out, err = run("build_fig_landscape.py", "--project", PROJ)
    check("landscape composite renders", (PROJ / "figures" / "Fig_2.png").is_file() and (PROJ / "figures" / "Fig_2.pdf").is_file(), out + err)
    check("landscape composite: compose reports 0 fail", ", 0 fail" in out, out)
else:
    print("SKIP figures that need Edge or Chrome: none found on this machine")

# ---- 5b. full-text helpers and reference verification ----------------------------------------------------------------
code, out, err = run("screen.py", "dois", "--project", PROJ)
d = json.loads(out)
check("dois lists the included DOIs", d["included"] == 30 and d["with_doi"] == 30 and len((PROJ / "data" / "included-dois.txt").read_text(encoding="utf-8").split()) == 30, out)
dois = (PROJ / "data" / "included-dois.txt").read_text(encoding="utf-8").split()
resolved = {"items": [{"input": doi, "status": "resolved", "doi": doi, "openalex_id": "W%d" % i, "oa_status": "gold" if i < 8 else "closed",
                       "content_pdf_available": i < 8, "is_retracted": i == 2, "cited_by_count": 100 - i} for i, doi in enumerate(dois)]}
(PROJ / "data" / "resolve-included.json").write_text(json.dumps(resolved), encoding="utf-8")
code, out, err = run("screen.py", "fulltext-items", "--project", PROJ, "--resolved", PROJ / "data" / "resolve-included.json", "--max", 5, "--out", PROJ / "data" / "fulltext-items.json")
items = json.loads((PROJ / "data" / "fulltext-items.json").read_text(encoding="utf-8"))
check("fulltext-items picks open-access, non-retracted records, most cited first", len(items) == 5 and items[0]["id_or_doi"] == "W0" and all(i["id_or_doi"] != "W2" for i in items), items)
result = {"items": [{"key": items[0]["key"], "status": "ok"}, {"key": items[1]["key"], "status": "ok"}, {"key": items[2]["key"], "status": "no_content"}]}
(PROJ / "data" / "fulltext-result.json").write_text(json.dumps(result), encoding="utf-8")
code, out, err = run("screen.py", "manifest", "--result", PROJ / "data" / "fulltext-result.json", "--out", PROJ / "literature" / "fulltext" / "manifest.csv")
man = (PROJ / "literature" / "fulltext" / "manifest.csv").read_text(encoding="utf-8").splitlines()
check("manifest lists only the downloaded files", man[0] == "pdf_filename,key" and len(man) == 3 and man[1].endswith(items[0]["key"]), man)
subprocess.run([sys.executable, str(CODE / "tools" / "arti-lit" / "cli.py"), "library", "add", "--key", "nodoi-2020", "--citation", "No DOI (2020). A record.", "--project", str(PROJ)], capture_output=True, text=True)
draft = PROJ / "writing" / "draft-verify.md"
draft.parent.mkdir(exist_ok=True)
draft.write_text("Text [LIT: nodoi-2020] and [LIT: ghost-1999].\n", encoding="utf-8")
code, out, err = run("verify_refs.py", "--project", PROJ, "--draft", draft)
v = json.loads(out)
check("verify_refs flags an unknown key and a key without a DOI (exit 1)", code == 1 and v["unknown_keys"] == ["ghost-1999"] and v["no_doi"] == ["nodoi-2020"] and v["cited"] == 2, out)
check("verify_refs writes the key list for library enrich", (PROJ / "data" / "cited-keys.txt").read_text(encoding="utf-8") == "nodoi-2020,ghost-1999")
subprocess.run([sys.executable, str(CODE / "tools" / "arti-lit" / "cli.py"), "library", "remove", "--key", "nodoi-2020", "--project", str(PROJ)], capture_output=True, text=True)
if os.environ.get("ARTI_TEST_LIVE") == "1":
    draft.write_text("Real [LIT: surname0-2021] but synthetic DOI.\n", encoding="utf-8")
    code, out, err = run("verify_refs.py", "--project", PROJ, "--draft", draft)
    v = json.loads(out)
    check("live: a synthetic DOI does not resolve in OpenAlex (exit 1)", code == 1 and v["unresolved"] == ["surname0-2021"], out)

# ---- 6. run log and scoreboard ---------------------------------------------------------------------------------------
code, d, _ = jrun("run_log.py", "init", "--project", PROJ, "--topic", "Synthetic topic")
check("run log starts", d and d["ok"] and not d["resumed"], d)
code, d, _ = jrun("run_log.py", "phase", "--project", PROJ, "--n", 0, "--name", "Setup", "--note", "test")
check("a phase is closed with real minutes", d and d["ok"] and d["last_phase"] == 0, d)
jrun("run_log.py", "problem", "--project", PROJ, "--text", "Scholar cooldown: skipped")
code, d, _ = jrun("run_log.py", "init", "--project", PROJ)
check("init again resumes instead of resetting", d and d["resumed"] and d["last_phase"] == 0, d)

# a small manuscript with an image and a table -> real .docx
(PROJ / "writing").mkdir(exist_ok=True)
md = PROJ / "writing" / "manuscript_draft1_test.md"
md.write_text("# Test manuscript\n\n## Introduction\n\nA claim [LIT: surname0-2021] and another [LIT: surname1-2022].\n\n"
              "![Flow](../figures/Fig_3_classification.png)\n\n**Fig. 1.** Test figure.\n\n" + (PROJ / "figures" / "Table 2.md").read_text(encoding="utf-8") + "\n## References\n\n", encoding="utf-8")
docx = PROJ / "submission" / "manuscript.docx"
p = subprocess.run([sys.executable, str(CODE / "tools" / "arti-docx" / "render.py"), "--md", str(md), "--out", str(docx)], capture_output=True, text=True, encoding="utf-8")
check("arti-docx builds the test manuscript", docx.is_file(), p.stdout + p.stderr)
code, out, err = run("check_docx.py", docx)
info = json.loads(out)
check("check_docx counts the image and the table", info["images"] >= 1 and info["tables"] >= 1, out)
code, out, err = run("check_docx.py", docx, "--expect-zotero")
check("check_docx --expect-zotero fails on a plain docx (exit 1)", code == 1, out)
code, out, err = run("scoreboard.py", "--project", PROJ)
board = (PROJ / "demo-scoreboard.md").read_text(encoding="utf-8")
check("scoreboard is written from the project files", "Synthetic topic" in board and "| Sources included | 30 |" in board and "Scholar cooldown" in board, board[:600])
check("scoreboard has no unfilled placeholder", "{{" not in board)

# ---- 7. optional Zotero round trip (live Crossref) --------------------------------------------------------------------
if os.environ.get("ARTI_TEST_LIVE") == "1":
    z = TMP / "zproject"
    run("scaffold_project.py", "--path", z, "--name", "Zotero test", "--no-register")
    for key, doi, cit in (("harris-2020", "10.1038/s41586-020-2649-2", "Harris et al. (2020). Array programming with NumPy. Nature."),
                          ("virtanen-2020", "10.1038/s41592-019-0686-2", "Virtanen et al. (2020). SciPy 1.0. Nature Methods.")):
        subprocess.run([sys.executable, str(CODE / "tools" / "arti-lit" / "cli.py"), "library", "add", "--key", key, "--citation", cit, "--doi", doi, "--project", str(z)],
                       capture_output=True, text=True)
    p = subprocess.run([sys.executable, str(CODE / "tools" / "arti-lit" / "cli.py"), "library", "enrich", "--keys", "harris-2020,virtanen-2020", "--project", str(z)],
                       capture_output=True, text=True, encoding="utf-8")
    en = json.loads(p.stdout)
    check("library enrich fills csl_json for both DOIs", len(en.get("enriched", [])) + len(en.get("already", [])) == 2 and not en.get("failed"), p.stdout[:300])
    zmd = z / "writing" / "m.md"
    zmd.parent.mkdir(exist_ok=True)
    zmd.write_text("# Z\n\n## Introduction\n\nArrays [LIT: harris-2020] and science [LIT: virtanen-2020].\n\n## References\n\n", encoding="utf-8")
    zd = z / "submission" / "manuscript.docx"
    p = subprocess.run([sys.executable, str(CODE / "tools" / "arti-docx" / "render.py"), "--md", str(zmd), "--out", str(zd), "--cite", "zotero", "--project", str(z)],
                       capture_output=True, text=True, encoding="utf-8")
    check("arti-docx --cite zotero builds", zd.is_file(), p.stdout + p.stderr)
    code, out, err = run("check_docx.py", zd, "--expect-zotero")
    zi = json.loads(out)
    check("the .docx holds two citation fields and one bibliography field", code == 0 and zi["zotero_citation_fields"] == 2 and zi["zotero_bibliography_fields"] == 1, out)

# ---- 8. profile seeding never overwrites ---------------------------------------------------------------------------------
fake = TMP / "fakehome"
(fake / "voice-profiles").mkdir(parents=True)
(fake / "memory").mkdir()
(fake / "memory" / "researcher-profile.md").write_text("REAL PROFILE\n", encoding="utf-8")
(fake / "voice-profiles" / "00-INDEX.md").write_text("# Voice Profile Catalog\n\n| Profile | Type | Field | Source | Last confirmed |\n|---|---|---|---|---|\n| [x](x.md) | Pointer | f | s | d |\n\n---\n", encoding="utf-8")
env = dict(os.environ, ARTI_HOME=str(fake))
code, out, err = run("seed_profiles.py", env=env)
check("a real researcher profile is kept", (fake / "memory" / "researcher-profile.md").read_text(encoding="utf-8") == "REAL PROFILE\n", out)
check("the demo voice profile is installed", (fake / "voice-profiles" / "demo-generic.md").is_file())
idx = (fake / "voice-profiles" / "00-INDEX.md").read_text(encoding="utf-8")
check("the catalog row is added after the existing row", idx.count("[demo-generic.md]") == 1 and idx.index("[x](x.md)") < idx.index("demo-generic"), idx)
code, out, err = run("seed_profiles.py", env=env)
check("a second run changes nothing", (fake / "voice-profiles" / "00-INDEX.md").read_text(encoding="utf-8") == idx and '"kept"' in out, out)

print("\n%d/%d passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
