"""Shared locations for the licensing test harnesses (no hardcoded user paths).

ARTI_TEST_SHOTS    screenshot folder (default: <temp>/arti-license-shots)
ARTI_SERVICES      the arti-services repo, for publish_release.py (default: ~/arti-services)
ARTI_TEST_BROWSER  a system Edge/Chrome executable; Playwright's own browsers are never installed
"""
import os
import tempfile
from pathlib import Path

CODE = Path(__file__).resolve().parents[2]
SHOTS = Path(os.environ.get("ARTI_TEST_SHOTS") or Path(tempfile.gettempdir()) / "arti-license-shots")
SHOTS.mkdir(parents=True, exist_ok=True)
SERVICES = Path(os.environ.get("ARTI_SERVICES") or Path.home() / "arti-services")
BROWSER = os.environ.get("ARTI_TEST_BROWSER") or next(
    (p for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                 r"C:\Program Files\Google\Chrome\Application\chrome.exe") if os.path.exists(p)), None)
if BROWSER is None:
    raise SystemExit("No system Edge/Chrome found; set ARTI_TEST_BROWSER")
