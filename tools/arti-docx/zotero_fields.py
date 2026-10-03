"""
Zotero-compatible Word fields for arti-docx (`--cite zotero`).

Emits `ADDIN ZOTERO_ITEM CSL_CITATION` fields for inline `[LIT: key]` markers and one
`ADDIN ZOTERO_BIBL` field for the reference list, so a co-author with Zotero can Refresh/edit and
Zotero (not this tool) formats the journal style. Structure follows the observed template spec in
`memory/memories/zotero-docx-field-format.md`.

There is no CSL engine here: the cached text inside each field is an author-year placeholder
(`(Kaw et al., 2016)`, bibliography in a plain APA-like shape) that is only correct until the
first Zotero Refresh, which re-renders every field in the style stored in ZOTERO_PREF.

Metadata comes from `literature/arti-lit.db`'s `csl_json` column (filled by `arti-lit library
enrich`). Unknown keys or keys without csl_json raise CiteError listing them all -- never a
silent empty citation.
"""
import hashlib
import json
import os
import random
import re
import sqlite3
import string
from xml.sax.saxutils import escape

from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

CITE_RE = re.compile(r"\[LIT:\s*([^\]]+)\]")
SCHEMA = "https://github.com/citation-style-language/schema/raw/master/csl-citation.json"
DEFAULT_STYLE = "http://www.zotero.org/styles/apa"
# itemData fields kept per item (abstract/links/references omitted: bulk Zotero doesn't need)
KEEP = ("type", "title", "container-title", "volume", "issue", "page", "DOI", "ISSN",
        "publisher", "author", "editor", "issued", "URL")


class CiteError(RuntimeError):
    pass


def scan_keys(md_text):
    """All distinct keys cited in the Markdown, in order of first appearance."""
    seen = []
    for m in CITE_RE.finditer(md_text):
        for k in split_keys(m.group(1)):
            if k not in seen:
                seen.append(k)
    return seen


def split_keys(raw):
    return [k.strip().lower() for k in raw.split(",") if k.strip()]


def load_items(project, keys):
    """{key: csl dict} for every key, or CiteError naming every problem key."""
    db_path = os.path.join(os.path.abspath(project or "."), "literature", "arti-lit.db")
    if not os.path.exists(db_path):
        raise CiteError("no literature/arti-lit.db under %s (pass --project)" % os.path.abspath(project or "."))
    conn = sqlite3.connect(db_path)
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(sources)")}
        if "csl_json" not in cols:
            raise CiteError("arti-lit.db has no csl_json column -- run `arti-lit library enrich` first")
        rows = {k: c for k, c in conn.execute("SELECT key, csl_json FROM sources")}
    finally:
        conn.close()
    missing = [k for k in keys if k not in rows]
    no_csl = [k for k in keys if k in rows and not rows[k]]
    if missing or no_csl:
        parts = []
        if missing:
            parts.append("not in arti-lit: " + ", ".join(missing))
        if no_csl:
            parts.append("no csl_json (run `library enrich`, or fill metadata by hand if no DOI): " + ", ".join(no_csl))
        raise CiteError("cannot resolve citations -- " + "; ".join(parts))
    items = {}
    for k in keys:
        csl = json.loads(rows[k])
        items[k] = {f: csl[f] for f in KEEP if f in csl}
    return items


# ---- cached placeholder text -------------------------------------------------------------

def _family(a):
    return a.get("family") or a.get("literal") or a.get("name") or ""


def _year(item):
    try:
        return str(item["issued"]["date-parts"][0][0])
    except (KeyError, IndexError, TypeError):
        return "n.d."


def _short(item):
    names = [_family(a) for a in item.get("author", []) if _family(a)]
    if not names:
        return re.sub(r"<[^>]+>", "", item.get("title", "Anon."))[:30]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return "%s & %s" % tuple(names)
    return names[0] + " et al."


def cite_text(entries):
    return "(" + "; ".join("%s, %s" % (_short(i), _year(i)) for _, i in entries) + ")"


def _initials(given):
    return " ".join(p[0] + "." for p in re.split(r"[\s-]+", given or "") if p)


def bib_text(item):
    authors = []
    for a in item.get("author", []):
        fam = _family(a)
        ini = _initials(a.get("given"))
        authors.append("%s, %s" % (fam, ini) if ini else fam)
    au = ", ".join(authors) if authors else _short(item)
    title = re.sub(r"<[^>]+>", "", item.get("title", ""))
    if isinstance(item.get("container-title"), list):
        item = dict(item, **{"container-title": (item["container-title"] or [""])[0]})
    venue = item.get("container-title", "")
    bits = [b for b in (venue, item.get("volume", ""), item.get("page", "")) if b]
    out = "%s (%s). %s." % (au, _year(item), title)
    if bits:
        out += " " + ", ".join(bits) + "."
    if item.get("DOI"):
        out += " https://doi.org/" + item["DOI"]
    return out


