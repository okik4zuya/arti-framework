# ARTi Framework dashboard

This is ARTi's own dashboard — patterned after `.jamrud` (routing skeleton, folder-picker
approach, focus-steal-on-launch on Windows) but not a fork of it: separate runtime, separate
code, and zero runtime data coupling — nothing here ever reads `.jamrud`'s `registry.json` or any
other `.jamrud` file.

Two jobs:

1. **Launcher** (primary): create a new project folder or point at an existing one, and open it
   in VS Code with one click — the researcher then talks to Claude in that folder ("set up this
   project") and `ARTi-setup` does the scaffolding. The dashboard never drops starter files itself.
2. **Visibility**: read-only panels over `memory/progress-index.md` (paper pipeline) and
   `memory/research-idea-bank.md` (parked research ideas), parsed fresh from disk on every
   request — no cache, no database, nothing here can drift from those files.

Runs on `127.0.0.1:4174` (`.jamrud` owns `4173`) via the vendored `~/.arti/python` interpreter —
plain stdlib `http.server`, no Flask/FastAPI, no pip dependencies.

## Platforms

- **VS Code launch is uniform**: the `code` CLI is on PATH after the standard VS Code installer
  on Windows, macOS, and Linux alike, so `platform_ops.open_in_vscode` needs no per-OS branching
  for the launch itself (Windows additionally uses a focus-steal script, a `.jamrud` nicety).
- **Folder browsing and the Desktop icon are native per OS** — Windows uses
  `System.Windows.Forms.FolderBrowserDialog`, macOS uses `osascript`, Linux uses `zenity` (falling
  back to `kdialog`).
- **Linux** depends on `zenity` or `kdialog` being installed for the folder picker — if neither is
  present, `/api/browse-folder` returns an error and the page falls back to a plain text input for
  pasting the path. Linux also currently runs on whatever `python3`/`python` is on PATH, since
  `install.sh` only vendors a `python-build-standalone` build for macOS today — not yet a vendored
  Linux interpreter (a pre-existing gap, tracked separately).

## What running means

- Closing the browser tab never stops the server — they're independent processes. Clicking the
  Desktop icon again is always safe: it checks `/api/ping` first and reuses the already-running
  server rather than erroring or double-spawning on the bound port.
- **Quit Dashboard** in the page footer (`POST /api/shutdown`, with a confirm step) is the one
  clean, discoverable way to stop the process. Without clicking it, the server just stays alive in
  the background — an idle stdlib HTTP server costs effectively nothing — until logout/reboot.
- A fresh spawn truncates `server.log`; a reused-server relaunch never touches it, so a traceback
  is always inspectable there without ever needing a console window.

## Files

```
arti-dashboard.html            adapted from .jamrud's workstation.html shell/CSS, new panels
start-arti-dashboard.bat       Windows, visible console — manual/debug entry point
start-arti-framework.vbs       Windows, hidden — what the Desktop icon actually runs
start-arti-dashboard.sh        mac/linux, visible/foreground — manual/debug entry point
server/
  server.py                    stdlib http.server; no db.py — nothing to persist
  platform_ops.py              per-OS: browse_folder / open_in_vscode / open_in_file_manager
  browse-folder.ps1            Windows native folder picker
  launch-focused.ps1           Windows focus-stealing VS Code/Explorer launch
```
