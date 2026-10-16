# Updating ARTi Framework

The dashboard looks for a newer version about every two days and shows a card in the sidebar when one is available. **Settings > About** has the release notes, including the skills and instructions that changed (they change how Claude behaves in your projects, so read them). ARTi never updates by itself: you decide when.

Updates are available while your license is active. An expired license keeps everything you already have working and can still install the version it was entitled to, but it does not unlock newer ones.

## Update inside ARTi (most releases)

1. Open **Settings > About** and read the notes, then press **I have read this**.
2. Press **Update now**. ARTi downloads the release (the file is checked against the signed release information), unpacks it, closes itself, replaces its skills, tools and dashboard, and opens again by itself. This takes about a minute.
3. A message at the top of the Updates section tells you what happened.

What it does for safety:

- The previous version is kept under `~/.arti/.backup/<version>/` (the last two are kept), together with a copy of `memory/arti.db`.
- If the new version does not start correctly, ARTi puts the old code and the old database back by itself, opens the old version again and tells you why the update was cancelled.
- If some ARTi files are in use (another ARTi window, or a Claude Code session using an ARTi tool), nothing is changed and you are asked to close them and try again.
- Your own content is never touched: `memory/`, `voice-profiles/`, `workflow-sessions/`, `inbox/`, `license.json` and `mcp-keys.json` are not part of an update.

### Go back to the previous version

After an update, Settings > About shows **Roll back to vX.Y.Z**. It puts the earlier skills, tools and dashboard back and restarts ARTi. Your data is not changed (the database is only restored automatically when an update fails, because rolling back by hand would throw away what you did after updating; releases only ever add to the database schema, so older code keeps working on a newer database).

### From Claude Code (no dashboard)

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" check --force
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" ack 0.2.0
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" apply 0.2.0
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" rollback
```

Close the ARTi window first; `apply` refuses while it answers. Claude Code sessions that already loaded the old skills keep them until you start a new session.

## Update with the installer (when a release needs it)

A release that changes the runtime (Python, poppler, tesseract), or one that is too old to be applied in place, says so in Settings > About ("needs the full installer"). The very first release that has **Update now** also has to be installed this way once, because older installs do not have the updater yet.

1. Download the latest installer (`ArtiFrameworkSetup-x.y.z.exe`, or the archive on macOS/Linux) from your private download link.
2. Run it, same as a fresh install (SmartScreen may warn about an unknown publisher: **More info** -> **Run anyway**). Your license is already activated on this machine, so it is not asked for again.
3. It installs over your existing `~/.arti` in place. You'll see a message like `Updating ARTi Framework v0.1.0 -> v0.2.0` during install.

Everything that is not your own content (`tools/`, `skills/`, `dashboard/`, `logo/`, the docs) is replaced with the new version's copy, including removing anything the new version deleted upstream.

## Database changes

If a new version changes a SQLite database's schema (`~/.arti/memory/arti.db` or a project's `literature/arti-lit.db`), the migration runs automatically the next time that database is opened, and your rows are preserved. Migrations are always additive (new tables or columns, never removals or renames), so a rollback to the previous version still works on the migrated database.

## MCP servers (`.mcp.json`) need a manual step after adding/changing one

`.mcp.json` (which registers MCP servers like `arti-ref-search-mcp`) is part of what gets replaced on update (it holds no API keys; those live in `mcp-keys.json`, which updates never touch), same as `tools/`, `skills/`, etc. — so a new version's server additions or config changes land automatically in `~/.arti` itself.

That only covers `~/.arti`. Reaching every other paper project without copying `.mcp.json` into each one relies on registering the same server at Claude Code's **user scope** (stored in `~/.claude.json`, not anything the installer or the updater touches or ever will — it's Claude Code's own live app state, outside `~/.arti` entirely). If an update adds a new MCP server, or you want an existing one reachable from your paper projects, run it by hand once per server:

```
claude mcp add --scope user <name> -- "C:\Users\<you>\.arti\python\python.exe" <script-path>
```

(substitute the server's actual command/args from `.mcp.json`; an HTTP server uses `--transport http <url>` instead). Use the **literal, resolved absolute path** here, not `${ARTI_PYTHON:-python}` — env var expansion works fine in the project-scope `.mcp.json`, but a `~/.claude.json` (user-scope) change like this needs a full Claude Code restart to take effect regardless, and a freshly-set env var doesn't reliably reach an already-running process tree even after that, so the literal path avoids stacking a second failure mode on top of the restart requirement.

## ⚠️ Don't uninstall to update

The uninstaller (`Uninstall.exe`, or Windows' "Add or Remove Programs") deletes the **entire** `~/.arti` folder, including `memory/`, `voice-profiles/`, and `workflow-sessions/` — i.e. it deletes your researcher content, not just the app. Uninstalling and reinstalling is **not** the update path and will lose your data. Update with **Update now**, or by re-running the installer over your existing install, never by uninstalling first.
