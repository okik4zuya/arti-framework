"""Aggregate the classified corpus and the OpenAlex landscape counts into the CSVs every figure and table is built from.

    python.exe scripts/aggregate.py --project P [--top-sources 10]

Reads (inside the project):
  data/classified.csv            written by screen.py apply (key, task, method, field, evidence, ...); access, journal,
                                 year and DOI are refreshed here from arti-lit, so run this again after the fulltext phase
  data/openalex-year.json        arti-search count --group-by publication_year --out ...   (optional)
  data/openalex-oa.json          arti-search count --group-by open_access.oa_status --out ... (optional)
  data/openalex-source.json      arti-search count --group-by primary_location.source.id --out ... (optional)
Writes (data/): classified.csv (refreshed), trend-year.csv, method-by-year.csv, method-counts.csv, task-counts.csv,
field-counts.csv, evidence-counts.csv, task-method.csv, top-journals.csv, coverage.csv, landscape-year.csv,
landscape-oa.csv, landscape-source.csv, and figures/Table 1.json + figures/Table 2.json (arti-table specs).
Prints a short JSON summary. Every number a figure or table shows comes from one of these files.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import lit, read_csv, read_json, write_csv, write_json, year_of  # noqa: E402

CLASS_FIELDS = ["key", "year", "doi", "journal", "task", "method", "field", "evidence", "access"]


def counts(rows, field, other="unclassified"):
    c = Counter((r.get(field) or other) for r in rows)
    return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--top-sources", type=int, default=10)
    a = ap.parse_args()
    project = Path(a.project)
    data = project / "data"
    figures = project / "figures"
    cpath = data / "classified.csv"
    if not cpath.exists():
        print(json.dumps({"ok": False, "error": "data/classified.csv is missing: run screen.py apply first"}))
        return 1

    db = lit()
    lib = {r["key"]: r for r in db.library_list(a.project)}
    rows = read_csv(cpath)
    for r in rows:
        src = lib.get(r["key"], {})
        r["year"] = year_of(r["key"])
        r["doi"] = src.get("doi") or r.get("doi") or ""
        r["journal"] = src.get("journal_name") or r.get("journal") or ""
        r["access"] = "fulltext" if src.get("read_status") in ("fulltext", "read") else "abstract"
    rows.sort(key=lambda r: r["key"])
    write_csv(cpath, rows, CLASS_FIELDS)

    # corpus tables
    years = sorted({r["year"] for r in rows if r["year"]})
    write_csv(data / "trend-year.csv", [{"year": y, "included": sum(1 for r in rows if r["year"] == y)} for y in years], ["year", "included"])
    methods = [m for m, _ in counts(rows, "method")]
    mby = Counter((r["year"], r.get("method") or "unclassified") for r in rows if r["year"])
    write_csv(data / "method-by-year.csv", [{"year": y, "method": m, "n": mby[(y, m)]} for y in years for m in methods if mby[(y, m)]],
              ["year", "method", "n"])
    for field, fname in (("method", "method-counts.csv"), ("task", "task-counts.csv"), ("field", "field-counts.csv"), ("evidence", "evidence-counts.csv")):
        write_csv(data / fname, [{field: k, "n": n} for k, n in counts(rows, field)], [field, "n"])
    tm = Counter((r.get("task") or "unclassified", r.get("method") or "unclassified") for r in rows)
    write_csv(data / "task-method.csv", [{"task": t, "method": m, "n": n} for (t, m), n in sorted(tm.items())], ["task", "method", "n"])
    journals = Counter(r["journal"] for r in rows if r["journal"])
    top = journals.most_common(a.top_sources)
    write_csv(data / "top-journals.csv", [{"journal": j, "n": n} for j, n in top], ["journal", "n"])

    # evidence coverage: fulltext versus abstract-only
    cov = []
    for ev, n in counts(rows, "evidence"):
        sub = [r for r in rows if (r.get("evidence") or "unclassified") == ev]
        full = sum(1 for r in sub if r["access"] == "fulltext")
        cov.append({"evidence": ev, "included": n, "fulltext": full, "abstract_only": n - full,
                    "pct_fulltext": round(100.0 * full / n) if n else 0})
    total_full = sum(1 for r in rows if r["access"] == "fulltext")
    cov.append({"evidence": "All included", "included": len(rows), "fulltext": total_full, "abstract_only": len(rows) - total_full,
                "pct_fulltext": round(100.0 * total_full / len(rows)) if rows else 0})
    write_csv(data / "coverage.csv", cov, ["evidence", "included", "fulltext", "abstract_only", "pct_fulltext"])

    # OpenAlex landscape (what exists in the whole index for the same query)
    this_year = date.today().year
    ly = read_json(data / "openalex-year.json", {}) or {}
    groups = [g for g in ly.get("groups", []) if str(g.get("key", "")).isdigit() and int(g["key"]) <= this_year]
    if groups:
        write_csv(data / "landscape-year.csv", [{"year": g["key"], "works": g["count"]} for g in sorted(groups, key=lambda g: g["key"])], ["year", "works"])
    lo = read_json(data / "openalex-oa.json", {}) or {}
    if lo.get("groups"):
        write_csv(data / "landscape-oa.csv", [{"oa_status": g["label"] or g["key"], "works": g["count"]}
                                              for g in sorted(lo["groups"], key=lambda g: -g["count"])], ["oa_status", "works"])
    ls = read_json(data / "openalex-source.json", {}) or {}
    if ls.get("groups"):
        top_sources = sorted(ls["groups"], key=lambda g: -g["count"])[:a.top_sources]
        write_csv(data / "landscape-source.csv", [{"source": g["label"] or g["key"], "works": g["count"]} for g in top_sources], ["source", "works"])

    # arti-table specs
    full_rows = [r for r in rows if r["access"] == "fulltext"][:13]
    t1 = {"table": "Table 1", "caption": "Characteristics of the included sources assessed at full text (task, approach family, field and evidence type as classified in this review).",
          "columns": ["Source", "Year", "Task", "Approach", "Field", "Evidence"], "align": ["left", "right", "left", "left", "left", "left"],
          "rows": [[r["key"], r["year"], r.get("task", ""), r.get("method", ""), r.get("field", ""), r.get("evidence", "")] for r in full_rows]}
    t2 = {"table": "Table 2", "caption": "Evidence base by study type: included sources read at full text versus assessed from the abstract only.",
          "columns": ["Evidence type", "Included", "Full text", "Abstract only", "Full text (%)"], "align": ["left", "right", "right", "right", "right"],
          "rows": [[c["evidence"], c["included"], c["fulltext"], c["abstract_only"], c["pct_fulltext"]] for c in cov]}
    write_json(figures / "Table 1.json", t1)
    write_json(figures / "Table 2.json", t2)

    print(json.dumps({"ok": True, "included": len(rows), "fulltext": total_full, "abstract_only": len(rows) - total_full,
                      "years": [years[0], years[-1]] if years else [], "top_method": counts(rows, "method")[0] if rows else None,
                      "landscape": bool(groups), "table1_rows": len(full_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
