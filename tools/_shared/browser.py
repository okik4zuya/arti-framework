"""Locate and drive the system Edge/Chrome in headless mode (no Node, no Playwright).

Shared by arti-convert pdf (Markdown -> PDF) and arti-compose (HTML figure -> vector PDF/PNG). Output
paths are always made absolute: a relative --print-to-pdf/--screenshot path makes the browser
exit 0 without writing anything (verified on Edge, 2026-10-14), so callers must check that the
file exists, never the exit code.
"""

import os
import pathlib
import shutil
import subprocess
import sys


def find_browser():
    if sys.platform == "win32":
        candidates = [
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
    else:
        candidates = [shutil.which("microsoft-edge"), shutil.which("google-chrome"), shutil.which("chromium")]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def file_url(path):
    """file:// URL for a local path; handles spaces and non-ASCII in project paths."""
    return pathlib.Path(path).resolve().as_uri()


def _run(args, timeout):
    # stderr from the browser is noisy (e.g. LoadEnclaveImageW) and not an error signal.
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def print_pdf(html_path, pdf_path, timeout=120, budget_ms=3000):
    """Print html_path to pdf_path honouring the page's own @page size. True only if the file exists."""
    browser = find_browser()
    if not browser:
        return False
    pdf_path = os.path.abspath(pdf_path)
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
    _run([
        browser, "--headless=new", "--disable-gpu", f"--virtual-time-budget={budget_ms}",
        f"--print-to-pdf={pdf_path}", "--no-pdf-header-footer", file_url(html_path),
    ], timeout)
    return os.path.exists(pdf_path)


def screenshot(html_path, png_path, width_px, height_px, scale=1.0, timeout=120, budget_ms=3000):
    """Screenshot at a CSS-pixel window size; output pixels = size * scale. True only if the file exists."""
    browser = find_browser()
    if not browser:
        return False
    png_path = os.path.abspath(png_path)
    if os.path.exists(png_path):
        os.remove(png_path)
    _run([
        browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--virtual-time-budget={budget_ms}",
        f"--window-size={int(width_px)},{int(height_px)}", f"--force-device-scale-factor={scale}",
        f"--screenshot={png_path}", file_url(html_path),
    ], timeout)
    return os.path.exists(png_path)


def dump_dom(html_path, timeout=120, budget_ms=3000, width_px=None, height_px=None):
    """Serialised DOM after scripts ran, or None if no browser. Used to read in-page measurements.
    Pass the page size so layout (and html scroll extents) match the final page, not the default window."""
    browser = find_browser()
    if not browser:
        return None
    size = [f"--window-size={int(width_px)},{int(height_px)}"] if width_px and height_px else []
    r = _run([
        browser, "--headless=new", "--disable-gpu", f"--virtual-time-budget={budget_ms}", *size,
        "--dump-dom", file_url(html_path),
    ], timeout)
    return r.stdout
