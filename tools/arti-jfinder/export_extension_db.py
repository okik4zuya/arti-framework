"""One-shot export: trims `arti-jfinder.db` down to the columns the
Scopus/ScienceDirect journal-metrics Chrome extension needs, and writes them
to a standalone SQLite file the extension bundles and queries via sql.js.

Run manually whenever the researcher re-ingests a new Scimago snapshot
(`ingest --file --year`), then re-publish the extension with the refreshed
file. Not wired into any CLI subcommand -- this is maintainer tooling, not
part of arti-jfinder's JSON command surface.

Usage:
    python export_extension_db.py [OUTPUT_PATH]

Defaults OUTPUT_PATH to <this project>/extension/assets/journals.sqlite.
"""
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

from db import DB_PATH, _latest_year, _connect

DEFAULT_OUTPUT = Path(
    r"C:\python_tools\arti_jfinder\ARTi Journal Finder\extension\assets\journals.sqlite"
)

TRIMMED_SCHEMA = """
CREATE TABLE journals (
  sourceid          INTEGER PRIMARY KEY,
  title             TEXT NOT NULL,
  issn              TEXT,
  eissn             TEXT,
  sjr               REAL,
  sjr_best_quartile TEXT,
  h_index           INTEGER,
  norm_title        TEXT
);
CREATE INDEX idx_journals_issn ON journals (issn);
CREATE INDEX idx_journals_eissn ON journals (eissn);
CREATE INDEX idx_journals_norm_title ON journals (norm_title);
"""


def normalize_title(title):
    """Mirrors offscreen.js's normalizeTitle() exactly -- title lookups are an
    exact match between this precomputed column and the extension's
    normalized query string. Needed for Google Scholar, which has no
    sourceid/ISSN to key off and relies on title matching entirely; without a
    precomputed column, the old query (`WHERE lower(title) = :t`) never
    matched because `lower()` alone doesn't strip punctuation like the JS
    side does."""
    if not title:
        return None
    s = unicodedata.normalize("NFKD", title)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s or None


def export(output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    src = _connect()
    try:
        year = _latest_year(src)
        if year is None:
            raise ValueError("arti-jfinder.db has no journal_metrics rows -- ingest a snapshot first")

        rows = src.execute(
            "SELECT j.sourceid, j.title, j.issn, j.eissn, m.sjr, m.sjr_best_quartile, m.h_index "
            "FROM journals j JOIN journal_metrics m ON m.journal_id = j.sourceid "
            "WHERE m.year = ?",
            (year,),
        ).fetchall()
    finally:
        src.close()

    dst = sqlite3.connect(output_path)
    try:
        dst.executescript(TRIMMED_SCHEMA)
        dst.executemany(
            "INSERT INTO journals (sourceid, title, issn, eissn, sjr, sjr_best_quartile, h_index, norm_title) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    r["sourceid"],
                    r["title"],
                    r["issn"],
                    r["eissn"],
                    r["sjr"],
                    r["sjr_best_quartile"],
                    r["h_index"],
                    normalize_title(r["title"]),
                )
                for r in rows
            ],
        )
        dst.commit()
        dst.execute("VACUUM")
    finally:
        dst.close()

    return {"year": year, "rows": len(rows), "output": str(output_path), "source_db": str(DB_PATH)}


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    result = export(out)
    print(f"Exported {result['rows']} journals (year {result['year']}) -> {result['output']}")
