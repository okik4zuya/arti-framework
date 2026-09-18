# `tools/_shared/`

A deliberate, narrow exception — every other tool under `tools/` (`arti-lit`, `arti-pdf`,
`arti-db`, ...) is fully standalone with no shared code. This folder exists only for cases where
duplicating the code a second time would be tolerable but a third time is not: poppler/tesseract
are OS binaries vendored once into `~/.arti/bin/` rather than something each tool would sensibly
re-vendor itself (`paths.py`), and the `PRAGMA user_version` migration runner both `arti-db` and
`arti-lit` need is identical in shape between the two (`db_migrate.py`). It is not the start of a
general shared-framework layer; don't add to it without a similarly narrow, load-bearing reason.

## `db_migrate.py`

Runs ordered, versioned schema migrations against a `sqlite3.Connection`, tracked via
`PRAGMA user_version`:

```python
from tools._shared.db_migrate import migrate

SCHEMA_VERSION = 1
MIGRATIONS = {
    # 0: lambda conn: conn.execute("ALTER TABLE ... "),  # step from version 0 -> 1
}
migrate(conn, MIGRATIONS, SCHEMA_VERSION)
```

Purely additive changes (new `CREATE TABLE IF NOT EXISTS`, new nullable `ALTER TABLE ... ADD
COLUMN`) don't need an entry here — both `arti-db/db.py` and `arti-lit/db.py` keep running those
unconditionally in `init_db()`, same as before this module existed. `db_migrate.py` exists for
what that pattern can't handle: renamed/dropped columns, type changes, backfills — anything that
must run exactly once, in order, against a db that could be sitting at any older version after a
client updates their install. See `init_db()` in either `db.py` for the current call site.

## `paths.py`

Resolves the vendored poppler/tesseract binaries under `~/.arti/bin/`:

```python
from tools._shared.paths import poppler_bin_dir, tesseract_exe
```

- `poppler_bin_dir()` → `~/.arti/bin/poppler/Library/bin`
- `tesseract_exe()` → `~/.arti/bin/tesseract/tesseract.exe`

**`bin/` only exists on a machine that ran the NSIS installer** (`installer/arti-installer.nsi`).
`install.ps1`/`install.sh` (git-clone/script-based setup) do not provision it. Any tool importing
this helper must check for existence before use, e.g.:

```python
import os
from tools._shared.paths import poppler_bin_dir, tesseract_exe

if not os.path.exists(tesseract_exe()):
    raise RuntimeError(
        "tesseract not found under ~/.arti/bin - this machine needs the NSIS installer "
        "(ArtiFrameworkSetup-<ver>.exe) to get OCR support, not install.ps1/install.sh."
    )
```

## Why these binaries are vendored at all

OCR/PDF text extraction (pdfminer + pdf2image + pytesseract) needs poppler and tesseract on disk.
They previously lived only inside the separate `artipdf` repo (`C:\python_tools\artipdf\poppler\`,
`\tesseract\`), resolved via that repo's own PyInstaller-relative `get_base_dir()` scheme, which
nothing in `~/.arti` could reach. The NSIS installer's build step copies those same folders
verbatim into the installer payload (see `../../installer/`), so a future ARTi PDF-ingest tool can
depend on `~/.arti` alone, with zero reference to `artipdf`.

No version pinning, no download URLs: the binaries are a straight local copy of whatever currently
sits in `C:\python_tools\artipdf` at installer-build time.