# ---- XML builders ------------------------------------------------------------------------

def _run(inner):
    return parse_xml('<w:r %s>%s</w:r>' % (nsdecls("w"), inner))


def _fld(kind):
    return _run('<w:fldChar w:fldCharType="%s"/>' % kind)


def _instr(text):
    return _run('<w:instrText xml:space="preserve"> %s </w:instrText>' % escape(text))


def _text(text):
    return _run('<w:t xml:space="preserve">%s</w:t>' % escape(text))


def _uri(key):
    return "http://zotero.org/users/local/items/" + hashlib.md5(key.encode()).hexdigest()[:8].upper()


class ZoteroCiter:
    def __init__(self, items):
        self.items = items
        self.ids = {k: n for n, k in enumerate(sorted(items), 1)}
        self.cited = []

    def citation_runs(self, keys):
        """Runs (begin, instr, separate, cached text, end) for one `[LIT: a, b]` marker."""
        entries = []
        for k in keys:
            entries.append((k, self.items[k]))
            if k not in self.cited:
                self.cited.append(k)
        text = cite_text(entries)
        payload = {
            "citationID": "".join(random.choices(string.ascii_letters + string.digits, k=8)),
            "properties": {"formattedCitation": text, "plainCitation": text, "noteIndex": 0},
            "citationItems": [
                {"id": self.ids[k], "uris": [_uri(k)], "itemData": dict(i, id=self.ids[k])}
                for k, i in entries
            ],
            "schema": SCHEMA,
        }
        return [
            _fld("begin"),
            _instr("ADDIN ZOTERO_ITEM CSL_CITATION " + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))),
            _fld("separate"),
            _text(text),
            _fld("end"),
        ]

    def bibliography_paragraphs(self, style_name="Bibliography"):
        """Paragraphs for the ZOTERO_BIBL field: begin/instr/separate in the first entry, `end`
        in a trailing empty paragraph. Entries sorted by first author, then year."""
        keys = sorted(self.cited, key=lambda k: (_short(self.items[k]).lower(), _year(self.items[k])))
        paras = []
        for n, k in enumerate(keys):
            p = parse_xml('<w:p %s><w:pPr><w:pStyle w:val="%s"/></w:pPr></w:p>' % (nsdecls("w"), style_name))
            if n == 0:
                p.append(_fld("begin"))
                p.append(_instr('ADDIN ZOTERO_BIBL {"uncited":[],"omitted":[],"custom":[]} CSL_BIBLIOGRAPHY'))
                p.append(_fld("separate"))
            p.append(_text(bib_text(self.items[k])))
            paras.append(p)
        end = parse_xml("<w:p %s/>" % nsdecls("w"))
        end.append(_fld("end"))
        paras.append(end)
        return paras


def set_style_pref(document, style_id=DEFAULT_STYLE):
    """Rewrite ZOTERO_PREF_n in docProps/custom.xml so Refresh uses `style_id`. No-op if the
    template carries no custom-properties part (Zotero then asks for a style on first use)."""
    part = next((p for p in document.part.package.iter_parts() if str(p.partname) == "/docProps/custom.xml"), None)
    if part is None:
        return False
    pref = ('<data data-version="3" zotero-version="9.0.6"><session id="%s"/>'
            '<style id="%s" hasBibliography="1" bibliographyStyleHasBeenSet="1"/>'
            '<prefs><pref name="fieldType" value="Field"/>'
            '<pref name="automaticJournalAbbreviations" value="true"/></prefs></data>'
            % ("".join(random.choices(string.ascii_letters + string.digits, k=8)), style_id))
    chunks = [pref[i:i + 255] for i in range(0, len(pref), 255)]
    xml = part.blob.decode("utf-8")
    # drop old pref properties, then append new ones with fresh pids
    xml = re.sub(r'<property [^>]*name="ZOTERO_PREF_\d+">.*?</property>', "", xml, flags=re.S)
    pids = [int(x) for x in re.findall(r'pid="(\d+)"', xml)]
    pid = max(pids + [1]) + 1
    props = ""
    for n, c in enumerate(chunks, 1):
        props += ('<property fmtid="{D5CDD505-2E9C-101B-9397-08002B2CF9AE}" pid="%d" name="ZOTERO_PREF_%d">'
                  '<vt:lpwstr>%s</vt:lpwstr></property>' % (pid, n, escape(c)))
        pid += 1
    xml = xml.replace("</Properties>", props + "</Properties>")
    part._blob = xml.encode("utf-8")
    return True
