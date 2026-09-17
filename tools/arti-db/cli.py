"""CLI front-end for arti-db. Every subcommand prints one JSON object to
stdout -- {"ok": true, "row"/"rows": ...} or {"ok": false, "error": ...} --
and exits 0/1, so a Claude session parses Bash output instead of hand-rolled
table scraping. Usage:

  "~/.arti/python/python.exe" "~/.arti/tools/arti-db/cli.py" <subcommand> ...
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


def _split_csv_ints(s):
    return [int(x) for x in s.split(",") if x.strip()]


def build_parser():
    p = argparse.ArgumentParser(prog="arti-db")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    pu = sub.add_parser("project")
    psub = pu.add_subparsers(dest="project_cmd", required=True)

    pup = psub.add_parser("upsert")
    pup.add_argument("--project-path", required=True)
    pup.add_argument("--topic", required=True)
    pup.add_argument("--stage")
    pup.add_argument("--target-journal")
    pup.add_argument("--status")
    pup.add_argument("--summary")
    pup.add_argument("--updated")

    plist = psub.add_parser("list")
    plist.add_argument("--stage")
    plist.add_argument("--status")

    pget = psub.add_parser("get")
    pget.add_argument("--project-path", required=True)

    psub.add_parser("export")

    ib = sub.add_parser("idea-bank")
    ibsub = ib.add_subparsers(dest="idea_bank_cmd", required=True)

    iba = ibsub.add_parser("add")
    iba.add_argument("--label", required=True)
    iba.add_argument("--idea-text", required=True)
    iba.add_argument("--c", type=int)
    iba.add_argument("--m", type=int)
    iba.add_argument("--e", type=int)
    iba.add_argument("--novelty-label")
    iba.add_argument("--date-parked")
    iba.add_argument("--source-project")
    iba.add_argument("--reason")
    iba.add_argument("--notes")
    iba.add_argument("--tag")

    ibs = ibsub.add_parser("search")
    ibs.add_argument("keywords", nargs="+")

    ibl = ibsub.add_parser("list")
    ibl.add_argument("--source-project")

    ibr = ibsub.add_parser("remove")
    ibr.add_argument("--id", type=int, required=True)

    ibsub.add_parser("export")

    ii = sub.add_parser("idea-index")
    iisub = ii.add_subparsers(dest="idea_index_cmd", required=True)

    iiu = iisub.add_parser("upsert")
    iiu.add_argument("--project", required=True)
    iiu.add_argument("--file", required=True)
    iiu.add_argument("--tipe", choices=["Ide", "Narasi"], default="Ide")
    iiu.add_argument("--status")
    iiu.add_argument("--hook")
    iiu.add_argument("--used-in")
    iiu.add_argument("--date-added")

    iil = iisub.add_parser("list")
    iil.add_argument("--project")
    iil.add_argument("--status")
    iil.add_argument("--include-archived", action="store_true")

    iia = iisub.add_parser("archive")
    iia.add_argument("--ids", required=True, help="comma-separated row ids")
    iia.add_argument("--summary", required=True)

    iilog = iisub.add_parser("log")
    iilog.add_argument("--note", required=True)

    iisub.add_parser("export")

    return p


def main():
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            db.init_db()
            _ok()

        db.init_db()

        if args.command == "project":
            if args.project_cmd == "upsert":
                row = db.project_upsert(
                    project_path=args.project_path, topic=args.topic, stage=args.stage,
                    target_journal=args.target_journal, status=args.status, summary=args.summary,
                    updated=args.updated,
                )
                _ok(row=row)
            elif args.project_cmd == "list":
                _ok(rows=db.project_list(stage=args.stage, status=args.status))
            elif args.project_cmd == "get":
                row = db.project_get(args.project_path)
                if row is None:
                    _err(f"no project_index row for project-path {args.project_path!r}")
                _ok(row=row)
            elif args.project_cmd == "export":
                db.project_export()
                _ok()

        elif args.command == "idea-bank":
            if args.idea_bank_cmd == "add":
                row = db.idea_bank_add(
                    label=args.label, idea_text=args.idea_text, c=args.c, m=args.m, e=args.e,
                    novelty_label=args.novelty_label, date_parked=args.date_parked,
                    source_project=args.source_project, reason_parked=args.reason, notes=args.notes,
                    tag=args.tag,
                )
                _ok(row=row)
            elif args.idea_bank_cmd == "search":
                _ok(rows=db.idea_bank_search(args.keywords))
            elif args.idea_bank_cmd == "list":
                _ok(rows=db.idea_bank_list(source_project=args.source_project))
            elif args.idea_bank_cmd == "remove":
                row = db.idea_bank_remove(args.id)
                if row is None:
                    _err(f"no idea_bank row with id {args.id}")
                _ok(row=row)
            elif args.idea_bank_cmd == "export":
                db.idea_bank_export()
                _ok()

        elif args.command == "idea-index":
            if args.idea_index_cmd == "upsert":
                row = db.idea_index_upsert(
                    project=args.project, file=args.file, tipe=args.tipe, status=args.status,
                    hook=args.hook, used_in=args.used_in, date_added=args.date_added,
                )
                _ok(row=row)
            elif args.idea_index_cmd == "list":
                _ok(rows=db.idea_index_list(
                    project=args.project, status=args.status, include_archived=args.include_archived,
                ))
            elif args.idea_index_cmd == "archive":
                ids = _split_csv_ints(args.ids)
                rows = db.idea_index_archive(ids, args.summary)
                _ok(rows=rows)
            elif args.idea_index_cmd == "log":
                row = db.idea_index_log(args.note)
                _ok(row=row)
            elif args.idea_index_cmd == "export":
                db.idea_index_export()
                _ok()
    except Exception as e:
        _err(e)


if __name__ == "__main__":
    main()
