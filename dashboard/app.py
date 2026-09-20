"""ARTi Framework dashboard -- native window entry point (Windows).

Replaces start-arti-framework.vbs as what the taskbar/Desktop shortcut
launches directly (pythonw.exe app.py). Single process now owns both the
HTTP server (server/server.py, run on a background thread, unchanged) and a
native pywebview window -- no more browser tab, no more subprocess-spawned
server.

Single-instance is enforced by trying to bind PORT first: if that fails,
another instance already owns it, so this process POSTs /api/focus to bring
the existing window forward and exits without creating a second window. This
replaces the old .vbs's IsAlive() liveness-check/reuse loop.
"""
import os
import sys
import threading
import webbrowser
import winreg
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent / "server"))

import server as dashboard_server  # noqa: E402
import webview  # noqa: E402

HOST = dashboard_server.HOST
PORT = dashboard_server.PORT

# Evergreen WebView2 Runtime's fixed client GUID -- same one Microsoft's own
# detection guidance checks. pywebview's edgechromium backend needs this OS
# component installed; without it, CoreWebView2Environment init fails inside
# the WinForms/pythonnet interop layer (logged by pywebview, not raised as a
# catchable Python exception), leaving a blank white window with no error
# surfaced to the user. Checking for it *before* creating the window lets us
# fall back to a browser tab instead of showing that dead window.
_WEBVIEW2_CLIENT_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
_WEBVIEW2_BOOTSTRAPPER_URL = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"

# Machine-wide (HKLM) and per-user (HKCU) install locations the Evergreen Runtime's
# registry entry can point at -- keyed by product name, joined with the registered
# version below to get the exact folder msedgewebview2.exe should be sitting in.
_WEBVIEW2_INSTALL_ROOTS = (
    (winreg.HKEY_LOCAL_MACHINE, os.environ.get("ProgramFiles(x86)")),
    (winreg.HKEY_LOCAL_MACHINE, os.environ.get("ProgramFiles")),
    (winreg.HKEY_CURRENT_USER, os.environ.get("LocalAppData")),
)


def _webview2_runtime_present():
    """Registry-only detection is not enough: a machine (Windows Sandbox's base
    image included) can carry the `Clients\\{GUID}\\pv` registration -- Windows
    Update servicing metadata -- without the actual msedgewebview2.exe binary
    being present, which is exactly the FileNotFoundException pywebview hits at
    CoreWebView2Environment.CreateAsync(). So: read the registered version, then
    confirm the real binary exists at the version-specific install path before
    trusting it."""
    subkey = rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_CLIENT_GUID}"
    wow_subkey = rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{_WEBVIEW2_CLIENT_GUID}"
    for hive, base_dir in _WEBVIEW2_INSTALL_ROOTS:
        if not base_dir:
            continue
        version = None
        for key_path in (subkey, wow_subkey):
            try:
                with winreg.OpenKey(hive, key_path) as key:
                    version, _ = winreg.QueryValueEx(key, "pv")
                    break
            except OSError:
                continue
        if not version:
            continue
        exe = Path(base_dir) / "Microsoft" / "EdgeWebView" / "Application" / version / "msedgewebview2.exe"
        if exe.is_file():
            return True
    return False

# Same mark used for the Desktop shortcut (install.ps1) and the favicon --
# passed to webview.start() below so the window/taskbar icon matches too,
# instead of inheriting pythonw.exe's default icon.
ICON_PATH = dashboard_server.ARTI_HOME / "logo" / "export" / "icon" / "arti-launcher.ico"


def _focus_existing():
    try:
        urlopen(Request(f"http://{HOST}:{PORT}/api/focus", data=b"", method="POST"), timeout=2)
    except OSError:
        pass


def _redirect_output_to_log():
    """pythonw.exe has no console, so anything printed (our own messages, or
    Python's default excepthook on an unhandled exception) normally vanishes
    silently instead of surfacing anywhere. Redirect stdout/stderr to
    server.log so it's always inspectable -- called only once main() knows
    this is a genuine fresh spawn (port bind succeeded), not a reused-instance
    focus-and-exit, so a relaunch while ARTi is already running never wipes an
    existing trace. start-arti-dashboard.bat's console window is unaffected:
    it runs python.exe with a real console attached, this only kicks in when
    there isn't one."""
    log_path = dashboard_server.DASHBOARD_DIR / "server.log"
    log_file = open(log_path, "w", encoding="utf-8", buffering=1)
    sys.stdout = log_file
    sys.stderr = log_file


def main():
    try:
        httpd = dashboard_server.create_server()
    except OSError:
        # Port already bound -- another instance is running. Focus it and exit
        # rather than erroring or opening a second window.
        _focus_existing()
        return

    _redirect_output_to_log()

    url = f"http://{HOST}:{PORT}/"

    if not _webview2_runtime_present():
        # No native window without WebView2 -- same browser-tab model mac/linux
        # already use (see dashboard/README.md), rather than a blank window
        # pywebview would otherwise silently show. Runs serve_forever() on the
        # main thread (no webview event loop to share it with here); "Quit
        # Dashboard" in the page footer (POST /api/shutdown) is what stops it,
        # same as on mac/linux.
        print(
            f"[arti] WebView2 Runtime not found -- opening {url} in your default browser instead "
            f"of a native window. Install it from {_WEBVIEW2_BOOTSTRAPPER_URL} for the native "
            "window next time.",
            file=sys.stderr,
        )
        webbrowser.open(url)
        httpd.serve_forever()
        return

    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    window = webview.create_window(
        "ARTi Framework",
        url,
        width=1280,
        height=860,
        # Small enough that Windows' Win+Left/Right half-screen snap can still
        # shrink the window to 50% width on common laptop resolutions (e.g.
        # 1366px wide -> 683px half) instead of clamping to the old 900px floor.
        min_size=(640, 480),
        text_select=True,
    )
    dashboard_server.set_window(window)

    def on_closed():
        httpd.shutdown()

    window.events.closed += on_closed
    webview.start(icon=str(ICON_PATH) if ICON_PATH.is_file() else None)


if __name__ == "__main__":
    main()
