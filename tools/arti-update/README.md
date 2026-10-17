# arti-update

Updates for ARTi: find out whether a newer release exists, show what changed, record that the researcher read it, then download the release bundle and put it in place ("Update now"), or go back to the previous version.

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" check [--force]
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" status
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" ack 0.2.0
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" download 0.2.0
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" apply 0.2.0
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" rollback [0.1.8]
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" result [--clear]
```

The dashboard does the same through `dashboard/server/update_check.py`: a silent check at start (about every 2 days), a card in the sidebar when a release is available, and Settings > About with the notes, the list of changed skills/instructions, **I have read this**, **Update now** (progress bar, restart overlay, result banner) and **Roll back to vX**. User guide: `UPDATING.md`.

## Files

| File | Role |
|---|---|
| `cli.py` | Check, ack, download (resumable), preflight, spawn the updater, rollback, result. Also used in-process by the dashboard |
| `updater.py` | The part that changes files, as its own process. Copied by `cli.py` to `.update/run/` (with `bundle.py`, `license.py`, `paths.py`, `pubkeys.json`) so it is never one of the files it replaces |
| `bundle.py` | `UPDATE_ITEMS` and the zip rules (shared by the release builder, the client and the updater); stdlib only |

## Checking (phase 3a)

- `POST /v1/update` on the licensing server, authenticated by this machine's license file. The server returns the newest release this license may install (released on or before `updates_until`) and, if a newer one exists beyond that, only its version (`locked_newer`). An expired license may still ask.
- The release is a manifest **signed offline** with the release key. This client verifies it against `tools/arti-license/pubkeys.json` (`release` keys) and ignores anything unsigned, tampered, signed by an unknown key id, or not newer than the installed version (no downgrade offers). The signed document is kept in the state (`available_doc`) because the download and the updater verify it again.
- `requires_installer` (runtime changed) and `min_client_version` (installed version too old to apply) both show as "needs the full installer".
- The result is cached in `~/.arti/.update/state.json` (git-ignored). Offline or a server error never breaks the dashboard; the earlier finding is kept and the error is shown.
- The check runs about every 2 days (+-1 h jitter). It is also the license heartbeat: a success counts as a confirmation, and when the server's dates changed the answer carries the renewed signed license, which is installed. A `key_revoked` answer sets the license aside (see `tools/arti-license/README.md`).
- `ack` stores the read-receipt locally and tells the server (best effort; logged as `update_ack`). **"I have read this" is required before Update now.**

## Manifest (signed, canonical JSON)

`version`, `released` (ISO UTC), `channel` (`stable`|`beta`), `notes` (Markdown), `skills_changed`, `min_client_version`, `requires_installer`, `bundle` (`null` for an installer-only release, else `{sha256, size, r2_key, items}`), `packs` (data packs such as the Scimago snapshot; empty until a later phase), `download_page`. Published from the maintainer side with `arti-services/release/publish_release.py [--bundle ZIP]`. Channel: `stable` unless `ARTI_UPDATE_CHANNEL=beta`.

## Applying (phase 3b)

Preconditions (`cli.preflight`, shown as plain messages): the release is the pending one and its signature verifies; it has a bundle and is not `requires_installer`; the notes were acknowledged; the license is usable (not revoked or invalid) and covers the release date; the version is newer. In the CLI the dashboard must not be running.

1. **Download** `POST /v1/download` with the license file and the version (streamed from R2 by the Worker; 10 starts per day per key). Saved as `.update/download/arti-<v>.zip.part`, resumed with `Range` after a dropped connection (3 attempts), kept only if size and sha256 equal the signed manifest, else deleted.
2. **Hand over**: `cli.py` copies the updater to `.update/run/` and starts it detached (`--pid` of the dashboard, the command that starts the dashboard again, the health URL).
3. **Updater** (`updater.py`), in order: verify the manifest signature, zip size and sha256 again; check the zip (`bundle.validate`: no absolute paths, `..`, backslashes, drive letters or symlinks; only `UPDATE_ITEMS`; items equal to the signed list; `VERSION` equals the release; size cap); unpack to `.update/staging/` while the dashboard still runs; phase `waiting`: the dashboard sees it and exits (the updater kills it after 20 s if it does not); back up the replaced items to `.backup/<old>/` and `memory/arti.db` to `arti.db.bak` (SQLite backup API); swap each item with renames, directories first and `VERSION` last, with retries; if one rename fails (a locked file) everything already swapped is put back and the message says to close other ARTi windows and Claude Code sessions; recreate skill junctions (Windows `mklink /J`, otherwise symlinks) for new skills and remove dangling ones; run the smoke command (`cli.py status` of the new code, must exit 0), start the dashboard and wait up to 30 s for `/api/ping`.
4. **Automatic rollback**: if the smoke command or the health check fails, the new dashboard is stopped, the old items and `arti.db.bak` are put back, the old dashboard is started and `.update/result.json` says `{ok:false, reason:"unhealthy"}`. Success writes `{ok:true, from, to}`, prunes `.backup/` to the two newest versions and deletes the staging and download folders.
5. **Result**: the dashboard reads `result.json` once at the next start and shows a banner. `progress.json` carries the phase while it runs.

Never touched: `memory/`, `voice-profiles/`, `workflow-sessions/`, `inbox/`, `license.json`, `license.revoked.json`, `mcp-keys.json`, `python/`, `bin/` (none is an update item). `.claude.json` is never edited.

## Rollback

`cli.py rollback [VERSION]` (or **Roll back to vX** in Settings > About) moves the saved items from `.backup/<version>/` back (all or nothing), recreates skill links, starts the dashboard again and consumes that backup. It does **not** restore the database: schemas change additively only (see `memory/memories/release-checklist.md`), so older code runs on a newer database, and restoring would lose the work done since the update. The additive rule is enforced by `tests/licensing/test_schema_additive.py` (baseline `tests/licensing/schema_baseline.json`, regenerated after each published release). Data a researcher writes never lives under an `UPDATE_ITEMS` path: the Scimago snapshot in `tools/arti-jfinder/` is replaced on update, the scope cache is `memory/jfinder-scope.db`.

## Environment (tests only)

`ARTI_HOME` (data: `.update/`, `.backup/`, `memory/`, license), `ARTI_CODE_HOME` (the code tree that is swapped; defaults to the folder this file is in), `ARTI_LICENSE_API`. `tests/licensing/test_apply.py` runs the whole path against a throw-away tree with a fake Worker and stub dashboard, never against the real `~/.arti`.
