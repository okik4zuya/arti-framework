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
SAVE_FILE_SCRIPT = SCRIPT_DIR / "browse-save-file.ps1"
LAUNCH_SCRIPT = SCRIPT_DIR / "launch-focused.ps1"
COPY_FILES_SCRIPT = SCRIPT_DIR / "copy-files-to-clipboard.ps1"


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


def open_file_default(path):
    """Launches path in its OS-default application -- the same as
    double-clicking it in a file manager."""
    system = platform.system()
    path = str(path)
    if system == "Windows":
        # Start-Process resolves a data-file path via ShellExecute, same as
        # explorer.exe would on double-click -- no need for a real .exe here.
        _run_powershell_focused(path, [])
    elif system == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def reveal_file_in_file_manager(path):
    """Opens path's containing folder with the file itself selected/highlighted
    -- the Files panel's three-dot "Open file location" action. Linux has no
    universal select-and-highlight command, so it falls back to just opening
    the parent folder (same graceful-degradation precedent as
    open_file_with_dialog())."""
    system = platform.system()
    path = str(path)
    if system == "Windows":
        # "/select," and the path must be two separate arguments, not one
        # combined string. launch-focused.ps1 only quotes an argument that
        # contains whitespace, so a combined "/select,C:\path with
        # spaces\file.txt" token gets its *entire* text (including the
        # "/select," prefix) wrapped in one pair of quotes -- a form
        # explorer.exe fails to parse, silently falling back to the default
        # Documents view instead of erroring. Kept separate, only the path
        # element gets quoted, producing the standard working form
        # `/select, "C:\path with spaces\file.txt"` (same two-argument
        # pattern as .NET's ProcessStartInfo.ArgumentList.Add convention).
        _run_powershell_focused("explorer.exe", ["/select,", path])
    elif system == "Darwin":
        subprocess.Popen(["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", str(Path(path).parent)])


def open_file_with_dialog(path):
    """Shows the OS's native "Open with..." application chooser for path.
    macOS/Linux have no equivalent single command for this, so they fall back
    to the default-app open instead (same graceful-degradation precedent as
    browse_folder()'s Linux picker fallback)."""
    system = platform.system()
    path = str(path)
    if system == "Windows":
        # shell32.dll's OpenAs_RunDLL entry point is the same one Explorer's
        # own "Open with" context-menu item calls.
        _run_powershell_focused("rundll32.exe", ["shell32.dll,OpenAs_RunDLL", path])
    else:
        open_file_default(path)


def copy_files_to_clipboard(paths):
    """Puts one or more absolute file paths onto the OS clipboard as real
    files (CF_HDROP), not a text path string -- what a paste into Explorer,
    WhatsApp Desktop, email clients, etc. expects. Windows only: macOS/Linux
    have no single cross-app-compatible equivalent (pbcopy/xclip only put
    text on the clipboard), so this raises NotImplementedError there rather
    than silently copying the wrong thing."""
    if platform.system() != "Windows":
        raise NotImplementedError("Copying files to the clipboard is only supported on Windows")
    payload_b64 = base64.b64encode(json.dumps(list(paths)).encode("utf-8")).decode("ascii")
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
         "-File", str(COPY_FILES_SCRIPT), "-PayloadB64", payload_b64],
        capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW,
    )


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


def save_file(initial_dir=None, default_name="message.md"):
    """Shows a native Save-As dialog (folder navigation + new-folder button +
    filename entry all built in) and returns the chosen absolute path, or
    None if cancelled / no picker available."""
    system = platform.system()
    if system == "Windows":
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
             "-File", str(SAVE_FILE_SCRIPT), "-InitialDir", initial_dir or "", "-DefaultName", default_name],
            capture_output=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW,
        )
        chosen = result.stdout.decode("utf-8", "replace").strip()
        return chosen or None
    elif system == "Darwin":
        loc_clause = f'default location POSIX file "{initial_dir}"' if initial_dir else ""
        script = (
            f'set theFile to choose file name with prompt "Save as" default name "{default_name}" {loc_clause}\n'
            'return POSIX path of theFile'
        )
        result = subprocess.run(["osascript", "-e", script], capture_output=True, timeout=120)
        chosen = result.stdout.decode("utf-8", "replace").strip()
        return chosen or None
    else:
        suggested = str(Path(initial_dir or Path.home()) / default_name)
        picker = None
        if shutil.which("zenity"):
            picker = ["zenity", "--file-selection", "--save", "--confirm-overwrite", "--filename", suggested]
        elif shutil.which("kdialog"):
            picker = ["kdialog", "--getsavefilename", suggested]
        if not picker:
            raise NoPickerAvailable("no save-file picker found: install zenity or kdialog")
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
