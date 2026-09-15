"""SQLite-backed store for arti-jfinder -- a cross-project singleton (like
`tools/arti-db`, unlike per-project `tools/arti-lit`) that imports Scimago's
manually-downloaded `journalrank.php?out=xls` export and serves it back to
Claude during ARTi-idea Stage 5 journal shortlisting. One connection per call,
guarded by a module-level lock, no ORM, no pip deps.

Source file quirks (informed the parsing below):
- `;`-delimited, UTF-8-encoded (the design session assumed cp1252, but the actual 2025 export
  decodes cleanly as UTF-8 and fails cp1252 on accented publisher/country names), decimal-comma
  numerics ("104,065" -> 104.065).
- The `Issn` column packs print+electronic ISSN comma-separated in one field,
  unlabeled as to which is which -- stored positionally as issn/eissn.
- `Publisher` appears twice in the header (duplicate column); the first
  occurrence is used.
- `Categories` is one semicolon-separated string of "Category Name (Qn)"
  pairs, exploded into one `journal_categories` row per pair.
- No SDG column in the 2025 export; `journal_metrics.sdg` stays NULL until a
  future snapshot carries it -- kept in the schema so that snapshot doesn't
  need a migration.
"""
import csv
import re
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

ARTI_HOME = Path(__file__).resolve().parent.parent.parent
DB_PATH = ARTI_HOME / "tools" / "arti-jfinder" / "arti-jfinder.db"

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS journals (
  sourceid   INTEGER PRIMARY KEY,
  title      TEXT NOT NULL,
  issn       TEXT,
  eissn      TEXT,
  type       TEXT,
  publisher  TEXT,
  country    TEXT,
  coverage   TEXT
);

CREATE TABLE IF NOT EXISTS journal_metrics (
  journal_id        INTEGER NOT NULL REFERENCES journals(sourceid),
  year              INTEGER NOT NULL,
  sjr               REAL,
  sjr_best_quartile TEXT,
  h_index           INTEGER,
  total_docs        INTEGER,
  total_docs_3y     INTEGER,
  total_refs        INTEGER,
  total_cites_3y    INTEGER,
  citable_docs_3y   INTEGER,
  cites_per_doc_2y  REAL,
  ref_per_doc       REAL,
  female_pct        REAL,
  overton           INTEGER,
  sdg               TEXT,
  PRIMARY KEY (journal_id, year)
);

CREATE TABLE IF NOT EXISTS journal_categories (
  journal_id INTEGER NOT NULL REFERENCES journals(sourceid),
  year       INTEGER NOT NULL,
  category   TEXT NOT NULL,
  quartile   TEXT
);
CREATE INDEX IF NOT EXISTS idx_journal_categories_lookup
  ON journal_categories (year, category, quartile);

