# arti-update

Update check for ARTi (phase 3a). It finds out whether a newer release exists, shows what changed, and
records that the researcher read it. It does **not** download or apply anything yet: updating is still
"run the newer installer over your install" (see `UPDATING.md`); one-click apply is phase 3b.

```
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" check [--force]
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" status
"~/.arti/python/python.exe" "~/.arti/tools/arti-update/cli.py" ack 0.2.0
```

The dashboard does the same through `dashboard/server/update_check.py`: a silent check at start (at most
once a day), a card in the sidebar when a release is available, and Settings > About with the notes, the
list of changed skills/instructions and an "I have read this" button.

## How it works

- `POST /v1/update` on the licensing server, authenticated by this machine's license file. The server
  returns the newest release this license may install (released on or before `updates_until`) and, if a
  newer one exists beyond that, only its version (`locked_newer`). An expired license may still ask.
- The release is a manifest **signed offline** with the release key. This client verifies it against
  `tools/arti-license/pubkeys.json` (`release` keys) and ignores anything unsigned, tampered, signed by an
  unknown key id, or not newer than the installed version (no downgrade offers).
- `requires_installer` (runtime changed) and `min_client_version` (installed version too old to apply) both
  show as "needs the full installer".
- The result is cached in `~/.arti/.update/state.json` (git-ignored). Offline or a server error never
  breaks the dashboard; the earlier finding is kept and the error is shown.
- `ack` stores the read-receipt locally and tells the server (best effort; logged as `update_ack`).

## Manifest (signed, canonical JSON)

`version`, `released` (ISO UTC), `channel` (`stable`|`beta`), `notes` (Markdown), `skills_changed` (list of
one-liners), `min_client_version`, `requires_installer`, `bundle` (`null` until phase 3b: `{sha256, size,
r2_key}`), `packs` (data packs such as the Scimago snapshot, versioned separately from the code; empty
until 3b), `download_page`. Published from the maintainer side with `arti-services/release/publish_release.py`.

Channel: `stable` unless `ARTI_UPDATE_CHANNEL=beta`.
