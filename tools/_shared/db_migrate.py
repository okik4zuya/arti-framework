"""Shared `PRAGMA user_version` migration runner for ARTi's SQLite-backed tools
(tools/arti-db, tools/arti-lit). Each caller keeps its own SCHEMA_VERSION constant
and MIGRATIONS dict; this module only knows how to read/compare/bump user_version
and run the right steps in between, once.

Purely additive schema changes (new table via CREATE TABLE IF NOT EXISTS, new
nullable/defaulted column via ALTER TABLE ... ADD COLUMN) don't need an entry here
-- callers keep running those unconditionally, same as before this module existed,
since re-running them against an already-migrated db is a no-op. This module exists
for the case that pattern can't handle: renamed/dropped columns, type changes,
backfills -- anything that must run exactly once, in order, against a db that may
be sitting at any older version.
"""


def migrate(conn, migrations, target_version):
    """Brings `conn`'s database from its current `PRAGMA user_version` up to
    `target_version`, running each version's migration step in order.

    `migrations` maps the version a step upgrades FROM to a callable(conn) that
    performs that one step. A version with no entry (e.g. one covered entirely
    by the caller's own additive CREATE/ALTER TABLE calls) is simply skipped.
    No-op if the db is already at or past target_version. Commits when done.
    """
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    while current < target_version:
        step = migrations.get(current)
        if step is not None:
            step(conn)
        current += 1
        conn.execute(f"PRAGMA user_version = {current}")
    conn.commit()
