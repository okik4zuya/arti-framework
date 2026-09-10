# `tools/_shared/`

A deliberate, narrow exception — every other tool under `tools/` (`arti-lit`, `arti-pdf`,
`arti-db`, ...) is fully standalone with no shared code. This folder exists only because
poppler/tesseract are OS binaries vendored once into `~/.arti/bin/` rather than something each
tool would sensibly re-vendor itself. It is not the start of a shared-framework layer; don't add
to it without a similarly binary-shaped reason.

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
