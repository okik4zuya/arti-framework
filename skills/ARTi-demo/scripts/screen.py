"""Bulk screening helpers on top of arti-lit (in-process, the same code `arti-lit library update` runs).

    python.exe scripts/screen.py dump   --project P --out data/screening-batch-1.md [--start 0] [--limit 50] [--chars 700] [--all]
    python.exe scripts/screen.py apply  --project P --decisions data/decisions-1.csv
    python.exe scripts/screen.py counts --project P --out data/prisma-counts.json
                                        [--identified openalex=96 --identified s2=20] [--dups 12]
    python.exe scripts/screen.py dois   --project P
    python.exe scripts/screen.py fulltext-items --project P --resolved data/resolve-included.json [--max 10] [--out data/fulltext-items.json]
    python.exe scripts/screen.py manifest --result data/fulltext-result.json --out literature/fulltext/manifest.csv

`dump` writes a compact Markdown file (key, citation, whether a DOI exists, abstract trimmed to --chars) for the rows
that have no screening stage yet (all rows with --all), so the researcher side reads 50 abstracts at a time instead of
a 100-row JSON.

`apply` reads a decisions CSV with columns
    key, stage, reason, search_source, task, method, field, evidence
(only key and stage are required) and writes each decision to arti-lit: `screening_stage`, `exclusion_reason`,
`search_source`; included rows with an abstract get read_status `abstract`. Stages: included,
excluded_title_abstract, excluded_eligibility (the final state of each row; eligibility is judged at abstract level
here, full texts come afterwards for a subset). For included rows the classification columns are merged into
`data/classified.csv` next to the project's `literature/` folder.

`dois` writes the DOIs of the included rows (data/included-dois.txt, one per line) and data/included-keys.csv (key,doi).
`fulltext-items` picks the included rows whose OpenAlex record says a PDF can be had (from `arti-search resolve --out`) and
writes the JSON list `arti-search fulltext --items-file` takes. `manifest` turns the `fulltext --out` result into the
`manifest.csv` that `arti-convert ingest` needs (only the files that were downloaded).

`counts` computes the PRISMA-ScR numbers from arti-lit (the single source of truth) and the per-record
classification coverage, and writes JSON for build_fig_prisma.py and the scoreboard.
"""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import lit, read_csv, write_csv, write_json, year_of  # noqa: E402

FINAL_STAGES = ("included", "excluded_title_abstract", "excluded_eligibility")
OUTSIDE_STAGES = ("outside_flow", "prior_review")  # kept in the library, not part of the PRISMA flow (journal-profile samples)
CLASS_FIELDS = ["key", "year", "doi", "journal", "task", "method", "field", "evidence", "access"]
OUTSIDE = ("prior_review", "outside_flow")


def rows_of(db, project):
    return [r for r in db.library_list(project) if r.get("screening_stage") not in OUTSIDE]


