"""CLI front-end for citation-chase. Cross-project singleton (no --project flag) that answers a
bounded question for two named sets of DOIs: does any paper in Set A cite, or get cited by, any
paper in Set B? Built for SLR novelty-claim checks (see HANDOFF.md) but generic to any two DOI
lists.

Primary source: OpenAlex (free, keyless). Fallback: Semantic Scholar, only for a DOI OpenAlex
can't resolve. Never Scopus (entitlement unconfirmed) or Google Scholar (no API, not built --
see HANDOFF.md Path D).

Prints one JSON object per Set-A DOI to stdout as it resolves, plus a final summary object --
same convention as arti-pdf-ingest. Resumable: --out is also the run's state file; a DOI already
recorded with status "ok" is not re-queried on a re-run.

Usage:

  "~/.arti/python/python.exe" "~/.arti/tools/citation-chase/cli.py" run \\
      --set-a DOI1,DOI2,... --set-b DOI3,DOI4,... --out PATH.jsonl [--mailto EMAIL]

  # or read DOI lists from files (one DOI per line):
  ... run --set-a-file a.txt --set-b-file b.txt --out PATH.jsonl
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OPENALEX_BASE = "https://api.openalex.org"
S2_BASE = "https://api.semanticscholar.org/graph/v1"
MAX_RETRIES = 5
USER_AGENT = "citation-chase/0.1 (~/.arti/tools/citation-chase)"

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def _emit(obj):
    print(json.dumps(obj, ensure_ascii=False))
    sys.stdout.flush()


def normalize_doi(doi):
    doi = (doi or "").strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def parse_doi_list(raw, file_path):
    dois = []
    if raw:
        dois.extend(re.split(r"[,\n]+", raw))
    if file_path:
        with open(file_path, encoding="utf-8") as f:
            dois.extend(f.readlines())
    return [normalize_doi(d) for d in dois if normalize_doi(d)]


def http_get_json(url, headers=None):
    """GET url, return parsed JSON. Raises HTTPNotFound / RuntimeError on failure."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code == 429 or 500 <= e.code < 600:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(f"HTTP {e.code} after {MAX_RETRIES} retries: {url}")
                time.sleep(delay)
                delay *= 2
                continue
            raise RuntimeError(f"HTTP {e.code}: {url}")
        except urllib.error.URLError as e:
            if attempt == MAX_RETRIES - 1:
                raise RuntimeError(f"network error after {MAX_RETRIES} retries: {e}")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"exhausted retries: {url}")


def fetch_openalex_work(doi, mailto=None):
    url = f"{OPENALEX_BASE}/works/https://doi.org/{doi}"
    if mailto:
        url += f"?mailto={urllib.parse.quote(mailto)}"
    return http_get_json(url)


def fetch_openalex_cited_by(work_id, set_b_doi_set, mailto=None):
    """Paginate works citing work_id, return the subset of their DOIs that are in Set B."""
    hits = []
    cursor = "*"
    while cursor:
        url = f"{OPENALEX_BASE}/works?filter=cites:{work_id}&per-page=200&cursor={cursor}"
        if mailto:
            url += f"&mailto={mailto}"
        page = http_get_json(url)
        if page is None:
            break
        for r in page.get("results", []):
            rdoi = normalize_doi(r.get("doi"))
            if rdoi in set_b_doi_set:
                hits.append(rdoi)
        cursor = (page.get("meta") or {}).get("next_cursor")
        if not page.get("results"):
            break
    return hits


def fetch_semanticscholar(doi):
    url = f"{S2_BASE}/paper/DOI:{doi}?fields=references.externalIds,citations.externalIds"
    return http_get_json(url)


def resolve_via_openalex(doi_a, set_b_openalex_index, set_b_doi_set, mailto=None):
    work = fetch_openalex_work(doi_a, mailto=mailto)
    if work is None:
        return None
    referenced_ids = set(work.get("referenced_works") or [])
    cites = sorted({set_b_openalex_index[rid] for rid in referenced_ids if rid in set_b_openalex_index})
    cited_by = sorted(set(fetch_openalex_cited_by(work["id"], set_b_doi_set, mailto=mailto)))
    return {
        "cites_from_set_b": cites,
        "cited_by_from_set_b": cited_by,
        "source": "openalex",
        "status": "ok",
    }


def resolve_via_semanticscholar(doi_a, set_b_doi_set):
    data = fetch_semanticscholar(doi_a)
    if data is None:
        return None
    cites, cited_by = set(), set()
    for ref in data.get("references") or []:
        rdoi = normalize_doi((ref.get("externalIds") or {}).get("DOI"))
        if rdoi in set_b_doi_set:
            cites.add(rdoi)
    for cit in data.get("citations") or []:
        cdoi = normalize_doi((cit.get("externalIds") or {}).get("DOI"))
        if cdoi in set_b_doi_set:
            cited_by.add(cdoi)
    return {
        "cites_from_set_b": sorted(cites),
        "cited_by_from_set_b": sorted(cited_by),
        "source": "semanticscholar",
        "status": "ok",
    }


