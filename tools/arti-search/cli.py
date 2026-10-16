#!/usr/bin/env python3
"""arti-search CLI: live literature discovery without any MCP registration.

    "~/.arti/python/python.exe" "~/.arti/tools/arti-search/cli.py" <subcommand> [options]

Subcommands: search, count, related, get, lookup, fulltext, s2-search, s2-recommend, s2-get, trace,
resolve, scholar, sources. Every call prints one JSON object (the result, or a summary when --out is
given) and exits 0, or prints the {"error", "error_type", "hint"?} envelope and exits 1. Parameters,
costs and limits: README.md.

Shared options:
  --query TEXT | --query-file PATH   the query (PATH '-' reads stdin; use a file for Boolean queries with
                                     quotes, which Windows shells mangle)
  --out PATH        write the full result to PATH and print only a summary (keeps big results out of the
                    conversation); without it stdout is bounded by --max-chars (default 24000)
  --ris PATH        (search, s2-search, scholar, trace, related) also write the records as RIS, ready for
                    `arti-lit library import-ris`
  --snapshot PATH   also write the raw JSON result (a dated record of what the search returned)
  --no-keys         ignore OPENALEX_API_KEY / SEMANTIC_SCHOLAR_API_KEY from env and mcp-keys.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import api  # noqa: E402
import config  # noqa: E402
from sources.openalex import ENTITY_KINDS, GROUP_BY, SORTS  # noqa: E402

DEFAULT_MAX_CHARS = 24000
RIS_TYPES = {"book": "BOOK", "book-chapter": "CHAP", "conference-paper": "CONF", "dissertation": "THES",
             "report": "RPRT", "dataset": "DATA", "preprint": "JOUR", "article": "JOUR", "review": "JOUR"}


# ---- input helpers -------------------------------------------------------------------------

def read_query(args, required=True):
    if getattr(args, "query_file", None):
        text = sys.stdin.read() if args.query_file == "-" else open(args.query_file, encoding="utf-8").read()
        text = " ".join(text.split())
    else:
        text = getattr(args, "query", None)
    if not text and required:
        raise ValueError("a query is required: pass --query TEXT or --query-file PATH")
    return text or ""


def split_list(value):
    if not value:
        return None
    out = []
    for v in value:
        out.extend(x.strip() for x in str(v).split(",") if x.strip())
    return out or None


def tri(value):
    return None if value is None else value == "true"


def work_type(value):
    items = split_list(value)
    if not items:
        return None
    return items[0] if len(items) == 1 else items


# ---- output --------------------------------------------------------------------------------

def to_ris(results):
    lines = []
    for r in results:
        extra = r.get("extra") or {}
        lines.append("TY  - " + RIS_TYPES.get(str(extra.get("type", "")).lower(), "JOUR"))
        for a in r.get("authors") or []:
            lines.append("AU  - " + str(a))
        lines.append("TI  - " + " ".join(str(r.get("title") or "Untitled").split()))
        year = extra.get("year") or (r.get("published_date") or "")[:4]
        if year:
            lines.append("PY  - " + str(year))
        venue = extra.get("venue") or ""
        if venue:
            lines.append("T2  - " + str(venue))
        if r.get("doi"):
            lines.append("DO  - " + str(r["doi"]))
        if r.get("abstract"):
            lines.append("AB  - " + " ".join(str(r["abstract"]).split()))
        if r.get("url"):
            lines.append("UR  - " + str(r["url"]))
        lines.append("N1  - arti-search %s %s" % (r.get("source", ""), r.get("paper_id", "")))
        lines.append("ER  - ")
        lines.append("")
    return "\n".join(lines)


def write_text(path, text):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def emit(result, args):
    """Print the result (or a summary) and return the exit code."""
    if isinstance(result, dict) and "error" in result:
        print(json.dumps(result, ensure_ascii=False))
        return 1
    records = result.get("results") if isinstance(result, dict) else None
    extras = {}
    if args.snapshot:
        write_text(args.snapshot, json.dumps(result, ensure_ascii=False, indent=2))
        extras["snapshot"] = args.snapshot
    if args.ris:
        if records is None:
            raise ValueError("--ris needs a subcommand that returns records")
        write_text(args.ris, to_ris(records))
        extras["ris"] = {"path": args.ris, "records": len(records)}
    if args.out:
        text = json.dumps(result, ensure_ascii=False, indent=2)
        write_text(args.out, text)
        summary = {"ok": True, "out": args.out, "bytes": len(text.encode("utf-8"))}
        if isinstance(result, dict):
            if "meta" in result:
                summary["meta"] = result["meta"]
            if records is not None:
                summary["returned"] = len(records)
            for k in ("total", "summary"):
                if k in result:
                    summary[k] = result[k]
            if "groups" in result:  # a grouped count can have hundreds of buckets: the file has them all
                summary["groups"] = result["groups"][:10]
                summary["groups_in_file"] = len(result["groups"])
        summary.update(extras)
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    payload = result
    if isinstance(result, dict) and extras:
        payload = dict(result, **{"written": extras})
    text = json.dumps(payload, ensure_ascii=False)
    limit = args.max_chars
    if limit and len(text) > limit and records is not None:
        slim = dict(payload)
        slim["results"] = [{k: v for k, v in r.items() if k != "abstract"} for r in records]
        slim["truncated"] = "abstracts dropped to fit --max-chars; use --out PATH for the full result"
        text = json.dumps(slim, ensure_ascii=False)
        while len(text) > limit and slim["results"]:
            slim["results"] = slim["results"][: max(1, len(slim["results"]) // 2)]
            slim["truncated"] = "abstracts dropped and results cut to fit --max-chars; use --out PATH"
            text = json.dumps(slim, ensure_ascii=False)
            if len(slim["results"]) == 1:
                break
    elif limit and len(text) > limit:
        text = json.dumps({"ok": False, "truncated": True, "bytes": len(text.encode("utf-8")),
                           "hint": "result is larger than --max-chars; rerun with --out PATH"})
    print(text)
    return 0


# ---- argument groups -----------------------------------------------------------------------

def add_query(p, required=False):
    p.add_argument("--query", help="query text")
    p.add_argument("--query-file", metavar="PATH", help="read the query from PATH ('-' for stdin)")


def add_filters(p):
    p.add_argument("--search-in", default="title_abstract",
                   help="title_abstract (default) | all | title | abstract | exact | semantic")
    p.add_argument("--work-type", action="append", help="e.g. review, or article,preprint (comma list)")
    p.add_argument("--include-retracted", action="store_true", help="keep retracted works (default: dropped)")
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--oa-only", action="store_true", help="only works with an open-access version")
    p.add_argument("--language", help="ISO 639-1, e.g. en")
    p.add_argument("--min-citations", type=int)
    p.add_argument("--has-abstract", choices=("true", "false"))
    p.add_argument("--has-content-pdf", action="store_true", help="only works whose PDF OpenAlex caches")
    p.add_argument("--topic-id")
    p.add_argument("--source-issn")
    p.add_argument("--cites", help="works citing this work (W-id or DOI)")
    p.add_argument("--cited-by", help="works cited by this work (W-id or DOI)")
    p.add_argument("--related-to", help="works OpenAlex lists as related to this work")
    p.add_argument("--filters", help="raw OpenAlex filter string appended as-is")


def filter_kwargs(a):
    return dict(
        search_in=a.search_in, work_type=work_type(a.work_type), exclude_retracted=not a.include_retracted,
        year_from=a.year_from, year_to=a.year_to, open_access_only=a.oa_only, language=a.language,
        min_citations=a.min_citations, has_abstract=tri(a.has_abstract), has_content_pdf=a.has_content_pdf,
        topic_id=a.topic_id, source_issn=a.source_issn, cites=a.cites, cited_by=a.cited_by,
        related_to=a.related_to, filters=a.filters)


def build_parser():
    ap = argparse.ArgumentParser(prog="arti-search", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def command(name, help_text, records=True):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--out", metavar="PATH")
        p.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
        p.add_argument("--no-keys", action="store_true")
        p.add_argument("--snapshot", metavar="PATH")
        p.add_argument("--ris", metavar="PATH") if records else p.set_defaults(ris=None)
        return p

    p = command("search", "OpenAlex works search")
    add_query(p)
    add_filters(p)
    p.add_argument("--max", type=int, default=10, dest="max_results")
    p.add_argument("--sort", default="relevance", choices=sorted(SORTS))
    p.add_argument("--cursor")
    p.add_argument("--no-abstracts", action="store_true")
    p.add_argument("--abstract-max-chars", type=int)

    p = command("count", "count OpenAlex works, optionally grouped", records=False)
    add_query(p)
    add_filters(p)
    p.add_argument("--group-by", choices=sorted(GROUP_BY))

    p = command("related", "OpenAlex related works for one seed")
    p.add_argument("id", help="OpenAlex W-id or DOI")
    p.add_argument("--max", type=int, default=10, dest="max_results")
    p.add_argument("--sort", default="citations", choices=sorted(SORTS))
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--work-type", action="append")
    p.add_argument("--abstract-max-chars", type=int)

    p = command("get", "one OpenAlex work", records=False)
    p.add_argument("id")

    p = command("lookup", "autocomplete a name to OpenAlex IDs", records=False)
    p.add_argument("kind", choices=sorted(ENTITY_KINDS))
    p.add_argument("name")
    p.add_argument("--limit", type=int, default=10)

    p = command("fulltext", "download open-access PDFs into <project>/literature/fulltext/", records=False)
    p.add_argument("--project", required=True, help="paper project root")
    p.add_argument("--items-file", metavar="PATH", help="JSON list of {id_or_doi, key}")
    p.add_argument("--item", action="append", metavar="DOI=KEY", help="one item, repeatable")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--max-files", type=int, default=20)
    p.add_argument("--source", default="auto", choices=("auto", "openalex_content", "oa_location"))

    p = command("s2-search", "Semantic Scholar search")
    add_query(p)
    p.add_argument("--max", type=int, default=10, dest="max_results")
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--min-citations", type=int)
    p.add_argument("--oa-only", action="store_true")
    p.add_argument("--publication-types")
    p.add_argument("--fields-of-study")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--abstract-max-chars", type=int)

    p = command("s2-recommend", "Semantic Scholar recommendations from seeds")
    p.add_argument("--positive", action="append", required=True, help="DOI, W-id or S2 id (comma list ok)")
    p.add_argument("--negative", action="append")
    p.add_argument("--max", type=int, default=20, dest="max_results")
    p.add_argument("--year-from", type=int)
    p.add_argument("--min-citations", type=int)
    p.add_argument("--pool", default="recent", choices=("recent", "all-cs"))
    p.add_argument("--abstract-max-chars", type=int)

    p = command("s2-get", "one Semantic Scholar paper", records=False)
    p.add_argument("id")

    p = command("trace", "citation tracing from 1-5 seeds")
    p.add_argument("--seeds", action="append", required=True, help="W-ids or DOIs (comma list ok, max 5)")
    p.add_argument("--direction", default="forward", choices=("forward", "backward", "both"))
    add_query(p)
    p.add_argument("--max", type=int, default=20, dest="max_results")
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--min-citations", type=int)
    p.add_argument("--abstract-max-chars", type=int)

    p = command("resolve", "match DOIs or titles to OpenAlex records", records=False)
    p.add_argument("--items", action="append", help="DOIs, DOI URLs or titles (comma list ok for DOIs)")
    p.add_argument("--items-file", metavar="PATH", help="one item per line")
    p.add_argument("--project", help="paper project root (flags in_library, read-only)")

    p = command("scholar", "Google Scholar search (scraping route; persisted cooldown)")
    add_query(p)
    p.add_argument("--max", type=int, default=10, dest="max_results")
    p.add_argument("--year-from", type=int)
    p.add_argument("--year-to", type=int)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--no-resolve", action="store_true")

    command("sources", "which search routes are live", records=False)
    return ap


# ---- dispatch ------------------------------------------------------------------------------

def run(args):
    c = args.cmd
    if c == "search":
        q = read_query(args, required=False)
        if not q and not (args.cites or args.cited_by or args.related_to or args.filters or args.topic_id
                          or args.source_issn):
            raise ValueError("nothing to search: pass --query/--query-file, or --cites, --cited-by, "
                             "--related-to, --topic-id, --source-issn or --filters")
        return api.safe(api.search_openalex_works, query=q,
                        max_results=args.max_results, sort=args.sort, cursor=args.cursor,
                        include_abstract=not args.no_abstracts, abstract_max_chars=args.abstract_max_chars,
                        **filter_kwargs(args))
    if c == "count":
        return api.safe(api.count_openalex_works, query=read_query(args, required=False) or None,
                        group_by=args.group_by, **filter_kwargs(args))
    if c == "related":
        return api.safe(api.related_openalex_works, id_or_doi=args.id, max_results=args.max_results,
                        sort=args.sort, year_from=args.year_from, year_to=args.year_to,
                        work_type=work_type(args.work_type), abstract_max_chars=args.abstract_max_chars)
    if c == "get":
        return api.safe(api.get_openalex_work, id_or_doi=args.id)
    if c == "lookup":
        return api.safe(api.lookup_openalex_entity, kind=args.kind, name=args.name, limit=args.limit)
    if c == "fulltext":
        items = []
        if args.items_file:
            with open(args.items_file, encoding="utf-8") as f:
                items.extend(json.load(f))
        for entry in args.item or []:
            doi, _, key = entry.rpartition("=")
            if not doi or not key:
                raise ValueError("--item must look like DOI=KEY, got %r" % entry)
            items.append({"id_or_doi": doi, "key": key})
        if not items:
            raise ValueError("no items: use --items-file PATH or --item DOI=KEY")
        return api.safe(api.download_openalex_fulltext, items=items, project_path=args.project,
                        dry_run=args.dry_run, max_files=args.max_files, source=args.source)
    if c == "s2-search":
        return api.safe(api.search_semanticscholar_papers, query=read_query(args), max_results=args.max_results,
                        year_from=args.year_from, year_to=args.year_to, min_citations=args.min_citations,
                        open_access_only=args.oa_only, publication_types=args.publication_types,
                        fields_of_study=args.fields_of_study, offset=args.offset,
                        abstract_max_chars=args.abstract_max_chars)
    if c == "s2-recommend":
        return api.safe(api.recommend_semanticscholar_papers, positive=split_list(args.positive),
                        negative=split_list(args.negative), max_results=args.max_results,
                        abstract_max_chars=args.abstract_max_chars, year_from=args.year_from,
                        min_citations=args.min_citations, pool=args.pool)
    if c == "s2-get":
        return api.safe(api.get_semanticscholar_paper, id_or_doi=args.id)
    if c == "trace":
        return api.safe(api.trace_openalex_citations, seeds=split_list(args.seeds), direction=args.direction,
                        query=read_query(args, required=False) or None, max_results=args.max_results,
                        year_from=args.year_from, year_to=args.year_to, min_citations=args.min_citations,
                        abstract_max_chars=args.abstract_max_chars)
    if c == "resolve":
        items = []
        if args.items_file:
            with open(args.items_file, encoding="utf-8") as f:
                items.extend(line.strip() for line in f if line.strip())
        for v in args.items or []:
            # a title may contain commas: split a value on commas only when every part looks like a DOI/URL
            parts = [x.strip() for x in v.split(",") if x.strip()]
            if len(parts) > 1 and all(x.lower().startswith(("10.", "http", "doi:")) for x in parts):
                items.extend(parts)
            else:
                items.append(v.strip())
        if not items:
            raise ValueError("no items: use --items TEXT or --items-file PATH")
        return api.safe(api.resolve_external_candidates, items=items, project_path=args.project)
    if c == "scholar":
        return api.safe(api.search_googlescholar_papers, query=read_query(args), max_results=args.max_results,
                        year_from=args.year_from, year_to=args.year_to, start=args.start,
                        resolve=not args.no_resolve)
    if c == "sources":
        return api.safe(api.check_search_sources)
    raise ValueError("unknown subcommand %r" % c)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    if args.no_keys:
        config.ignore_keys()
    try:
        return emit(run(args), args)
    except (ValueError, OSError) as e:
        print(json.dumps({"error": str(e), "error_type": type(e).__name__}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
