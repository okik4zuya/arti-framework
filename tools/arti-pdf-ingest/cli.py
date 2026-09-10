"""CLI front-end for arti-pdf-ingest. Converts a batch of PDFs to Markdown fulltext for one
project's `literature\\fulltext\\` folder and registers each conversion in that project's
arti-lit library. Every run prints one JSON object per manifest row plus a final summary object,
same convention as arti-lit. Usage:

  "~/.arti/python/python.exe" "~/.arti/tools/arti-pdf-ingest/cli.py" ingest \\
      --project PATH --manifest PATH [--source-dir PATH] [--keep-source-pdf]

Extraction (pdfminer text layer, OCR fallback via pdf2image + pytesseract) mirrors
C:\\python_tools\\artipdf\\pdf2md.py::extract_text_to_markdown() but runs in-process against the
vendored ~/.arti/python interpreter and ~/.arti/bin/{poppler,tesseract} binaries, so this tool
depends on ~/.arti alone -- zero reference to the separate artipdf repo or its own venv/bundled
binaries. artipdf itself is left untouched either way.
"""
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys

ARTI_HOME = os.environ.get("ARTI_HOME") or os.path.expanduser("~/.arti")
if ARTI_HOME not in sys.path:
    sys.path.insert(0, ARTI_HOME)

from tools._shared.paths import poppler_bin_dir, tesseract_exe  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ARTI_LIT_CLI = os.path.join(ARTI_HOME, "tools", "arti-lit", "cli.py")


def _emit(**kwargs):
    print(json.dumps(kwargs, ensure_ascii=False))


def extract_text_to_markdown(pdf_path):
    """Return Markdown text for one PDF. Raises on failure -- caller catches per-row."""
    from pdfminer.high_level import extract_text

    text = extract_text(pdf_path)

    if not text.strip():
        from pdf2image import convert_from_path
        import pytesseract

        tess = tesseract_exe()
        if not os.path.exists(tess):
            raise RuntimeError(
                "no text layer and tesseract not found under ~/.arti/bin -- this machine needs "
                "the NSIS installer (ArtiFrameworkSetup-<ver>.exe) for OCR support"
            )
        pytesseract.pytesseract.tesseract_cmd = tess

        pages = convert_from_path(pdf_path, dpi=300, poppler_path=poppler_bin_dir())
        text = "\n".join(pytesseract.image_to_string(page) for page in pages)

    return "# Extracted PDF Content\n\n" + text


def arti_lit(project, *args):
    """Run one arti-lit subcommand, return its parsed JSON result."""
    result = subprocess.run(
        [sys.executable, ARTI_LIT_CLI, *args, "--project", project],
        capture_output=True, text=True, encoding="utf-8",
    )
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"ok": False, "error": f"arti-lit produced no parseable JSON: {result.stderr.strip()}"}


def ingest(project, manifest, source_dir, keep_source_pdf):
    summary = {"ok": 0, "skipped": 0, "error": 0}

    with open(manifest, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        pdf_filename = (row.get("pdf_filename") or "").strip()
        key = (row.get("key") or "").strip()

        if not pdf_filename or not key:
            summary["error"] += 1
            _emit(key=key, pdf=pdf_filename, status="error", detail="manifest row missing pdf_filename or key")
            continue

        pdf_path = os.path.join(source_dir, pdf_filename)
        if not os.path.exists(pdf_path):
            summary["error"] += 1
            _emit(key=key, pdf=pdf_filename, status="error", detail=f"PDF not found: {pdf_path}")
            continue

        existing = arti_lit(project, "library", "get", "--key", key)
        if not existing.get("ok"):
            summary["error"] += 1
            _emit(key=key, pdf=pdf_filename, status="error", detail=f"key not in arti-lit library: {existing.get('error')}")
            continue

        try:
            markdown = extract_text_to_markdown(pdf_path)
        except Exception as e:
            summary["error"] += 1
            _emit(key=key, pdf=pdf_filename, status="error", detail=f"extraction failed: {e}")
            continue

        fulltext_dir = os.path.join(project, "literature", "fulltext")
        os.makedirs(fulltext_dir, exist_ok=True)
        md_path = os.path.join(fulltext_dir, f"{key}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown)

        if keep_source_pdf:
            shutil.copy2(pdf_path, os.path.join(fulltext_dir, f"{key}.pdf"))

        update = arti_lit(
            project, "library", "update", "--key", key,
            "--local-file", f"literature/fulltext/{key}.md", "--status", "fulltext",
        )
        if not update.get("ok"):
            summary["error"] += 1
            _emit(key=key, pdf=pdf_filename, status="error", detail=f"arti-lit update failed: {update.get('error')}")
            continue

        summary["ok"] += 1
        _emit(key=key, pdf=pdf_filename, status="ok", detail=f"literature/fulltext/{key}.md")

    _emit(summary=summary)


def build_parser():
    p = argparse.ArgumentParser(prog="arti-pdf-ingest")
    sub = p.add_subparsers(dest="command", required=True)

    ing = sub.add_parser("ingest")
    ing.add_argument("--project", required=True)
    ing.add_argument("--manifest", required=True)
    ing.add_argument("--source-dir")
    ing.add_argument("--keep-source-pdf", action="store_true")

    return p


def main():
    args = build_parser().parse_args()
    if args.command == "ingest":
        source_dir = args.source_dir or os.path.dirname(os.path.abspath(args.manifest))
        ingest(args.project, args.manifest, source_dir, args.keep_source_pdf)


if __name__ == "__main__":
    main()
