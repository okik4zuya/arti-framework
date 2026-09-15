"""CLI front-end for arti-jfinder. Every subcommand prints one JSON object to
stdout -- {"ok": true, "row"/"rows"/...} or {"ok": false, "error": ...} -- and
exits 0/1, matching arti-lit/arti-db conventions. Cross-project singleton (like
`tools/arti-db`) -- no `--project` flag, one shared database under
`~/.arti/tools/arti-jfinder/arti-jfinder.db`. Usage:

  "~/.arti/python/python.exe" "~/.arti/tools/arti-jfinder/cli.py" <subcommand> ...
"""
import argparse
import json
import sys

import db

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def _ok(**kwargs):
    print(json.dumps({"ok": True, **kwargs}, ensure_ascii=False))
    sys.exit(0)


def _err(message):
    print(json.dumps({"ok": False, "error": str(message)}, ensure_ascii=False))
    sys.exit(1)


def build_parser():
    p = argparse.ArgumentParser(prog="arti-jfinder")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    ig = sub.add_parser("ingest")
    ig.add_argument("--file", required=True)
    ig.add_argument("--year", required=True, type=int)

    journal = sub.add_parser("journal")
    journal_sub = journal.add_subparsers(dest="journal_cmd", required=True)

    js = journal_sub.add_parser("search")
    js.add_argument("--category")
    js.add_argument("--quartile", choices=["Q1", "Q2", "Q3", "Q4"])
    js.add_argument("--min-sjr", type=float)
    js.add_argument("--keyword")
    js.add_argument("--year", type=int)
    js.add_argument("--limit", type=int, default=20)

    jg = journal_sub.add_parser("get")
    jg.add_argument("--id", required=True, type=int, dest="sourceid")

    journal_sub.add_parser("categories").add_argument("--year", type=int)

    scope = sub.add_parser("scope")
    scope_sub = scope.add_subparsers(dest="scope_cmd", required=True)

    sg = scope_sub.add_parser("get")
    sg.add_argument("--id", required=True, type=int, dest="sourceid")

    ss = scope_sub.add_parser("set")
    ss.add_argument("--id", required=True, type=int, dest="sourceid")
    ss.add_argument("--text", required=True)
    ss.add_argument("--source-url")

    return p


def main():
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            db.init_db()
            _ok()

        db.init_db()

        if args.command == "ingest":
            result = db.ingest(args.file, args.year)
            _ok(**result)

        elif args.command == "journal":
            if args.journal_cmd == "search":
                rows = db.journal_search(
                    category=args.category, quartile=args.quartile, min_sjr=args.min_sjr,
                    keyword=args.keyword, year=args.year, limit=args.limit,
                )
                _ok(rows=rows)
            elif args.journal_cmd == "get":
                row = db.journal_get(args.sourceid)
                if row is None:
                    _err(f"no journal with sourceid {args.sourceid!r}")
                _ok(row=row)
            elif args.journal_cmd == "categories":
                _ok(categories=db.journal_categories(year=args.year))

        elif args.command == "scope":
            if args.scope_cmd == "get":
                row = db.scope_get(args.sourceid)
                _ok(row=row)
            elif args.scope_cmd == "set":
                row = db.scope_set(args.sourceid, args.text, source_url=args.source_url)
                _ok(row=row)
    except Exception as e:
        _err(e)


if __name__ == "__main__":
    main()
