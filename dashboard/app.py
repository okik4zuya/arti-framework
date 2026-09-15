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
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent / "server"))

import server as dashboard_server  # noqa: E402
import webview  # noqa: E402

HOST = dashboard_server.HOST
PORT = dashboard_server.PORT

# Same mark used for the Desktop shortcut (install.ps1) and the favicon --
# passed to webview.start() below so the window/taskbar icon matches too,
# instead of inheriting pythonw.exe's default icon.
ICON_PATH = dashboard_server.ARTI_HOME / "logo" / "export" / "icon" / "arti-launcher.ico"


def _focus_existing():
    try:
        urlopen(Request(f"http://{HOST}:{PORT}/api/focus", data=b"", method="POST"), timeout=2)
    except OSError:
        pass


def main():
    try:
        httpd = dashboard_server.create_server()
    except OSError:
        # Port already bound -- another instance is running. Focus it and exit
        # rather than erroring or opening a second window.
        _focus_existing()
        return

    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    window = webview.create_window(
        "ARTi Framework",
        f"http://{HOST}:{PORT}/",
        width=1280,
        height=860,
        # Small enough that Windows' Win+Left/Right half-screen snap can still
        # shrink the window to 50% width on common laptop resolutions (e.g.
        # 1366px wide -> 683px half) instead of clamping to the old 900px floor.
        min_size=(640, 480),
    )
    dashboard_server.set_window(window)

    def on_closed():
        httpd.shutdown()

    window.events.closed += on_closed
    webview.start(icon=str(ICON_PATH) if ICON_PATH.is_file() else None)


if __name__ == "__main__":
    main()
