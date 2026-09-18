# ARTi Framework

A Claude Code workflow for taking a research paper from "I don't have an idea yet" to
"it's submitted" — eight skills, a set of export tools, and a local dashboard.

- **ARTi-setup** — one-time onboarding; scaffolds each new paper project
- **ARTi-idea** — gap map → idea canvas → novelty scoring → research design → journal target
- **ARTi-writing** — journal profile → blueprint → draft → review → cover letter → rebuttal
- **ARTi-figure** — study-design diagrams (`.drawio`) and manuscript tables from a JSON spec
- **ARTi-ref** — literature CRUD, fulltext ingestion, and paper-content retrieval against
  `arti-lit.db`
- **ARTi-scratchbook** — section-organized raw-material staging document writers fill before
  drafting
- **ARTi-jfinder** — ad-hoc journal lookup and ranking questions (SJR, quartile, aims & scope)
- **ARTi-crosscite** — cross-citation overlap check between two literature clusters

Everything installs into `~/.arti`, including a private, vendored Python 3.11 — nothing is
added to your PATH and no system Python is touched or required.

---

## Install

**Prerequisite:** [Claude Code](https://claude.com/claude-code) must already be installed.

### Windows

1. Download the ZIP: green **Code** button → **Download ZIP**.
2. Right-click the downloaded ZIP → **Properties** → tick **Unblock** → **OK**, then
   **Extract All…**. (Skipping Unblock is the single most common cause of a failed install —
   Windows blocks scripts that came from the internet.)
3. Open the extracted folder and double-click **`install.bat`**.
4. Wait for `=== ARTi install complete ===`, then press a key to close the window.

### macOS / Linux

```bash
cd ~/Downloads/arti-main     # wherever you extracted the ZIP
bash install.sh
```

On macOS the first launch of the new Desktop app may need **right-click → Open** once, because
it isn't code-signed.

### What the installer does

- Copies `skills/`, `tools/`, `dashboard/`, `logo/` and `CLAUDE.md` into `~/.arti`
- Downloads a private Python 3.11 into `~/.arti/python` (~25 MB — the slow step) and installs
  `tools/requirements.txt` into it
- Links each skill into `~/.claude/skills/` so Claude Code picks it up
- Seeds empty `memory/` and `inbox/` index files **only if they don't already exist**
- Creates an **ARTi Framework** icon on your Desktop that opens the dashboard

It never overwrites your own content. Re-running it is also how you **update** — see
[UPDATING.md](UPDATING.md) for the full procedure and an important caution about the
uninstaller. In short: it re-syncs the repo files, skips the Python download if `VERSION` is
unchanged, and leaves `memory/`, `inbox/`, `voice-profiles/` and `workflow-sessions/` untouched.

### Optional extras

The installer needs none of these, and every tool degrades cleanly without them:

| For | Install | Without it |
|---|---|---|
| PNG export of figures | [draw.io desktop](https://www.drawio.com/) | You still get the editable `.drawio` file — open and export it by hand. |
| PDF export (`arti-pdf`) | Microsoft Edge or Google Chrome | Already present on any stock Windows 10/11. Needed only for frozen A4 PDFs. |
| VS Code launch from the dashboard | [VS Code](https://code.visualstudio.com/) on your PATH | The dashboard still creates the project folder; open it yourself. |

---

## First run

1. Double-click the **ARTi Framework** Desktop icon. The dashboard opens at
   <http://127.0.0.1:4174/>.
2. Create a project folder there, or point the dashboard at an existing one, and open it in
   VS Code.
3. In that folder, tell Claude: **"set up ARTi"**. `ARTi-setup` builds your Researcher Profile
   in `~/.arti/memory/` and scaffolds the project. From then on, "help me find a research gap"
   or "let's draft the introduction" routes to the right skill on its own.

You never have to run the tools in `tools/` by hand — the skills invoke them.

---

## Verifying an install

```
~/.arti/python/python.exe -V          # Windows      -> Python 3.11.10
~/.arti/python/bin/python3 -V         # macOS/Linux  -> Python 3.11.10
```

and in Claude Code, `/skills` should list `ARTi-setup`, `ARTi-idea`, `ARTi-writing`,
`ARTi-figure`, `ARTi-ref`, `ARTi-scratchbook`, `ARTi-jfinder`, `ARTi-crosscite`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| PowerShell window flashes and closes | Run `install.bat`, not `install.ps1` — the `.bat` sets the execution policy and pauses on exit. |
| `install.ps1 is not digitally signed` | You skipped step 2. Right-click the **ZIP** → Properties → Unblock, then re-extract. |
| Python download fails | A proxy or firewall is blocking `github.com`. Fix the connection and re-run the installer; nothing else has to be undone. |
| `pip install failed` warning | Harmless unless you need `.docx` export. Re-run the installer when you're back online. |
| Skills don't appear in Claude Code | Restart Claude Code, then check `~/.claude/skills/` contains the eight `ARTi-*` entries. |
| Desktop icon does nothing | Check `~/.arti/dashboard/server.log` — the launcher writes any traceback there. |
| `tar.exe not found` (Windows) | Needs Windows 10 build 1803 or later. |

## Uninstall

Delete `~/.arti`, the eight `ARTi-*` entries in `~/.claude/skills/`, and the Desktop icon.
Your paper project folders are separate and are not touched.

## Platform support

- **Windows** is the only fully supported, tested platform: the NSIS installer (`.exe`) and
  `install.ps1` are what this README's install steps use.
- **macOS**: `install.sh` is reviewed for correctness but has not been run/tested on an actual
  Mac. Use at your own risk; file an issue if something breaks.
- **Linux**: `install.sh`'s Python vendoring currently downloads the macOS
  (`-apple-darwin-`) build by mistake and does not work. Not fixed yet — Windows is the
  supported path for now.

## Layout

```
~/.arti/
  skills/     the eight ARTi-* skills (linked into ~/.claude/skills/)
  tools/      arti-render, arti-docx, arti-pdf, arti-table, arti-memcheck, ...
  dashboard/  local launcher (127.0.0.1:4174)
  python/     vendored Python 3.11 - downloaded by the installer, never tracked
  memory/     your profile, idea bank, project index  (yours; never in git)
  inbox/      raw-idea inbox                            (yours; never in git)
```
