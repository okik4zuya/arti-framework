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
import sys
import threading
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent / "server"))

import server as dashboard_server  # noqa: E402
import webview  # noqa: E402

HOST = dashboard_server.HOST
PORT = dashboard_server.PORT

# pywebview's edgechromium backend needs the Evergreen WebView2 Runtime, an OS
# component; without it, CoreWebView2Environment init fails inside the
# WinForms/pythonnet interop layer (logged by pywebview, not raised as a
# catchable Python exception), leaving a blank white window with no error
# surfaced to the user. Checking for it *before* creating the window lets us
# fall back to a browser tab instead of showing that dead window. Detection
# (registry version plus a binary that really opens, since the Windows Sandbox
# base image lists a phantom msedgewebview2.exe) and the one-time background
# install live in server/webview2_runtime.py.
import webview2_runtime  # noqa: E402

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

    if not webview2_runtime.runtime_present():
        # No native window without WebView2 -- same browser-tab model mac/linux
        # already use (see dashboard/README.md), rather than a blank window
        # pywebview would otherwise silently show. Runs serve_forever() on the
        # main thread (no webview event loop to share it with here); "Quit
        # Dashboard" in the page footer (POST /api/shutdown) is what stops it,
        # same as on mac/linux. Meanwhile the runtime is installed once in the
        # background (same lock as install.ps1, no retry for 24 hours after a
        # failure); the page shows a banner with the progress and a Retry button.
        verdict = webview2_runtime.maybe_start_install()
        print(
            f"[arti] WebView2 Runtime not found ({verdict}) -- opening {url} in your default browser "
            f"instead of a native window. Manual install: {webview2_runtime.MANUAL_URL}",
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
