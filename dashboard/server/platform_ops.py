"""Per-OS operations for the ARTi dashboard: opening VS Code, opening a file
manager, and browsing for a folder. One module, three functions, each with a
platform.system() branch -- keeps every OS-specific detail here instead of
scattered `if sys.platform` checks in server.py.
"""
import base64
import json
import platform
import shutil
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BROWSE_SCRIPT = SCRIPT_DIR / "browse-folder.ps1"
BROWSE_FILES_SCRIPT = SCRIPT_DIR / "browse-files.ps1"
LAUNCH_SCRIPT = SCRIPT_DIR / "launch-focused.ps1"


class NoPickerAvailable(Exception):
    """Raised on Linux when neither zenity nor kdialog is on PATH."""


def _run_powershell_focused(exe, args, timeout=15, hidden=False):
    payload_b64 = base64.b64encode(json.dumps({"exe": exe, "args": args, "hidden": hidden}).encode("utf-8")).decode("ascii")
    kwargs = {}
    if platform.system() == "Windows":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
         "-File", str(LAUNCH_SCRIPT), "-PayloadB64", payload_b64],
        capture_output=True, timeout=timeout, **kwargs,
    )


def open_in_vscode(path):
    system = platform.system()
    path = str(path)
    if system == "Windows":
        _run_powershell_focused("code.cmd", ["-n", path], hidden=True)
    else:
        # The VS Code CLI shim ("code") is on PATH after the standard installer
        # on macOS/Linux too -- no per-OS branching needed for the launch itself.
        subprocess.Popen(["code", "-n", path])


def open_in_file_manager(path):
    system = platform.system()
    path = str(path)
    if system == "Windows":
        _run_powershell_focused("explorer.exe", [path])
    elif system == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def browse_folder():
    """Returns the chosen absolute path, or None if cancelled / no picker available."""
    system = platform.system()
    if system == "Windows":
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass", "-File", str(BROWSE_SCRIPT)],
            capture_output=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        chosen = result.stdout.decode("utf-8", "replace").strip()
        return chosen or None
    elif system == "Darwin":
        result = subprocess.run(
            ["osascript", "-e", 'POSIX path of (choose folder)'],
            capture_output=True, timeout=120,
        )
        chosen = result.stdout.decode("utf-8", "replace").strip()
        return chosen or None
    else:
        picker = None
        if shutil.which("zenity"):
            picker = ["zenity", "--file-selection", "--directory"]
        elif shutil.which("kdialog"):
            picker = ["kdialog", "--getexistingdirectory"]
        if not picker:
            raise NoPickerAvailable("no folder picker found: install zenity or kdialog")
        result = subprocess.run(picker, capture_output=True, timeout=120)
        chosen = result.stdout.decode("utf-8", "replace").strip()
        return chosen or None


def browse_files():
    """Returns a list of chosen absolute .ris paths (empty if cancelled / no
    picker available)."""
    system = platform.system()
    if system == "Windows":
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
             "-File", str(BROWSE_FILES_SCRIPT)],
            capture_output=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        out = result.stdout.decode("utf-8", "replace").strip()
        return [line for line in out.splitlines() if line.strip()]
    elif system == "Darwin":
        script = (
            'set theFiles to choose file with multiple selections allowed of type {"ris"}\n'
            'set out to ""\n'
            'repeat with f in theFiles\n'
            'set out to out & POSIX path of f & linefeed\n'
            'end repeat\n'
            'return out'
        )
        result = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=120)
        out = result.stdout.decode("utf-8", "replace").strip()
        return [line for line in out.splitlines() if line.strip()]
    else:
        picker = None
        if shutil.which("zenity"):
            picker = ["zenity", "--file-selection", "--multiple",
                      "--file-filter=*.ris", "--separator=\n"]
        elif shutil.which("kdialog"):
            picker = ["kdialog", "--getopenfilenames", "--multiple"]
        if not picker:
            raise NoPickerAvailable("no file picker found: install zenity or kdialog")
        result = subprocess.run(picker, capture_output=True, timeout=120)
        out = result.stdout.decode("utf-8", "replace").strip()
        return [line for line in out.splitlines() if line.strip()]
