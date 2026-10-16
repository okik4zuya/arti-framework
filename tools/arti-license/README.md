# arti-license

Client side of ARTi licensing (shipped). The Worker, D1 database and the maintainer tool `arti-admin`
live in a separate repo (`arti-services`, not shipped). Design: `memory/memories/licensing-update-plan.md`.

```
"~/.arti/python/python.exe" ~/.arti/tools/arti-license/cli.py <command>
```

| Command | What |
|---|---|
| `activate KEY` | Bind this machine to the key (machine hash is sent here, never at purchase) and write `~/.arti/license.json`; also clears a revoked state |
| `status [--refresh]` | Show the local license; `--refresh` re-validates online first |
| `deactivate` | Free this machine's seat (authenticated by its own license file). A seat held by another computer is never freed from a client: support does it |
| `install-file PATH` | Install a signed license file (site / offline) |
| `verify [--file PATH] [--now ISO]` | Offline check. Exit 0 valid or grace, 1 expired, 2 invalid, missing or revoked |

Errors print `[code]` with a plain message: `seat_limit`, `key_revoked`, `expired`, `not_found`,
`not_entitled`, `rate_limited`, `bad_checksum`, `unreachable`.

## Files

- `pubkeys.json` - public keys only, `{"license": {kid: base64}, "release": {kid: base64}}`. The `dev-*`
  kids are **dev keys**; replace with production kids before any release.
- `config.json` - `api_base`. Placeholder until the Worker domain is decided; `ARTI_LICENSE_API` overrides it.
- Verification code is `tools/_shared/license.py` (key checksum, machine hash, canonical JSON, Ed25519
  verify, expiry/grace, `kid` lookup). Needs `cryptography` (pinned in `tools/requirements.txt`).

## Contract details that must match the Worker

- Key `ARTI-XXXX-XXXX-XXXX-XXXX`: Crockford base32, last char = checksum over the first 15 with odd
  weights `2i+1` mod 32. Catches every single-character typo and adjacent swaps, except two characters
  exactly 16 apart in the alphabet. `I`/`L` fold to `1`, `O` to `0`, after the `ARTI` prefix is stripped.
- Signed bytes = canonical JSON of `payload`: sorted keys, no whitespace, UTF-8 unescaped.
- `machine_hash` = sha256(`"arti-v1"` + MachineGuid / IOPlatformUUID / `/etc/machine-id`). A `site` license
  has `machine_hash: null` and verifies anywhere.
- States: `valid` until `expires`, `grace` for `grace_days` after, then `expired` (no updates; tools and data
  keep working). `revoked` = the server answered `key_revoked`; `license.json` is set aside as
  `license.revoked.json`. Never deletes anything.
- `evaluate()` judges the term from the later of the local clock and the signed `issued` time, so a clock set
  back is never trusted below the last server contact (`clock_behind` is reported when it is over a day).
- `ARTI_MACHINE_ID` overrides the platform id, for tests that simulate several machines.

`license.json` and `license.revoked.json` are per machine: git-ignored and absent from the NSIS `File` list and
`TrackedItems`, so neither a commit nor the installer can carry a maintainer's license.

## What happens when (buyer view and behind the scenes)

Only the **dashboard** is gated. "Skills and tools" below means every ARTi skill, every tool in `tools/` and
Claude Code in VS Code: none of them reads the license (only ARTi-setup may print a one-line notice from
`verify`, never a stop). The installers are the other gate, and fail closed on a fresh install.
`tests/licensing/` checks each row (`test_gate.py`, `test_edge.py`, `test_revoke.py`, `test_update.py`;
the Worker side is `arti-services/licensing-worker/tests/update_unit.mjs`).

