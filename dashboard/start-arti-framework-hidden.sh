#!/usr/bin/env bash
# ARTi Framework -- hidden launcher for macOS/Linux. This is what the Desktop
# icon (the .app on macOS, the .desktop file on Linux) actually runs. No
# terminal window ever appears.
#
# Liveness check first: if the dashboard server is already answering on
# 127.0.0.1:4174 (e.g. the researcher closed the browser tab earlier but
# never quit the server), skip spawning anything and just open a tab against
# it. Otherwise spawn it detached, wait briefly for /api/ping, then open the
# browser tab.
set -uo pipefail

ARTI_HOME="$HOME/.arti"
DASHBOARD_DIR="$ARTI_HOME/dashboard"
SERVER_DIR="$DASHBOARD_DIR/server"
LOG_PATH="$DASHBOARD_DIR/server.log"

PYTHON="$ARTI_HOME/python/bin/python3"
if [ ! -x "$PYTHON" ]; then
  PYTHON="$(command -v python3 || command -v python)"
fi

is_alive() {
  curl -sf --max-time 1 "http://127.0.0.1:4174/api/ping" >/dev/null 2>&1
}

open_url() {
  if command -v open >/dev/null 2>&1; then
    open "http://127.0.0.1:4174/"
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:4174/"
  fi
}

if ! is_alive; then
  rm -f "$LOG_PATH"
  ( cd "$SERVER_DIR" && nohup "$PYTHON" server.py > "$LOG_PATH" 2>&1 & disown )

  tries=0
  while ! is_alive && [ "$tries" -lt 40 ]; do
    sleep 0.25
    tries=$((tries + 1))
  done
fi

open_url
