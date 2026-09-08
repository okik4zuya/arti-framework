#!/usr/bin/env bash
# Manual/debug entry point (visible/foreground). The Desktop icon does NOT use
# this script -- it uses the hidden launcher (see README.md for the per-OS
# hidden-launch mechanism).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PYTHON="$HOME/.arti/python/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

URL="http://127.0.0.1:4174/"
if command -v open >/dev/null 2>&1; then
  open "$URL"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL"
fi

cd "$DIR/server"
exec "$PYTHON" server.py