CREATE TABLE IF NOT EXISTS journal_scope (
  journal_id      INTEGER PRIMARY KEY REFERENCES journals(sourceid),
  aims_scope_text TEXT NOT NULL,
  source_url      TEXT,
  fetched_at      TEXT NOT NULL
);
"""

_CATEGORY_RE = re.compile(r"^(.*)\s\((Q[1-4])\)$")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _row_to_dict(row):
    return dict(row) if row is not None else None


def init_db():
    with _lock:
        conn = _connect()
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# ingest
# ---------------------------------------------------------------------------

def _comma_float(s):
    s = (s or "").strip()
    if not s:
        return None
    return float(s.replace(",", "."))


def _int(s):
    s = (s or "").strip()
    if not s:
        return None
    return int(s)


def _split_issn(s):
    s = (s or "").strip()
    if not s:
        return None, None
    parts = [p.strip() for p in s.split(",") if p.strip()]
    issn = parts[0] if len(parts) > 0 else None
    eissn = parts[1] if len(parts) > 1 else None
    return issn, eissn


def _parse_categories(s):
    s = (s or "").strip()
    if not s:
        return []
    out = []
    for chunk in s.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        m = _CATEGORY_RE.match(chunk)
        if m:
            out.append((m.group(1).strip(), m.group(2)))
        else:
            out.append((chunk, None))
    return out


def ingest(file_path, year):
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"file not found: {path}")

    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader)
        rows = list(reader)

    expected_min_cols = 25
    if len(header) < expected_min_cols:
        raise ValueError(
            f"unexpected header shape ({len(header)} columns) -- not a Scimago export?"
        )

    journals_n = 0
    metrics_n = 0
    categories_n = 0
    skipped = 0

    with _lock:
        conn = _connect()
        try:
            conn.executescript(SCHEMA)
            conn.execute("DELETE FROM journal_metrics WHERE year = ?", (year,))
            conn.execute("DELETE FROM journal_categories WHERE year = ?", (year,))

            for r in rows:
                if len(r) < expected_min_cols:
                    skipped += 1
                    continue
                try:
                    sourceid = _int(r[1])
                    title = r[2].strip()
                    jtype = r[3].strip() or None
                    issn, eissn = _split_issn(r[4])
                    publisher = r[5].strip() or None
                    sjr = _comma_float(r[8])
                    sjr_best_quartile = r[9].strip() or None
                    h_index = _int(r[10])
                    total_docs = _int(r[11])
                    total_docs_3y = _int(r[12])
                    total_refs = _int(r[13])
                    total_cites_3y = _int(r[14])
                    citable_docs_3y = _int(r[15])
                    cites_per_doc_2y = _comma_float(r[16])
                    ref_per_doc = _comma_float(r[17])
                    female_pct = _comma_float(r[18])
                    overton = _int(r[19])
                    country = r[20].strip() or None
                    coverage = r[23].strip() or None
                    categories = _parse_categories(r[24])
                except (ValueError, IndexError) as e:
                    skipped += 1
                    continue

                if sourceid is None or not title:
                    skipped += 1
                    continue

                conn.execute(
                    "INSERT INTO journals (sourceid, title, issn, eissn, type, publisher, country, coverage) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT(sourceid) DO UPDATE SET "
                    "title=excluded.title, issn=excluded.issn, eissn=excluded.eissn, "
                    "type=excluded.type, publisher=excluded.publisher, "
                    "country=excluded.country, coverage=excluded.coverage",
                    (sourceid, title, issn, eissn, jtype, publisher, country, coverage),
                )
                journals_n += 1

                conn.execute(
                    "INSERT INTO journal_metrics (journal_id, year, sjr, sjr_best_quartile, h_index, "
                    "total_docs, total_docs_3y, total_refs, total_cites_3y, citable_docs_3y, "
                    "cites_per_doc_2y, ref_per_doc, female_pct, overton, sdg) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                    (sourceid, year, sjr, sjr_best_quartile, h_index, total_docs, total_docs_3y,
                     total_refs, total_cites_3y, citable_docs_3y, cites_per_doc_2y, ref_per_doc,
                     female_pct, overton),
                )
                metrics_n += 1

                for category, quartile in categories:
                    conn.execute(
                        "INSERT INTO journal_categories (journal_id, year, category, quartile) "
                        "VALUES (?, ?, ?, ?)",
                        (sourceid, year, category, quartile),
                    )
                    categories_n += 1

            conn.commit()
        finally:
            conn.close()

    return {
        "year": year,
        "journals": journals_n,
        "metrics_rows": metrics_n,
        "category_rows": categories_n,
        "skipped_rows": skipped,
        "source_rows": len(rows),
    }


# ---------------------------------------------------------------------------
# journal
# ---------------------------------------------------------------------------

def _latest_year(conn):
    row = conn.execute("SELECT MAX(year) AS y FROM journal_metrics").fetchone()
    return row["y"] if row else None


def journal_search(category=None, quartile=None, min_sjr=None, keyword=None, year=None, limit=20):
    with _lock:
        conn = _connect()
        try:
            resolved_year = year or _latest_year(conn)
            if resolved_year is None:
                return []

            clauses = ["m.year = ?"]
            params = [resolved_year]
            join_categories = bool(category or quartile)

            if category:
                clauses.append("c.category = ? COLLATE NOCASE")
                params.append(category)
            if quartile:
                clauses.append("c.quartile = ?")
                params.append(quartile)
            if min_sjr is not None:
                clauses.append("m.sjr >= ?")
                params.append(min_sjr)
            if keyword:
                clauses.append("j.title LIKE ? ESCAPE '\\'")
                params.append(f"%{keyword}%")

            query = (
                "SELECT DISTINCT j.sourceid, j.title, j.issn, j.eissn, j.type, j.publisher, "
                "j.country, j.coverage, m.sjr, m.sjr_best_quartile, m.h_index, m.total_docs, "
                "m.total_docs_3y, m.total_refs, m.total_cites_3y, m.citable_docs_3y, "
                "m.cites_per_doc_2y, m.ref_per_doc, m.female_pct, m.overton, m.year "
                "FROM journals j JOIN journal_metrics m ON m.journal_id = j.sourceid "
            )
            if join_categories:
                query += "JOIN journal_categories c ON c.journal_id = j.sourceid AND c.year = m.year "
            query += "WHERE " + " AND ".join(clauses)
            query += " ORDER BY m.sjr DESC NULLS LAST LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [_row_to_dict(r) for r in rows]
        finally:
            conn.close()


def journal_get(sourceid):
    with _lock:
        conn = _connect()
        try:
            journal = conn.execute(
                "SELECT * FROM journals WHERE sourceid = ?", (sourceid,)
            ).fetchone()
            if journal is None:
                return None
            journal = _row_to_dict(journal)

            year = _latest_year(conn)
            metrics = None
            categories = []
            if year is not None:
                metrics = conn.execute(
                    "SELECT * FROM journal_metrics WHERE journal_id = ? AND year = ?",
                    (sourceid, year),
                ).fetchone()
                metrics = _row_to_dict(metrics)
                categories = [
                    _row_to_dict(r)
                    for r in conn.execute(
                        "SELECT category, quartile FROM journal_categories "
                        "WHERE journal_id = ? AND year = ? ORDER BY category",
                        (sourceid, year),
                    ).fetchall()
                ]

            journal["metrics"] = metrics
            journal["categories"] = categories
            return journal
        finally:
            conn.close()


def _normalize_title(s):
    """Port of the extension's offscreen.js normalizeTitle() -- lowercase,
    strip diacritics, spell out '&' as Scimago's Title column does, collapse
    non-alphanumerics to spaces."""
    import unicodedata
    if not s:
        return None
    s = s.lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def journal_lookup(issn=None, title=None, year=None):
    """Looks up one journal by ISSN (exact, either issn or eissn column) or,
    failing that, by normalized title (coarse LIKE pre-filter on the title's
    first significant word, then an exact normalized-title compare in
    Python -- journals.title has no precomputed norm_title column in this
    master DB, unlike the extension's trimmed export). Mirrors offscreen.js's
    lookupOne()."""
    with _lock:
        conn = _connect()
        try:
            resolved_year = year or _latest_year(conn)
            if resolved_year is None:
                return None

            def _fetch(sourceid):
                journal = _row_to_dict(conn.execute(
                    "SELECT sourceid, title, issn, eissn FROM journals WHERE sourceid = ?",
                    (sourceid,),
                ).fetchone())
                if journal is None:
                    return None
                metrics = _row_to_dict(conn.execute(
                    "SELECT sjr, sjr_best_quartile, h_index FROM journal_metrics "
                    "WHERE journal_id = ? AND year = ?",
                    (sourceid, resolved_year),
                ).fetchone()) or {}
                return {
                    "sourceid": journal["sourceid"],
                    "title": journal["title"],
                    "issn": journal["issn"],
                    "eissn": journal["eissn"],
                    "sjr": metrics.get("sjr"),
                    "sjr_best_quartile": metrics.get("sjr_best_quartile"),
                    "h_index": metrics.get("h_index"),
                }

            if issn:
                code = re.sub(r"[^0-9Xx]", "", issn).upper()
                if code:
                    row = conn.execute(
                        "SELECT sourceid FROM journals WHERE issn = ? OR eissn = ? LIMIT 1",
                        (code, code),
                    ).fetchone()
                    if row is not None:
                        return _fetch(row["sourceid"])

            norm = _normalize_title(title)
            if norm:
                first_word = norm.split(" ", 1)[0]
                candidates = conn.execute(
                    "SELECT sourceid, title FROM journals WHERE title LIKE ? ESCAPE '\\'",
                    (f"%{first_word}%",),
                ).fetchall()
                for c in candidates:
                    if _normalize_title(c["title"]) == norm:
                        return _fetch(c["sourceid"])

            return None
        finally:
            conn.close()


def journal_categories(year=None):
    with _lock:
        conn = _connect()
        try:
            resolved_year = year or _latest_year(conn)
            if resolved_year is None:
                return []
            rows = conn.execute(
                "SELECT DISTINCT category FROM journal_categories WHERE year = ? ORDER BY category",
                (resolved_year,),
            ).fetchall()
            return [r["category"] for r in rows]
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# scope
# ---------------------------------------------------------------------------

def scope_get(sourceid):
    with _lock:
        conn = _connect()
        try:
            row = conn.execute(
                "SELECT * FROM journal_scope WHERE journal_id = ?", (sourceid,)
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()


def scope_set(sourceid, text, source_url=None):
    with _lock:
        conn = _connect()
        try:
            journal = conn.execute(
                "SELECT sourceid FROM journals WHERE sourceid = ?", (sourceid,)
            ).fetchone()
            if journal is None:
                raise ValueError(f"no journal with sourceid {sourceid!r}")
            now = _now()
            conn.execute(
                "INSERT INTO journal_scope (journal_id, aims_scope_text, source_url, fetched_at) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(journal_id) DO UPDATE SET "
                "aims_scope_text=excluded.aims_scope_text, source_url=excluded.source_url, "
                "fetched_at=excluded.fetched_at",
                (sourceid, text, source_url, now),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM journal_scope WHERE journal_id = ?", (sourceid,)
            ).fetchone()
            return _row_to_dict(row)
        finally:
            conn.close()
