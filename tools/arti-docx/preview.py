#!/usr/bin/env python3
"""
arti-docx preview - render a .docx to PDF and PNG pages so its layout can be looked at.

    python preview.py manuscript.docx [--out-dir DIR] [--dpi 70]

Developer aid, not part of the manuscript pipeline: it needs LibreOffice (`soffice`), which ARTi does not ship.
When LibreOffice is not installed it prints a notice and exits 0, so callers can run it unconditionally.
LibreOffice is only a rough stand-in for Word (small differences in column widths, spacing and fonts are
normal); it never touches the .docx itself. Zotero fields are not evaluated.

Writes <out-dir>/<name>.pdf and <out-dir>/<name>-<page>.png (default out-dir: next to the .docx, in "preview/").
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile

ARTI_HOME = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def find_soffice():
    found = shutil.which("soffice")
    if found:
        return found
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            cand = os.path.join(base, "LibreOffice", "program", "soffice.exe")
            if os.path.isfile(cand):
                return cand
    for cand in ("/Applications/LibreOffice.app/Contents/MacOS/soffice", "/usr/bin/soffice"):
        if os.path.isfile(cand):
            return cand
    return None


def find_pdftoppm():
    found = shutil.which("pdftoppm")
    if found:
        return found
    hits = glob.glob(os.path.join(ARTI_HOME, "bin", "poppler", "**", "pdftoppm*"), recursive=True)
    return hits[0] if hits else None


def main():
    ap = argparse.ArgumentParser(description="Render a .docx to PDF and PNG pages (needs LibreOffice)")
    ap.add_argument("docx")
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--dpi", type=int, default=70)
    a = ap.parse_args()

    docx_path = os.path.abspath(a.docx)
    if not os.path.isfile(docx_path):
        raise SystemExit("arti-docx preview: no such file: %s" % docx_path)
    soffice = find_soffice()
    if not soffice:
        print("arti-docx preview: LibreOffice not found, preview skipped (optional developer aid)")
        return
    out_dir = os.path.abspath(a.out_dir or os.path.join(os.path.dirname(docx_path), "preview"))
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(docx_path))[0]

    # own profile folder, so a LibreOffice window the user has open does not block the conversion
    with tempfile.TemporaryDirectory() as profile:
        cmd = [soffice, "-env:UserInstallation=file:///" + profile.replace("\\", "/"), "--headless",
               "--convert-to", "pdf", "--outdir", out_dir, docx_path]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    pdf = os.path.join(out_dir, name + ".pdf")
    if not os.path.isfile(pdf):
        raise SystemExit("arti-docx preview: LibreOffice produced no PDF: %s" % (p.stderr or p.stdout).strip()[:300])
    print("arti-docx preview: %s" % pdf)

    pdftoppm = find_pdftoppm()
    if not pdftoppm:
        print("arti-docx preview: pdftoppm not found, PNG pages skipped")
        return
    for old in glob.glob(os.path.join(out_dir, name + "-*.png")):
        os.remove(old)
    subprocess.run([pdftoppm, "-r", str(a.dpi), "-png", pdf, os.path.join(out_dir, name)], check=True)
    for png in sorted(glob.glob(os.path.join(out_dir, name + "-*.png"))):
        print("arti-docx preview: %s" % png)


if __name__ == "__main__":
    main()
