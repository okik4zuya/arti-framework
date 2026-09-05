#!/usr/bin/env bash
# ARTi installer / updater (macOS)
#
# Sets up ~/.arti as the single cross-project home for ARTi tooling
# (vendored Python + tools/ + skills/) - never inside a Drive-synced folder.
# Re-running this script later is how you update: it re-syncs repo files,
# skips re-downloading Python if VERSION already matches, and re-copies
# skills into ~/.claude/skills.
#
# Does NOT touch researcher content (researcher-profile.md, voice-profiles/,
# workflow-sessions/, etc.) - that is created/populated by the ARTi-setup
# skill on first run, or by a one-time manual migration.
#
# Usage: unzip the repo, cd into it, then: bash install.sh
# NOTE: not run/tested on an actual Mac - reviewed for correctness only.

set -euo pipefail

# TODO: fill in once the GitHub repo exists, e.g. 'https://github.com/<you>/arti.git'.
# Until then this script operates purely on local files (safe no-op for the
# clone/pull step) - useful for bootstrapping ~/.arti from a local checkout.
REPO_URL=""

ARTI_HOME="$HOME/.arti"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TRACKED_ITEMS=(tools skills install.ps1 install.sh install.bat VERSION .gitignore)

echo "=== ARTi installer ==="
echo "Target: $ARTI_HOME"

# --- 1. sync tracked repo content into ~/.arti --------------------------------

mkdir -p "$ARTI_HOME"

if [ -n "$REPO_URL" ]; then
  if [ -d "$ARTI_HOME/.git" ]; then
    if command -v git >/dev/null 2>&1; then
      echo "Updating existing ~/.arti checkout (git pull)..."
      (cd "$ARTI_HOME" && git pull --ff-only)
    else
      echo "WARNING: git not found - cannot pull updates. Install git or re-run later." >&2
    fi
  elif command -v git >/dev/null 2>&1; then
    echo "Cloning $REPO_URL into ~/.arti..."
    git clone "$REPO_URL" "$ARTI_HOME"
  else
    echo "git not found - downloading zipball instead..."
    zip_url="${REPO_URL%.git}/archive/refs/heads/main.zip"
    tmp_zip="$(mktemp -t arti-repo.XXXXXX.zip)"
    curl -fsSL -o "$tmp_zip" "$zip_url"
    tmp_extract="$(mktemp -d -t arti-repo-extract.XXXXXX)"
    unzip -q "$tmp_zip" -d "$tmp_extract"
    src_root="$(find "$tmp_extract" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
    for item in "${TRACKED_ITEMS[@]}"; do
      if [ -e "$src_root/$item" ]; then
        cp -R "$src_root/$item" "$ARTI_HOME/"
      fi
    done
    rm -rf "$tmp_zip" "$tmp_extract"
  fi
elif [ -n "$SCRIPT_DIR" ] && [ "$SCRIPT_DIR" != "$ARTI_HOME" ]; then
  echo "No REPO_URL configured - syncing tracked files from local checkout ($SCRIPT_DIR)..."
  for item in "${TRACKED_ITEMS[@]}"; do
    if [ -e "$SCRIPT_DIR/$item" ]; then
      cp -R "$SCRIPT_DIR/$item" "$ARTI_HOME/"
    fi
  done
else
  echo "Running in place at ~/.arti with no REPO_URL configured - nothing to sync."
fi

# --- 2. researcher-content subfolders (created empty if missing, never overwritten) --

mkdir -p "$ARTI_HOME/voice-profiles" "$ARTI_HOME/workflow-sessions"

# --- 3. vendored Python (python-build-standalone) ------------------------------

VERSION_FILE="$ARTI_HOME/VERSION"
if [ ! -f "$VERSION_FILE" ]; then
  echo "ERROR: VERSION file missing at $VERSION_FILE - expected PYTHON_BUILD_TAG= and PYTHON_VERSION= lines." >&2
  exit 1
