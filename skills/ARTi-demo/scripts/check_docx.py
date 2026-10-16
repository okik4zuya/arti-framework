"""Look inside a finished .docx and report what is really in it (not what the source Markdown says).

    python.exe scripts/check_docx.py submission/manuscript.docx [--expect-zotero]

Counts Zotero citation fields (`ZOTERO_ITEM`), bibliography fields (`ZOTERO_BIBL`), embedded images, tables, and the
approximate number of words in the body. With --expect-zotero, exits 1 unless there is at least one citation field and
exactly one bibliography field. Prints one JSON object.
"""
import argparse
import json
import re
import sys
import zipfile


def inspect(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
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
        ok = info["zotero_citation_fields"] >= 1 and info["zotero_bibliography_fields"] == 1
    print(json.dumps(dict(info, ok=ok)))
    sys.exit(0 if ok else 1)
