"""Lookup helpers for binaries vendored into ~/.arti/bin by the NSIS installer.

bin/ is populated exclusively by the NSIS installer (installer/arti-installer.nsi) - it is
NOT fetched by install.ps1/install.sh. On a machine that used git-clone/script-based setup,
these paths simply won't exist. Callers must check before use (e.g. os.path.exists(...))
rather than assuming poppler/tesseract are always present. See tools/_shared/README.md.
"""

import os

ARTI_HOME = os.environ.get("ARTI_HOME") or os.path.expanduser("~/.arti")


def poppler_bin_dir():
    return os.path.join(ARTI_HOME, "bin", "poppler", "Library", "bin")


def tesseract_exe():
    return os.path.join(ARTI_HOME, "bin", "tesseract", "tesseract.exe")
