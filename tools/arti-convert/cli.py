"""arti-convert: document conversion in one place.

    cli.py pdf    --md SRC.md [--out-dir DIR]                     Markdown -> print-styled A4 PDF (Edge/Chrome)
    cli.py ingest --project PATH --manifest PATH [--source-dir PATH] [--keep-source-pdf]
                                                                  PDFs -> fulltext Markdown, registered in arti-lit

Each subcommand keeps the arguments of the tool it replaced (arti-pdf render.py, arti-pdf-ingest cli.py, both retired).
Markdown -> .docx stays in tools/arti-docx.
"""
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMMANDS = {"pdf": "md2pdf", "ingest": "ingest"}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(0 if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help") else 2)
    sys.path.insert(0, HERE)
    importlib.import_module(COMMANDS[sys.argv[1]]).main(sys.argv[2:])


if __name__ == "__main__":
    main()
