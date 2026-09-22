"""Entry point for the Explorer "Register as ARTi Project" context-menu verb
(installer/arti-installer.nsi writes the HKCU\\...\\Directory\\shell and
Directory\\Background\\shell keys that invoke this with pythonw.exe, so there
is never a console window -- all feedback goes through MessageBoxW).

Usage: register_project_cli.py <folder-path>
"""
import ctypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import db  # noqa: E402  (path must be set up first)

MB_OK = 0x0
MB_YESNO = 0x4
MB_ICONERROR = 0x10
MB_ICONINFORMATION = 0x40
MB_ICONQUESTION = 0x20
IDYES = 6


def _message_box(text, title, flags):
    return ctypes.windll.user32.MessageBoxW(0, text, title, flags)


def main():
    if len(sys.argv) < 2:
        _message_box("No folder path was passed to register_project_cli.py.",
                      "ARTi", MB_OK | MB_ICONERROR)
        return 1

    folder_path = Path(sys.argv[1])
    if not folder_path.is_dir():
        _message_box(f"'{folder_path}' does not exist or is not a folder.",
                      "ARTi", MB_OK | MB_ICONERROR)
        return 1

    existing = db.find_project(folder_path)
    if existing is None:
        entry = db.upsert_project(folder_path, name=folder_path.name, category="Other",
                                   tags=[], touch_opened=True)
        _message_box(f"Registered '{entry['name']}' as an ARTi project.",
                      "ARTi", MB_OK | MB_ICONINFORMATION)
        return 0

    choice = _message_box(
        f"'{folder_path.name}' is already registered as '{existing['name']}' "
        f"(category: {existing['category']}).\n\n"
        "Update its last-opened time and keep it registered?",
        "ARTi", MB_YESNO | MB_ICONQUESTION,
    )
    if choice == IDYES:
        db.upsert_project(folder_path, touch_opened=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