fi
PY_BUILD_TAG="$(grep '^PYTHON_BUILD_TAG=' "$VERSION_FILE" | cut -d= -f2 | tr -d '[:space:]')"
PY_VERSION="$(grep '^PYTHON_VERSION=' "$VERSION_FILE" | cut -d= -f2 | tr -d '[:space:]')"
if [ -z "$PY_BUILD_TAG" ] || [ -z "$PY_VERSION" ]; then
  echo "ERROR: VERSION file malformed at $VERSION_FILE." >&2
  exit 1
fi

PYTHON_DIR="$ARTI_HOME/python"
STAMP_FILE="$PYTHON_DIR/INSTALLED_VERSION"
NEED_PYTHON=1
if [ -f "$STAMP_FILE" ] && [ "$(cat "$STAMP_FILE")" = "$PY_BUILD_TAG/$PY_VERSION" ]; then
  NEED_PYTHON=0
fi

if [ "$NEED_PYTHON" -eq 1 ]; then
  echo "Fetching Python $PY_VERSION (build $PY_BUILD_TAG) via python-build-standalone..."
  arch="$(uname -m)"
  case "$arch" in
    arm64) pbs_arch="aarch64" ;;
    x86_64) pbs_arch="x86_64" ;;
    *) echo "ERROR: unsupported architecture: $arch" >&2; exit 1 ;;
  esac
  asset="cpython-${PY_VERSION}+${PY_BUILD_TAG}-${pbs_arch}-apple-darwin-install_only.tar.gz"
  url="https://github.com/astral-sh/python-build-standalone/releases/download/${PY_BUILD_TAG}/${asset}"
  tmp_tar="$(mktemp -t arti-python.XXXXXX.tar.gz)"
  curl -fsSL -o "$tmp_tar" "$url"

  rm -rf "$PYTHON_DIR"
  mkdir -p "$PYTHON_DIR"
  tmp_extract="$(mktemp -d -t arti-python-extract.XXXXXX)"
  tar -xzf "$tmp_tar" -C "$tmp_extract"
  # python-build-standalone's install_only archives extract to a top-level "python/" dir.
  cp -R "$tmp_extract/python/." "$PYTHON_DIR/"
  rm -rf "$tmp_extract" "$tmp_tar"

  echo "$PY_BUILD_TAG/$PY_VERSION" > "$STAMP_FILE"

  REQ_FILE="$ARTI_HOME/tools/requirements.txt"
  if [ -f "$REQ_FILE" ]; then
    "$PYTHON_DIR/bin/python3" -m pip install --quiet -r "$REQ_FILE"
  fi
  echo "  [ok] Python installed at $PYTHON_DIR"
else
  echo "  [ok] Python $PY_VERSION (build $PY_BUILD_TAG) already installed - skipping."
fi

# --- 4. wire skills into ~/.claude/skills --------------------------------------
# Symlinks, not copies: ~/.arti/skills/<name> is the only place a skill is ever edited.
# A symlink makes ~/.claude/skills/<name> resolve to the same directory, so there is no
# separate copy to fall out of sync and no re-run-the-installer step after an edit.

SKILLS_SRC="$ARTI_HOME/skills"
SKILLS_DST="$HOME/.claude/skills"
if [ -d "$SKILLS_SRC" ]; then
  mkdir -p "$SKILLS_DST"
  for d in "$SKILLS_SRC"/*/; do
    [ -d "$d" ] || continue
    name="$(basename "$d")"
    link="$SKILLS_DST/$name"
    if [ -L "$link" ] && [ "$(readlink "$link")" = "$d" ]; then
      echo "  [ok] skill already linked: $name"
      continue
    fi
    rm -rf "$link"
    if ln -s "${d%/}" "$link" 2>/dev/null; then
      echo "  [ok] skill linked: $name"
    else
      echo "  WARNING: symlink failed for $name - falling back to a copy." >&2
      cp -R "$d" "$SKILLS_DST/"
      echo "  [ok] skill copied (no live-edit link): $name"
    fi
  done
fi

# --- 5. summary -----------------------------------------------------------------

echo ""
echo "=== ARTi install complete ==="
echo "  Home:      $ARTI_HOME"
echo "  Python:    $PYTHON_DIR/bin/python3"
echo "  Skills:    $SKILLS_DST"
echo "  Re-run this script anytime to update."