def cmd_dump(a):
    db = lit()
    rows = db.library_list(a.project)
    if not a.all:
        rows = [r for r in rows if not r.get("screening_stage")]
    total = len(rows)
    rows = rows[a.start:a.start + a.limit]
    out = ["# Screening batch (%d-%d of %d rows)\n" % (a.start + 1, a.start + len(rows), total)]
    for r in rows:
        abstract = " ".join((r.get("abstract") or "").split())
        if len(abstract) > a.chars:
            abstract = abstract[:a.chars].rstrip() + " ..."
        out.append("## %s\n%s\nDOI: %s | stage: %s\n\n%s\n" % (
            r["key"], r["citation"], "yes" if r.get("doi") else "NO", r.get("screening_stage") or "-",
            abstract or "(no abstract)"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(out), encoding="utf-8")
    print(json.dumps({"ok": True, "out": a.out, "rows_in_file": len(rows), "rows_unscreened_total": total}))


def cmd_apply(a):
    db = lit()
    decisions = read_csv(a.decisions)
    existing = {r["key"]: r for r in db.library_list(a.project)}
    classified_path = Path(a.project) / "data" / "classified.csv"
    classified = {r["key"]: r for r in (read_csv(classified_path) if classified_path.exists() else [])}
    done, unknown, bad = Counter(), [], []
    for d in decisions:
        key = (d.get("key") or "").strip().lower()
        stage = (d.get("stage") or "").strip()
        if key not in existing:
            unknown.append(key)
            continue
        if stage not in FINAL_STAGES + OUTSIDE_STAGES:
            bad.append({"key": key, "stage": stage})
            continue
        row = existing[key]
        kwargs = {"screening_stage": stage}
        reason = (d.get("reason") or "").strip()
        if stage.startswith("excluded"):
            kwargs["exclusion_reason"] = reason or "no reason given"
        if (d.get("search_source") or "").strip():
            kwargs["search_source"] = d["search_source"].strip()
        if stage == "included" and row.get("abstract") and row.get("read_status") == "export-only":
            kwargs["read_status"] = "abstract"
        db.library_update(a.project, key, **kwargs)
        done[stage] += 1
        if stage == "included":
            c = classified.get(key, {})
            c.update({"key": key, "year": year_of(key), "doi": row.get("doi") or "", "journal": row.get("journal_name") or "",
                      "task": (d.get("task") or c.get("task") or "").strip(), "method": (d.get("method") or c.get("method") or "").strip(),
                      "field": (d.get("field") or c.get("field") or "").strip(), "evidence": (d.get("evidence") or c.get("evidence") or "").strip(),
                      "access": c.get("access") or "abstract"})
            classified[key] = c
    if classified:
        write_csv(classified_path, sorted(classified.values(), key=lambda r: r["key"]), CLASS_FIELDS)
    print(json.dumps({"ok": not (unknown or bad), "applied": dict(done), "unknown_keys": unknown, "bad_stage": bad,
                      "classified_rows": len(classified)}, ensure_ascii=False))
    return 0 if not (unknown or bad) else 1


def cmd_counts(a):
    db = lit()
    rows = rows_of(db, a.project)
    stage = Counter(r.get("screening_stage") or "none" for r in rows)
    screened = len(rows)
    excluded_ta = stage["excluded_title_abstract"]
    excluded_elig = stage["excluded_eligibility"]
    included_rows = [r for r in rows if r.get("screening_stage") == "included"]
    included = len(included_rows)
    full = sum(1 for r in included_rows if r.get("read_status") in ("fulltext", "read"))
    r_ta, r_el = Counter(), Counter()
    for r in rows:
        label = (r.get("exclusion_reason") or "no reason").split(":")[0].strip()[:60]
        if r.get("screening_stage") == "excluded_title_abstract":
            r_ta[label] += 1
        elif r.get("screening_stage") == "excluded_eligibility":
            r_el[label] += 1
    ident = {}
    for item in a.identified or []:
        name, _, n = item.partition("=")
        ident[name.strip()] = int(n)
    dups = a.dups or 0
    out = {
        "identified_by_source": ident,
        "identified_total": sum(ident.values()) if ident else screened + dups,
        "duplicates_removed": dups,
        "screened": screened,
        "excluded_title_abstract": excluded_ta,
        "assessed_for_eligibility": screened - excluded_ta,
        "excluded_eligibility": excluded_elig,
        "included": included,
        "included_fulltext": full,
        "included_abstract_only": included - full,
        "unfinished_rows": screened - excluded_ta - excluded_elig - included,
        "top_exclusion_reasons_title_abstract": r_ta.most_common(4),
        "top_exclusion_reasons_eligibility": r_el.most_common(4),
        "stage_counts": dict(stage),
    }
    write_json(a.out, out)
    print(json.dumps(out, ensure_ascii=False))


def cmd_dois(a):
    db = lit()
    rows = [r for r in db.library_list(a.project, screening_stage="included")]
    data = Path(a.project) / "data"
    data.mkdir(parents=True, exist_ok=True)
    withdoi = [r for r in rows if r.get("doi")]
    (data / "included-dois.txt").write_text("\n".join(r["doi"] for r in withdoi) + "\n", encoding="utf-8")
    write_csv(data / "included-keys.csv", [{"key": r["key"], "doi": r["doi"]} for r in withdoi], ["key", "doi"])
    print(json.dumps({"ok": True, "included": len(rows), "with_doi": len(withdoi), "out": str(data / "included-dois.txt")}))


def cmd_fulltext_items(a):
    resolved = json.loads(Path(a.resolved).read_text(encoding="utf-8"))
    keys = {r["doi"].lower(): r["key"] for r in read_csv(Path(a.project) / "data" / "included-keys.csv")}
    cand = []
    for it in resolved.get("items", []):
        doi = (it.get("doi") or "").lower()
        if doi in keys and it.get("status") == "resolved" and not it.get("is_retracted") and                 (it.get("content_pdf_available") or it.get("oa_status") in ("gold", "green", "hybrid", "bronze", "diamond")):
            cand.append({"id_or_doi": it.get("openalex_id") or doi, "key": keys[doi], "cited_by": it.get("cited_by_count") or 0})
    cand.sort(key=lambda c: -c["cited_by"])
    items = [{"id_or_doi": c["id_or_doi"], "key": c["key"]} for c in cand[:a.max]]
    write_json(a.out, items)
    print(json.dumps({"ok": True, "candidates": len(cand), "items": len(items), "out": a.out}))


def cmd_manifest(a):
    result = json.loads(Path(a.result).read_text(encoding="utf-8"))
    ok = [i for i in result.get("items", []) if i.get("status") in ("ok", "skipped_exists")]
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("pdf_filename,key\n" + "".join("%s.pdf,%s\n" % (i["key"], i["key"]) for i in ok), encoding="utf-8")
    print(json.dumps({"ok": True, "downloaded": len(ok), "not_available": len(result.get("items", [])) - len(ok), "out": a.out}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("dump")
    p.add_argument("--project", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--chars", type=int, default=700)
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("apply")
    p.add_argument("--project", required=True)
    p.add_argument("--decisions", required=True)
    p = sub.add_parser("counts")
    p.add_argument("--project", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--identified", action="append", metavar="SOURCE=N")
    p.add_argument("--dups", type=int)
    p = sub.add_parser("dois")
    p.add_argument("--project", required=True)
    p = sub.add_parser("fulltext-items")
    p.add_argument("--project", required=True)
    p.add_argument("--resolved", required=True)
    p.add_argument("--max", type=int, default=10)
    p.add_argument("--out", default="data/fulltext-items.json")
    p = sub.add_parser("manifest")
    p.add_argument("--result", required=True)
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    return {"dump": cmd_dump, "apply": cmd_apply, "counts": cmd_counts, "dois": cmd_dois,
            "fulltext-items": cmd_fulltext_items, "manifest": cmd_manifest}[a.cmd](a) or 0


if __name__ == "__main__":
    sys.exit(main())
