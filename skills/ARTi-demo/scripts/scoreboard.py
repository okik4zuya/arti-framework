"""Write demo-scoreboard.md from the project's own files (nothing typed by hand).

    python.exe scripts/scoreboard.py --project P [--docx submission/manuscript.docx]

Reads demo-run-log.json, data/prisma-counts.json, data/verification.json ({"cited": n, "resolved": n, ...}, written in
phase 9), the figures folder, the draft's [LIT: key] tags, and the .docx itself (check_docx). Missing inputs show as
"n/a" instead of failing, so a partial run still gets an honest scoreboard.
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import SKILL_DIR, read_json  # noqa: E402
from check_docx import inspect  # noqa: E402

CAPABILITY_NAMES = {
    0: ("Scaffold, profiles, preflight", "ARTi-setup, preflight.py, seed_profiles.py"),
    1: ("Idea: gap map, novelty score, cross-citation check, journal choice", "ARTi-idea, citation-chase, arti-jfinder"),
    2: ("Literature search across sources, DOI dedup", "arti-search, arti-lit"),
    3: ("PRISMA-ScR screening with logged exclusion reasons", "arti-lit, screen.py"),
    4: ("Open-access full text, abstract-level fallback", "arti-search fulltext, arti-convert ingest"),
    5: ("Journal Profile (light) and Manuscript Blueprint", "ARTi-writing"),
    6: ("Classification and aggregation", "screen.py, aggregate.py"),
    7: ("Figures and tables (PRISMA, landscape, classification, graphical abstract)", "arti-compose, matplotlib, arti-table"),
    8: ("Scratchbook and manuscript draft", "ARTi-scratchbook, ARTi-writing"),
    9: ("Verification of references and numbers", "arti-search resolve, arti-lit"),
    10: ("Word manuscript with Zotero fields", "arti-lit enrich, arti-docx"),
}

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--docx", default="submission/manuscript.docx")
a = ap.parse_args()
P = Path(a.project)


def na(v):
    return "n/a" if v is None else str(v)


log = read_json(P / "demo-run-log.json", {}) or {}
counts = read_json(P / "data" / "prisma-counts.json", {}) or {}
ver = read_json(P / "data" / "verification.json", {}) or {}
docx_path = P / a.docx
info = {}
if docx_path.is_file():
    try:
        info = inspect(str(docx_path))
    except Exception as e:  # a broken docx must show up, not crash the scoreboard
        info = {"error": str(e)}

finished = datetime.now().strftime("%Y-%m-%d %H:%M")
minutes = None
if log.get("started"):
    minutes = round((datetime.now() - datetime.strptime(log["started"], "%Y-%m-%d %H:%M:%S")).total_seconds() / 60.0)

figs = sorted(p.name for p in (P / "figures").glob("Fig_[0-9]*.png"))
ga = sorted(p.name for p in (P / "figures").glob("graphical-abstract*.png")) + sorted(p.name for p in (P / "figures").glob("GA*.png"))
tables = sorted(p.name for p in (P / "figures").glob("Table *.md"))
drafts = sorted(glob.glob(str(P / "writing" / "manuscript_draft*.md")))
cited = None
if drafts:
    keys = set()
    for m in re.finditer(r"\[LIT:\s*([^\]]+)\]", Path(drafts[-1]).read_text(encoding="utf-8")):
        keys.update(k.strip() for k in m.group(1).split(",") if k.strip())
    cited = len(keys)

caps = ["| Capability | Tool | Phase minutes | Note |", "|---|---|---|---|"]
for ph in log.get("phases", []):
    name, tool = CAPABILITY_NAMES.get(ph["n"], (ph["name"], ""))
    caps.append("| %s | %s | %s | %s (%s) |" % (name, tool, ph["minutes"], (ph.get("note") or "").replace("|", "/"), ph["status"]))
phases = ["| Phase | Name | Minutes | Status |", "|---|---|---|---|"] + [
    "| %s | %s | %s | %s |" % (p["n"], p["name"], p["minutes"], p["status"]) for p in log.get("phases", [])]
problems = ["- " + p["text"] for p in log.get("problems", [])] or ["- none recorded"]

values = {
    "topic": log.get("topic", "n/a"), "project": str(P), "started": log.get("started", "n/a"), "finished": finished,
    "minutes": na(minutes), "docx": a.docx if docx_path.is_file() else "NOT PRODUCED",
    "identified": na(counts.get("identified_total")), "screened": na(counts.get("screened")), "included": na(counts.get("included")),
    "inc_full": na(counts.get("included_fulltext")), "inc_abs": na(counts.get("included_abstract_only")),
    "figures": "%d (%s)" % (len(figs), ", ".join(figs)) if figs else "0", "ga": ", ".join(ga) if ga else "none",
    "tables": "%d (%s)" % (len(tables), ", ".join(tables)) if tables else "0", "cited": na(cited),
    "resolved": na(ver.get("resolved")), "zitems": na(info.get("zotero_citation_fields")),
    "zbibl": na(info.get("zotero_bibliography_fields")), "images": na(info.get("images")), "words": na(info.get("words_approx")),
    "capabilities": "\n".join(caps), "phases": "\n".join(phases), "problems": "\n".join(problems),
}
text = (SKILL_DIR / "references" / "scoreboard-template.md").read_text(encoding="utf-8")
for k, v in values.items():
    text = text.replace("{{%s}}" % k, v)
(P / "demo-scoreboard.md").write_text(text, encoding="utf-8")
print(json.dumps({"ok": True, "out": str(P / "demo-scoreboard.md"), "minutes": minutes, "docx": docx_path.is_file()}))
