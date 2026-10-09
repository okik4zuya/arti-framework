"""arti-annotate CLI.

    cli.py list FILE [--status open|revised]
    cli.py strip FILE [--write]
    cli.py revise FILE ID --text "new span text"     (or --text-file PATH)
    cli.py accept FILE ID
    cli.py revert FILE ID

Mutating commands rewrite FILE in place (UTF-8, line endings preserved). `list` prints JSON.
"""
import argparse
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import annot  # noqa: E402


def _read(path):
    with io.open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def _write(path, text):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def main(argv=None):
    for st in (sys.stdout, sys.stderr):
        if hasattr(st, "reconfigure"):
            st.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="arti-annotate")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list"); s.add_argument("file"); s.add_argument("--status", choices=["open", "revised"])
    s = sub.add_parser("strip"); s.add_argument("file"); s.add_argument("--write", action="store_true")
    s = sub.add_parser("revise"); s.add_argument("file"); s.add_argument("id")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--text"); g.add_argument("--text-file")
    for name in ("accept", "revert"):
        s = sub.add_parser(name); s.add_argument("file"); s.add_argument("id")
    a = p.parse_args(argv)

    text = _read(a.file)
    try:
        if a.cmd == "list":
            items = [x for x in annot.parse(text) if not a.status or x["status"] == a.status]
            print(json.dumps(items, ensure_ascii=False, indent=2))
        elif a.cmd == "strip":
            out = annot.strip(text)
            if a.write:
                _write(a.file, out)
            else:
                sys.stdout.write(out)
        elif a.cmd == "revise":
            new = a.text if a.text is not None else _read(a.text_file)
            _write(a.file, annot.revise(text, a.id, new))
        elif a.cmd == "accept":
            _write(a.file, annot.accept(text, a.id))
        elif a.cmd == "revert":
            _write(a.file, annot.revert(text, a.id))
    except (KeyError, ValueError) as e:
        print("error: %s" % e.args[0], file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
