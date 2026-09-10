# ARTi Framework dashboard

This is ARTi's own dashboard — patterned after `.jamrud` (routing skeleton, folder-picker
approach, focus-steal-on-launch on Windows) but not a fork of it: separate runtime, separate
code, and zero runtime data coupling — nothing here ever reads `.jamrud`'s `registry.json` or any
other `.jamrud` file.

One job: **Launcher**. Create a new project folder or point at an existing one, and open it in
VS Code with one click — the researcher then talks to Claude in that folder ("set up this
project") and `ARTi-setup` does the scaffolding. The dashboard never drops starter files itself.

The dashboard used to also carry a read-only "visibility" layer over `memory/project-index.md`
(paper pipeline) and `memory/research-idea-bank.md` (parked research ideas). That layer was
Claude-in-loop — only as fresh as whichever skill last remembered to upsert those files — and was
removed. The project registry is now `project_index`, a table in `~/.arti/memory/arti.db` shared
with `tools/arti-db/` — see `server/db.py`, which reads/writes it directly (aliasing its
`topic`/`project_path` columns to the `name`/`path` keys the dashboard UI expects) rather than
keeping a separate database.

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

- **Windows**: the Desktop icon launches `app.py`, which hosts the HTTP server (background thread)
  and a native pywebview window in one process — no browser tab, no separate server process.
  Clicking the icon again is safe: `app.py` tries to bind port 4174 first, and if that fails
  (another instance already owns it) it POSTs `/api/focus` to bring the existing window forward and
  exits instead of opening a second window. Closing the window (native X button) stops the HTTP
  server and exits the process — no orphaned background process to hunt down.
- **mac/linux**: still the browser-tab model — closing the tab never stops the server, they're
  independent processes; `start-arti-dashboard.sh` is the manual/foreground entry point. (pywebview
  wrapping is Windows-only for now — see `memory/memories/dashboard-build.md`.)
- **Quit Dashboard** in the page footer (`POST /api/shutdown`, with a confirm step) still works on
  every platform as an explicit stop, in addition to the native window's X button on Windows.
- A fresh spawn truncates `server.log`; a reused-server relaunch never touches it, so a traceback
  is always inspectable there without ever needing a console window.

## Files

```
arti-dashboard.html            adapted from .jamrud's workstation.html shell/CSS, new panels
app.py                         Windows — native entry point: HTTP server + pywebview window, one process
start-arti-dashboard.bat       Windows, visible console — manual/debug entry point (launches app.py)
start-arti-framework.vbs       superseded by app.py — kept for reference, no longer wired to any shortcut
start-arti-dashboard.sh        mac/linux, visible/foreground — manual/debug entry point
server/
  server.py                    stdlib http.server
  db.py                        View over `project_index` (memory/arti.db, shared with tools/arti-db/)
  platform_ops.py              per-OS: browse_folder / open_in_vscode / open_in_file_manager
  browse-folder.ps1            Windows native folder picker
  launch-focused.ps1           Windows focus-stealing VS Code/Explorer launch
```
