"""CLI front-end for arti-lit. Every subcommand prints one JSON object to
stdout -- {"ok": true, "row"/"rows"/...} or {"ok": false, "error": ...} --
and exits 0/1, so a Claude session parses Bash output instead of hand-rolled
table scraping. Per-project, not a cross-project singleton: every subcommand
takes --project PATH (default cwd). Usage:

  "~/.arti/python/python.exe" "~/.arti/tools/arti-lit/cli.py" <subcommand> ... [--project PATH]
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
    p = argparse.ArgumentParser(prog="arti-lit")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("init")
    pi.add_argument("--project")

    lib = sub.add_parser("library")
    libsub = lib.add_subparsers(dest="library_cmd", required=True)

    la = libsub.add_parser("add")
    la.add_argument("--key", required=True)
    la.add_argument("--citation", required=True)
    la.add_argument("--doi")
    la.add_argument("--local-file")
    la.add_argument("--status", choices=db.READ_STATUSES, default="export-only")
    la.add_argument("--used-in")
    la.add_argument("--project")

    lu = libsub.add_parser("update")
    lu.add_argument("--key", required=True)
    lu.add_argument("--citation")
    lu.add_argument("--doi")
    lu.add_argument("--local-file")
    lu.add_argument("--status", choices=db.READ_STATUSES)
    lu.add_argument("--used-in")
    lu.add_argument("--project")

    lg = libsub.add_parser("get")
    lg.add_argument("--key", required=True)
    lg.add_argument("--project")

    ll = libsub.add_parser("list")
    ll.add_argument("--status", choices=db.READ_STATUSES)
    ll.add_argument("--project")

    ls = libsub.add_parser("search")
    ls.add_argument("keywords", nargs="+")
    ls.add_argument("--project")

    lr = libsub.add_parser("remove")
    lr.add_argument("--key", required=True)
    lr.add_argument("--project")

    le = libsub.add_parser("export")
    le.add_argument("--project")

    refs = sub.add_parser("refs")
    refssub = refs.add_subparsers(dest="refs_cmd", required=True)

    rg = refssub.add_parser("generate")
    rg.add_argument("--keys", required=True, help="comma-separated keys")
    rg.add_argument("--order", choices=["alpha", "appearance"], default="alpha")
    rg.add_argument("--output")
    rg.add_argument("--project")

    return p


def main():
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            db.init_db(project=args.project)
            _ok()

        db.init_db(project=args.project)

        if args.command == "library":
            if args.library_cmd == "add":
                row = db.library_add(
                    args.project, key=args.key, citation=args.citation, doi=args.doi,
                    local_file=args.local_file, read_status=args.status, used_in=args.used_in,
                )
                _ok(row=row)
            elif args.library_cmd == "update":
                row = db.library_update(
                    args.project, key=args.key, citation=args.citation, doi=args.doi,
                    local_file=args.local_file, read_status=args.status, used_in=args.used_in,
                )
                _ok(row=row)
            elif args.library_cmd == "get":
                row = db.library_get(args.project, args.key)
                if row is None:
                    _err(f"no source with key {args.key!r}")
                _ok(row=row)
            elif args.library_cmd == "list":
                _ok(rows=db.library_list(args.project, status=args.status))
            elif args.library_cmd == "search":
                _ok(rows=db.library_search(args.project, args.keywords))
            elif args.library_cmd == "remove":
                row = db.library_remove(args.project, args.key)
                if row is None:
                    _err(f"no source with key {args.key!r}")
                _ok(row=row)
            elif args.library_cmd == "export":
                db.library_export(args.project)
                _ok()

        elif args.command == "refs":
            if args.refs_cmd == "generate":
                keys = [k.strip() for k in args.keys.split(",") if k.strip()]
                result = db.refs_generate(
                    args.project, keys, order=args.order, output=args.output,
                )
                _ok(**result)
    except Exception as e:
        _err(e)


if __name__ == "__main__":
    main()
