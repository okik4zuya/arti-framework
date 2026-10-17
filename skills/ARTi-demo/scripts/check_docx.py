"""Look inside a finished .docx and report what is really in it (not what the source Markdown says).

    python.exe scripts/check_docx.py submission/manuscript.docx [--expect-zotero]

Counts Zotero citation fields (`ZOTERO_ITEM`), bibliography fields (`ZOTERO_BIBL`), embedded images, tables, and the
approximate number of words in the body. With --expect-zotero, exits 1 unless there is at least one citation field and
exactly one bibliography field and the .docx was built from `tools/arti-docx/assets/default-academic-template-zotero.docx`
(all its styles and customXml parts present). Prints one JSON object.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

# <ARTi home>/tools/arti-docx/assets/ (this file is <ARTi home>/skills/ARTi-demo/scripts/check_docx.py)
ASSETS = Path(__file__).resolve().parents[3] / "tools" / "arti-docx" / "assets"
ZOTERO_TEMPLATE = ASSETS / "default-academic-template-zotero.docx"


def _style_ids(zf):
    return set(re.findall(r'w:styleId="([^"]+)"', zf.read("word/styles.xml").decode("utf-8", errors="replace")))


def uses_zotero_template(zf):
    """True when every style of default-academic-template-zotero.docx is in the .docx and its customXml parts
    (which carry the Zotero document preferences) are still there. A .docx built from the plain template lacks both."""
    if not ZOTERO_TEMPLATE.is_file():
        return None
    with zipfile.ZipFile(ZOTERO_TEMPLATE) as t:
        want_styles = _style_ids(t)
        want_parts = {n for n in t.namelist() if n.startswith("customXml/item") and n.endswith(".xml")}
    return want_styles <= _style_ids(zf) and want_parts <= set(zf.namelist())


def inspect(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
        zotero_template = uses_zotero_template(z)
    instr = " ".join(re.findall(r"<w:instrText[^>]*>(.*?)</w:instrText>", xml, flags=re.S))
    # fldSimple fields keep the instruction in an attribute
    instr += " " + " ".join(re.findall(r'<w:fldSimple[^>]*w:instr="([^"]*)"', xml))
    text = " ".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", xml, flags=re.S))
    return {
        "zotero_citation_fields": instr.count("ZOTERO_ITEM"),
        "zotero_bibliography_fields": instr.count("ZOTERO_BIBL"),
        "images": sum(1 for n in names if n.startswith("word/media/")),
        "drawings": xml.count("<w:drawing"),
        "tables": xml.count("<w:tbl>"),
        "zotero_template": zotero_template,
        "words_approx": len(text.split()),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--expect-zotero", action="store_true")
    a = ap.parse_args()
    try:
        info = inspect(a.docx)
    except (OSError, zipfile.BadZipFile, KeyError) as e:
        print(json.dumps({"ok": False, "error": "%s: %s" % (type(e).__name__, e)}))
        sys.exit(1)
    ok = True
    if a.expect_zotero:
        ok = info["zotero_citation_fields"] >= 1 and info["zotero_bibliography_fields"] == 1 and info["zotero_template"] is True
    print(json.dumps(dict(info, ok=ok)))
    sys.exit(0 if ok else 1)
