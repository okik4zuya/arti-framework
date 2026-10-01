# Updating ARTi Framework

There is no auto-update or in-app update check. Updating is a manual, three-step process:

1. Go to the [Releases page](https://github.com/okik4zuya/arti-framework/releases) and download
   the latest `ArtiFrameworkSetup-x.y.z.exe`.
2. Run it, same as a fresh install (Unblock the file first if Windows flags it as downloaded from
   the internet).
3. It installs over your existing `~/.arti` in place. You'll see a message like
   `Updating ARTi Framework v0.1.0 -> v0.2.0` during install, confirming what changed.

Your own content is never touched by an update: `memory/`, `voice-profiles/`, `workflow-sessions/`,
and `inbox/` are only created if missing, never overwritten or deleted. Everything else
(`tools/`, `skills/`, `dashboard/`, `logo/`, `installer/`, the docs) is replaced with the new
version's copy, including removing anything the new version deleted upstream.

If a new version changes a SQLite database's schema (`~/.arti/memory/arti.db` or a project's
`literature/arti-lit.db`), the migration runs automatically the next time that database is
opened — no manual step needed, and your existing rows are preserved.

## MCP servers (`.mcp.json`) need a manual step after adding/changing one

`.mcp.json` (which registers MCP servers like `arti-ref-search-mcp`) is part of
what gets replaced on update, same as `tools/`, `skills/`, etc. — so a new version's server
additions or config changes land automatically in `~/.arti` itself.

That only covers `~/.arti`. Reaching every other paper project without copying `.mcp.json` into
each one relies on registering the same server at Claude Code's **user scope** (stored in
`~/.claude.json`, not anything this installer touches or ever will — it's Claude Code's own live
app state, outside `~/.arti` entirely). The updater never runs this for you. If an update adds a
new MCP server, or you want an existing one reachable from your paper projects, re-run it by hand
once per server:

```
claude mcp add --scope user <name> -- "C:\Users\<you>\.arti\python\python.exe" <script-path>
```

(substitute the server's actual command/args from `.mcp.json`; an HTTP server uses
`--transport http <url>` instead). Use the **literal, resolved absolute path** here, not
`${ARTI_PYTHON:-python}` — env var expansion works fine in the project-scope `.mcp.json`, but a
`~/.claude.json` (user-scope) change like this needs a full Claude Code restart to take effect
regardless, and a freshly-set env var doesn't reliably reach an already-running process tree even
after that, so the literal path avoids stacking a second failure mode on top of the restart
requirement.

## ⚠️ Don't uninstall to update

The uninstaller (`Uninstall.exe`, or Windows' "Add or Remove Programs") deletes the **entire**
`~/.arti` folder, including `memory/`, `voice-profiles/`, and `workflow-sessions/` — i.e. it
deletes your researcher content, not just the app. Uninstalling and reinstalling is **not** the
update path and will lose your data. Always update by re-running the installer over your existing
install (steps above), never by uninstalling first.