def build_set_b_openalex_index(set_b_dois, mailto=None):
    """Map OpenAlex work id -> Set-B DOI, for the Set-B DOIs OpenAlex can resolve.

    Resolving Set B once (N lookups) instead of resolving every Set-A paper's full reference
    list (which can run 30-60 entries each) is the same backward-citation answer at a fraction
    of the API calls -- forward citations are unaffected since OpenAlex's cited-by results
    already carry their own DOI, no extra resolution needed.
    """
    index = {}
    unresolved = []
    for doi in set_b_dois:
        work = fetch_openalex_work(doi, mailto=mailto)
        if work is None:
            unresolved.append(doi)
            continue
        index[work["id"]] = doi
    return index, unresolved


def load_existing(out_path):
    rows = {}
    if not os.path.exists(out_path):
        return rows
    with open(out_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if "doi" in obj:
                rows[obj["doi"]] = obj
    return rows


def write_all(out_path, rows_in_order, summary):
    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows_in_order:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.write(json.dumps({"summary": summary}, ensure_ascii=False) + "\n")


def write_overlap_report(report_path, rows_in_order, set_a_dois, set_b_dois):
    overlaps = [r for r in rows_in_order if r.get("cites_from_set_b") or r.get("cited_by_from_set_b")]
    lines = [
        "# Citation-chase overlap report",
        "",
        f"Set A: {len(set_a_dois)} DOIs. Set B: {len(set_b_dois)} DOIs.",
        "",
    ]
    if not overlaps:
        lines.append("No overlaps found: no Set-A paper cites or is cited by any Set-B paper.")
    else:
        lines.append("| Set A DOI | Cites (Set B) | Cited by (Set B) | Source |")
        lines.append("|---|---|---|---|")
        for r in overlaps:
            lines.append(
                f"| {r['doi']} | {', '.join(r.get('cites_from_set_b') or []) or '-'} "
                f"| {', '.join(r.get('cited_by_from_set_b') or []) or '-'} | {r.get('source') or '-'} |"
            )
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(set_a_dois, set_b_dois, out_path, mailto=None, report=True):
    existing = load_existing(out_path)
    set_b_doi_set = set(set_b_dois)

    set_b_index, unresolved_b = build_set_b_openalex_index(set_b_dois, mailto=mailto)
    if unresolved_b:
        _emit({
            "note": "some Set-B DOIs not found in OpenAlex; backward-citation checks against "
                    "them rely only on forward cited-by results carrying their own DOI",
            "unresolved_set_b": unresolved_b,
        })

    rows = []
    summary = {"ok": 0, "partial": 0, "error": 0, "not_found": 0, "overlaps_found": 0}

    for doi in set_a_dois:
        if doi in existing and existing[doi].get("status") == "ok":
            row = existing[doi]
            rows.append(row)
            _emit(row)
            summary["ok"] += 1
            if row.get("cites_from_set_b") or row.get("cited_by_from_set_b"):
                summary["overlaps_found"] += 1
            continue

        row = {"doi": doi}
        try:
            result = resolve_via_openalex(doi, set_b_index, set_b_doi_set, mailto=mailto)
            if result is None:
                result = resolve_via_semanticscholar(doi, set_b_doi_set)
            if result is None:
                row.update({"cites_from_set_b": [], "cited_by_from_set_b": [], "source": None,
                             "status": "not_found"})
                summary["not_found"] += 1
            else:
                row.update(result)
                summary["ok"] += 1
                if row.get("cites_from_set_b") or row.get("cited_by_from_set_b"):
                    summary["overlaps_found"] += 1
        except Exception as e:
            row.update({"cites_from_set_b": [], "cited_by_from_set_b": [], "source": None,
                         "status": "error", "detail": str(e)})
            summary["error"] += 1

        rows.append(row)
        _emit(row)
        write_all(out_path, rows, summary)

    write_all(out_path, rows, summary)
    if report:
        report_path = os.path.join(os.path.dirname(os.path.abspath(out_path)), "overlap-report.md")
        write_overlap_report(report_path, rows, set_a_dois, set_b_dois)

    _emit({"summary": summary})


def build_parser():
    p = argparse.ArgumentParser(prog="citation-chase")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("run", help="check whether Set A cites/is cited by Set B")
    r.add_argument("--set-a", help="comma- or newline-separated DOIs")
    r.add_argument("--set-a-file", help="path to a file with one DOI per line")
    r.add_argument("--set-b", help="comma- or newline-separated DOIs")
    r.add_argument("--set-b-file", help="path to a file with one DOI per line")
    r.add_argument("--out", required=True, help="JSONL output/state file (also the resume file)")
    r.add_argument("--mailto", help="email for OpenAlex's polite pool (optional, speeds up API)")
    r.add_argument("--no-report", action="store_true", help="skip writing overlap-report.md")

    return p


def main():
    args = build_parser().parse_args()
    if args.command == "run":
        set_a = parse_doi_list(args.set_a, args.set_a_file)
        set_b = parse_doi_list(args.set_b, args.set_b_file)
        if not set_a or not set_b:
            _emit({"summary": {"error": "both --set-a and --set-b must resolve to at least one DOI"}})
            sys.exit(1)
        run(set_a, set_b, args.out, mailto=args.mailto, report=not args.no_report)


if __name__ == "__main__":
    main()
