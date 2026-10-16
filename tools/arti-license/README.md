# arti-license

Client side of ARTi licensing (shipped). The Worker, D1 database and the maintainer tool `arti-admin`
live in a separate repo (`arti-services`, not shipped). Design: `memory/memories/licensing-update-plan.md`.

```
"~/.arti/python/python.exe" ~/.arti/tools/arti-license/cli.py <command>
```

| Command | What |
|---|---|
| `activate KEY` | Bind this machine to the key (machine hash is sent here, never at purchase) and write `~/.arti/license.json` |
| `status [--refresh]` | Show the local license; `--refresh` re-validates online first |
| `deactivate [--key KEY --machine HASH]` | Free this machine's seat, or another one with the key |
| `activations KEY` | List a key's seats |
| `install-file PATH` | Install a signed license file (site / offline) |
| `verify [--file PATH] [--now ISO]` | Offline check. Exit 0 valid or grace, 1 expired, 2 invalid |

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
  keep working). Never deletes anything.
- `ARTI_MACHINE_ID` overrides the platform id, for tests that simulate several machines.

`license.json` is per machine: git-ignored (`/license.json`) and absent from the NSIS `File` list and
`TrackedItems`, so neither a commit nor the installer can carry a maintainer's license.