| Event | What the buyer sees | Behind the scenes | Skills and tools |
|---|---|---|---|
| First install, good key, online | Install finishes, dashboard opens | Installer runs `activate`, Worker binds the machine hash, signed `license.json` written | Usable |
| Install with bad key (typo) | "That key has a typo" before any network call | Checksum fails locally, nothing is written, a fresh install is cleaned up | n/a |
| Install offline | "Cannot reach the licensing server", install stops | `activate` needs the Worker once, fresh install is cleaned up | n/a |
| Install, seat already used elsewhere | "This key is already active on another computer ..." | Worker answers `seat_limit` (409); fresh install is cleaned up. Deactivate on the old computer (Settings > License) or ask support | n/a |
| Dashboard start, license fine | Nothing | Offline check only (signature, machine, dates). Validated online only if nothing has confirmed the license for 3 days (+-1 h jitter; the update heartbeat counts as a confirmation), 4 s timeout, silent, at most one attempt per 6 h; a running dashboard re-evaluates every 12 h (no request unless due) | Usable |
| License ends within 30 days | Amber card "License ends in N days" | Offline date check | Usable |
| Expired, inside grace (14 d) | Amber card "License expired. Renew soon", hint "Already renewed? Press Refresh status" | Refresh attempted at every start | Usable |
| Expired past grace | Red card "Updates are off", dashboard still opens | Same refresh; the update check still answers, and a release dated on or before `updates_until` can still be installed (Update now); anything later is shown as "comes after the updates your license covers" | Usable, data untouched |
| Renewal (admin extends) | New date within 2 days (the update heartbeat carries the renewed license), or at once with **Refresh status** | The update answer includes a freshly signed license when the server's dates differ; `/validate` does the same on demand | Usable |
| Refresh before the renewal is processed | "This license has expired and is not renewed yet ..." | Worker `/validate` refuses with `expired`; local license unchanged | Usable |
| Revoked, machine online | At the next check (the update heartbeat every 2 days, or the 3-day validate, whichever comes first) the dashboard locks: red card "License revoked", License page explains, other Settings pages dimmed, API 403 `license_required` | `/validate` (or the daily update check) answers `key_revoked`; `license.json` moves to `license.revoked.json`; the key is not re-activated by itself | **Usable** |
| Revoked, machine offline | Nothing until it is next online | A revoke cannot be known offline | Usable |
| Revoke lifted by the admin | Press **Check again** on the License page: dashboard unlocks | `/validate` with the set-aside file succeeds, `license.json` restored | Usable |
| New key typed over a revoked license | Dashboard unlocks | `activate` writes `license.json` and removes `license.revoked.json` | Usable |
| No license (never activated, or deactivated) | Dashboard locked, License page with the key form | State `missing`; only `/api/license/*`, `/api/about`, ping are served | Usable |
| Seat full when activating | "This key is already active on another computer ... Deactivate it on that computer, or contact support to move it". No button or command to move it from here | Worker answers `seat_limit`; the client never lists or frees another computer's seat (the key may belong to someone else). Support moves it with `arti-admin deactivate` or the admin page (3 per key per year, admin may exceed) | Usable |
| Deactivating this computer too often (3/year) | "Self-service deactivation limit (3/year) reached; contact support" | Worker `rate_limited` (server text shown); license stays installed | Usable |
| Request burst | "Too many requests. Wait a minute and try again." | Worker `rate_limited` (20 per minute per IP) | Usable |
| Deactivate this computer | Dashboard locks, key can be used elsewhere | `/deactivate` frees the seat, then `license.json` is deleted | Usable |
| Worker unreachable (days or months) | Refresh says "Cannot reach the licensing server"; nothing else changes | Offline verdict stays authoritative; silent background failures; once expired the usual expired rules apply | Usable |
| Computer clock set back | Amber card "Computer clock looks wrong" | Term judged from `max(clock, signed issued)`; never a lock by itself | Usable |
| `license.json` damaged or edited | Locked, "could not be read / was changed. Activate again with your key" | Signature check fails; activating again on the same computer repairs it without a new seat | Usable |
| `~/.arti` copied to another computer | Locked, "This license belongs to another computer" | Machine hash differs (`wrong_machine`); the original computer is unaffected. Activate with the key (needs a free seat) | Usable |
| Signing key rotated | Nothing | Client trusts every `kid` in `pubkeys.json`; Worker accepts retired kids listed in `LICENSE_OLD_PUBKEYS`. Drop a kid from `pubkeys.json` only to lock out files signed with it | Usable |

## Request budget (Worker traffic, sized for 10,000 machines)

Per machine: one update heartbeat every 2 days (also the revoke and renewal signal) and a `/validate` only
when nothing has confirmed the license for 3 days, or in grace/expired, or on **Refresh status**; both with
+-1 h jitter and at most one attempt per 6 h. Worker side: `/validate`, `/update` and `/deactivate` are
authenticated by the signed license file and are not rate limited (a limiter row would be a D1 write per
request); `/activate`, `/activations` and `/ack` still are. `last_seen` is rewritten at most once a day, and
`validated` is no longer logged per call (state changes are the audit trail). About 5,000 requests and a few
thousand row writes per day at 10,000 machines, roughly 5% of the Cloudflare free limits.
