# ARTi Framework

A Claude Code workflow for taking a research paper from "I don't have an idea yet" to
"it's submitted" — eleven skills, a set of export tools, and a local dashboard.

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
- **ARTi-demo** — one command, one question (the topic), then an unattended tour: search, screening, full texts, figures, a Word manuscript with Zotero citations and a scoreboard
- **ARTi-annotate** — resolve the inline comments and suggested edits you made in the dashboard md preview
- **ARTi-SLR** — PRISMA systematic literature review, from research question to synthesis

Everything installs into `~/.arti`, including a private, vendored Python 3.11 — nothing is
added to your PATH and no system Python is touched or required.

---

## Install

ARTi Framework is a paid product. After purchase you get a **license key** (`ARTI-XXXX-XXXX-XXXX-XXXX`)
and a private download link for the installer. A key works on one machine at a time; installing needs an
internet connection once, to activate it.

**Prerequisite:** [Claude Code](https://claude.com/claude-code) must already be installed.

### Windows

1. Download `ArtiFrameworkSetup-x.y.z.exe` from your private link. Windows SmartScreen may warn that the
   publisher is unknown (the installer is not code-signed): **More info** -> **Run anyway**.
2. Run it and enter your license key when asked. It activates this machine online, then installs.
3. Wait for the finish page, then tick **Launch ARTi dashboard** or use the **ARTi Framework** Desktop icon.

### macOS / Linux

```bash
tar -xzf arti-framework-x.y.z.tar.gz -C ~/Downloads/arti-framework && cd ~/Downloads/arti-framework
bash install.sh
```

On macOS the first launch of the new Desktop app may need **right-click -> Open** once, because
it isn't code-signed.

### What the installer does

- Copies `skills/`, `tools/`, `dashboard/`, `logo/` and the docs into `~/.arti`
- Downloads a private Python 3.11 into `~/.arti/python` (~25 MB - the slow step) and installs
  `tools/requirements.txt` into it
- Links each skill into `~/.claude/skills/` so Claude Code picks it up
- Seeds empty `memory/` and `inbox/idea-index.md` files **only if they don't already exist**
- Creates an **ARTi Framework** icon on your Desktop that opens the dashboard

It never overwrites your own content. Updating means running a newer installer over the existing
install - see [UPDATING.md](UPDATING.md) for the procedure and an important caution about the
uninstaller. If your license expires, your data and every tool keep working; you only stop receiving updates.
The dashboard needs an active license to open, while the skills and tools in Claude Code do not.

### Optional extras

The installer needs none of these, and every tool degrades cleanly without them:

| For | Install | Without it |
|---|---|---|
| PNG export of figures | [draw.io desktop](https://www.drawio.com/) | You still get the editable `.drawio` file — open and export it by hand. |
| PDF export (`arti-convert pdf`) | Microsoft Edge or Google Chrome | Already present on any stock Windows 10/11. Needed only for frozen A4 PDFs. |
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
`ARTi-figure`, `ARTi-ref`, `ARTi-scratchbook`, `ARTi-jfinder`, `ARTi-crosscite`, `ARTi-annotate`, `ARTi-SLR`, `ARTi-demo`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Activation fails with `seat_limit` | The key is already active on another machine. Free it there (`arti-license deactivate`) or contact support. |
| Activation fails with `unreachable` | No internet, or a firewall blocks `lisensi.arti.ai.id`. Fix the connection and run the installer again. |
| Python download fails | A proxy or firewall is blocking `github.com` (the Python build is downloaded from there). Fix the connection and re-run the installer; nothing else has to be undone. |
| `pip install failed` warning | Harmless unless you need `.docx` export. Re-run the installer when you're back online. |
| Skills don't appear in Claude Code | Restart Claude Code, then check `~/.claude/skills/` contains the ten `ARTi-*` entries. |
| Desktop icon does nothing | Check `~/.arti/dashboard/server.log` — the launcher writes any traceback there. |
| `tar.exe not found` (Windows) | Needs Windows 10 build 1803 or later. |

## Uninstall

Delete `~/.arti`, the ten `ARTi-*` entries in `~/.claude/skills/`, and the Desktop icon.
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
  skills/     the ten ARTi-* skills (linked into ~/.claude/skills/)
  tools/      arti-lit, arti-render, arti-docx, arti-convert, arti-memcheck, arti-search, ...
  CAPABILITIES.md  one-line map of every skill, tool and MCP server
  dashboard/  local launcher (127.0.0.1:4174)
  python/     vendored Python 3.11 - downloaded by the installer, never tracked
  memory/     your profile, idea bank, project index  (yours; never in git)
  inbox/      idea-index.md only (raw-idea inbox retired) (yours; never in git)
```
