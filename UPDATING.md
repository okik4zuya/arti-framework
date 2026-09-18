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

## ⚠️ Don't uninstall to update

The uninstaller (`Uninstall.exe`, or Windows' "Add or Remove Programs") deletes the **entire**
`~/.arti` folder, including `memory/`, `voice-profiles/`, and `workflow-sessions/` — i.e. it
deletes your researcher content, not just the app. Uninstalling and reinstalling is **not** the
update path and will lose your data. Always update by re-running the installer over your existing
install (steps above), never by uninstalling first.
