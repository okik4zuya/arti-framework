"""Check every reference the draft cites, in one call (runbook phase 9, and the key list for phase 10).

    python.exe scripts/verify_refs.py --project P --draft writing/manuscript_draft1_2026-10-16.md

Collects the keys in `[LIT: k1, k2]` tags, looks each up in arti-lit, and sends the DOIs to `arti-search resolve`
(OpenAlex). Writes data/verification.json:
    {"cited": n, "resolved": n, "no_doi": [keys], "unknown_keys": [keys], "unresolved": [keys], "retracted": [keys],
     "keys": [all cited keys]}
and data/cited-keys.txt (comma list for `arti-lit library enrich --keys`). Prints the same JSON. Exit 1 when any cited
key is unknown, has no DOI, did not resolve, or is retracted: those citations must be fixed or removed before the .docx
is built (arti-docx --cite zotero stops on a key without metadata).
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import lit, run_json, tool_cmd, write_json  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--draft", required=True)
a = ap.parse_args()
project = Path(a.project)
text = Path(a.draft).read_text(encoding="utf-8")
keys = []
for m in re.finditer(r"\[LIT:\s*([^\]]+)\]", text):
    for k in m.group(1).split(","):
        k = k.strip().lower()
        if k and k not in keys:
            keys.append(k)

db = lit()
lib = {r["key"]: r for r in db.library_list(a.project)}
unknown = [k for k in keys if k not in lib]
no_doi = [k for k in keys if k in lib and not lib[k].get("doi")]
doi_of = {k: lib[k]["doi"] for k in keys if k in lib and lib[k].get("doi")}
unresolved, retracted, resolved = [], [], 0
if doi_of:
    items_file = project / "data" / "cited-dois.txt"
    items_file.parent.mkdir(parents=True, exist_ok=True)
    items_file.write_text("\n".join(doi_of.values()) + "\n", encoding="utf-8")
    out = project / "data" / "resolve-cited.json"
    code, data, raw, err = run_json(tool_cmd("arti-search", "resolve", "--items-file", items_file, "--project", project, "--out", out), timeout=300)
    full = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"items": []}
    by_doi = {(i.get("input") or "").lower(): i for i in full.get("items", [])}
    for k, doi in doi_of.items():
        row = by_doi.get(doi.lower())
        if not row or row.get("status") != "resolved":
            unresolved.append(k)
        else:
            resolved += 1
            if row.get("is_retracted"):
                retracted.append(k)
result = {"cited": len(keys), "resolved": resolved, "no_doi": no_doi, "unknown_keys": unknown, "unresolved": unresolved,
          "retracted": retracted, "keys": keys}
write_json(project / "data" / "verification.json", result)
(project / "data" / "cited-keys.txt").write_text(",".join(keys), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False))
sys.exit(1 if (unknown or no_doi or unresolved or retracted) else 0)
