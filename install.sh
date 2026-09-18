#!/usr/bin/env bash
# ARTi installer / updater (macOS + Linux)
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
TRACKED_ITEMS=(tools skills dashboard logo installer CLAUDE.md README.md UPDATING.md prompt-templates.md install.ps1 install.sh install.bat VERSION .gitignore)

# Copy one tracked item into $ARTI_HOME under its own name.
#
# `cp -R src/tools "$ARTI_HOME/"` when $ARTI_HOME/tools ALREADY exists nests the
# source inside it ($ARTI_HOME/tools/tools) instead of merging, so every re-run of
# this installer would bury the tree a level deeper. Clearing the destination first
# fixes that and additionally drops files deleted upstream, which a merge would
# leave behind forever.
copy_tracked_item() {
  local src="$1" dest="$2"
  if [ -d "$src" ]; then
    rm -rf "$dest"
  fi
  cp -R "$src" "$dest"
}

echo "=== ARTi installer ==="
echo "Target: $ARTI_HOME"

# Read the framework version already installed (if any) before it gets overwritten below,
# so we can tell the user whether this run is a fresh install or an update, and to what.
OLD_VERSION_FILE="$ARTI_HOME/VERSION"
OLD_FRAMEWORK_VERSION=""
if [ -f "$OLD_VERSION_FILE" ]; then
  OLD_FRAMEWORK_VERSION="$(grep '^FRAMEWORK_VERSION=' "$OLD_VERSION_FILE" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')"
fi

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
        copy_tracked_item "$src_root/$item" "$ARTI_HOME/$item"
      fi
    done
    rm -rf "$tmp_zip" "$tmp_extract"
  fi
elif [ -n "$SCRIPT_DIR" ] && [ "$SCRIPT_DIR" != "$ARTI_HOME" ]; then
  echo "No REPO_URL configured - syncing tracked files from local checkout ($SCRIPT_DIR)..."
  for item in "${TRACKED_ITEMS[@]}"; do
    if [ -e "$SCRIPT_DIR/$item" ]; then
      copy_tracked_item "$SCRIPT_DIR/$item" "$ARTI_HOME/$item"
    fi
  done
else
  echo "Running in place at ~/.arti with no REPO_URL configured - nothing to sync."
fi

NEW_FRAMEWORK_VERSION=""
if [ -f "$OLD_VERSION_FILE" ]; then
  NEW_FRAMEWORK_VERSION="$(grep '^FRAMEWORK_VERSION=' "$OLD_VERSION_FILE" 2>/dev/null | cut -d= -f2 | tr -d '[:space:]')"
fi
if [ -n "$NEW_FRAMEWORK_VERSION" ]; then
  if [ -n "$OLD_FRAMEWORK_VERSION" ] && [ "$OLD_FRAMEWORK_VERSION" != "$NEW_FRAMEWORK_VERSION" ]; then
    echo "Updating ARTi Framework v$OLD_FRAMEWORK_VERSION -> v$NEW_FRAMEWORK_VERSION"
  elif [ -n "$OLD_FRAMEWORK_VERSION" ]; then
    echo "ARTi Framework v$NEW_FRAMEWORK_VERSION (already up to date)"
  else
    echo "Installing ARTi Framework v$NEW_FRAMEWORK_VERSION"
  fi
fi

# --- 2. researcher-content subfolders (created empty if missing, never overwritten) --

mkdir -p "$ARTI_HOME/memory" "$ARTI_HOME/memory/memories" "$ARTI_HOME/voice-profiles" "$ARTI_HOME/workflow-sessions" "$ARTI_HOME/inbox/archive"

# inbox/ is the researcher's raw-idea inbox. Its contents are git-ignored (the maintainer's own
# ideas never ship), so a fresh install seeds the two index files it needs, missing-only.
if [ ! -f "$ARTI_HOME/inbox/index.md" ]; then
  cat > "$ARTI_HOME/inbox/index.md" <<'EOF'
# ~/.arti/inbox/ index

Cross-project raw-idea inbox - for capture about the ARTi framework/skills themselves (new skill
ideas, workflow friction, tooling gaps), distinct from `~/.arti/memory/research-idea-bank.md`
(research ideas for future papers) and from `~/.arti/inbox/idea-index.md` (the general cross-project
aggregator of every project's triaged `inbox/` ideas, this file's own entries included). Unprefixed
filename = not yet reviewed. Triaged files (OK/SKIP/PARKED) are capped at 10 outside `archive/`;
untriaged ones are uncapped and never archived.

| File | Type | Status | One-line hook | Used in | Date added |
|---|---|---|---|---|---|
EOF
  echo "  [ok] stub created: inbox/index.md"
fi

if [ ! -f "$ARTI_HOME/inbox/idea-index.md" ]; then
  cat > "$ARTI_HOME/inbox/idea-index.md" <<'EOF'
# Idea List Index

**File location:** `~/.arti/inbox/idea-index.md` - a `project-index.md`-style aggregator: one row
per raw idea captured in any project's `inbox/` folder (this `~/.arti` home's own `inbox/` included),
so "what's my idea list and status" is answered by reading this one file, no per-project scanning
needed.

> Claude upserts a row here the moment an idea is triaged (OK/SKIP/PARKED) in any project's
> `inbox/index.md`.

| Idea | Project | Status | One-line hook | Date added |
|---|---|---|---|---|
EOF
  echo "  [ok] stub created: inbox/idea-index.md"
fi

# Minimal tracker stubs (created only if missing - never overwrites real content).
# Covers a fresh/rebuilt ~/.arti so the package tracker isn't silently absent. Both files live in
# ~/.arti/memory/, alongside every other memory-system file.
if [ ! -f "$ARTI_HOME/memory/MEMORY.md" ]; then
  cat > "$ARTI_HOME/memory/MEMORY.md" <<'EOF'
# ~/.arti/memory Index

Plain pointers-only index of this ~/.arti home's researcher-facing state and package files. See
`todo-list.md` for the live package build/scope checklist and `status.md` for the live narrative
(current state + archive). Add a one-line pointer row here for each new topic file, per the
`[[slug]]`-link convention.

## Index

## Change log
EOF
  echo "  [ok] stub created: memory/MEMORY.md"
fi

if [ ! -f "$ARTI_HOME/memory/todo-list.md" ]; then
  cat > "$ARTI_HOME/memory/todo-list.md" <<'EOF'
---
name: todo-list
description: Authoritative, live checklist for the ARTi package build (checkboxes only - see status.md for narrative)
metadata:
  type: project
---

Authoritative package build/scope checklist. Add Phase sections and `- [ ]`/`- [x]` items as the
package plan develops. No narrative here - session write-ups and Current-state prose belong in
`status.md`.

## Change log
EOF
  echo "  [ok] stub created: memory/todo-list.md"
fi

if [ ! -f "$ARTI_HOME/memory/status.md" ]; then
  cat > "$ARTI_HOME/memory/status.md" <<'EOF'
---
name: status
description: Live narrative for the ARTi package build - Current state + archive (see todo-list.md for the checklist)
metadata:
  type: project
---

## Current state

(nothing yet)

## Archive

## Change log
EOF
  echo "  [ok] stub created: memory/status.md"
fi

# figure-style.md is seeded from the tracked generic default (missing-only), then owned and
# customized by the researcher from there - the installer never touches it again after this.
FIGURE_STYLE_DEFAULT="$ARTI_HOME/skills/ARTi-figure/references/figure-style-default.md"
FIGURE_STYLE_PATH="$ARTI_HOME/memory/figure-style.md"
if [ -f "$FIGURE_STYLE_DEFAULT" ] && [ ! -f "$FIGURE_STYLE_PATH" ]; then
  cp "$FIGURE_STYLE_DEFAULT" "$FIGURE_STYLE_PATH"
  echo "  [ok] stub created: memory/figure-style.md (seeded from ARTi-figure's default)"
fi

# working-preferences.md is seeded from the tracked framework-default (missing-only), the same
# pattern as figure-style.md above - so every install ships with the framework-level rules (e.g.
# cross-project discovery) even before any researcher-specific rule has been captured. The
# installer never touches it again after this; Claude grows it in place per its own header.
WORKING_PREFS_DEFAULT="$ARTI_HOME/skills/ARTi-setup/references/working-preferences-default.md"
WORKING_PREFS_PATH="$ARTI_HOME/memory/working-preferences.md"
if [ -f "$WORKING_PREFS_DEFAULT" ] && [ ! -f "$WORKING_PREFS_PATH" ]; then
  cp "$WORKING_PREFS_DEFAULT" "$WORKING_PREFS_PATH"
  echo "  [ok] stub created: memory/working-preferences.md (seeded from ARTi-setup's default)"
fi

# --- 3. vendored Python (python-build-standalone) + pip dependencies ----------
# Always reconciles requirements.txt against the vendored interpreter, even when
# Python itself doesn't need reinstalling - so re-running the installer is enough
# to pick up a newly-added tool dependency.-

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
  if ! curl -fsSL -o "$tmp_tar" "$url"; then
    echo "ERROR: could not download Python from $url" >&2
    echo "       Check your internet connection (a proxy or firewall blocking github.com is the" >&2
    echo "       usual cause), then re-run this installer." >&2
    exit 1
  fi

  rm -rf "$PYTHON_DIR"
  mkdir -p "$PYTHON_DIR"
  tmp_extract="$(mktemp -d -t arti-python-extract.XXXXXX)"
  tar -xzf "$tmp_tar" -C "$tmp_extract"
  # python-build-standalone's install_only archives extract to a top-level "python/" dir.
  cp -R "$tmp_extract/python/." "$PYTHON_DIR/"
  rm -rf "$tmp_extract" "$tmp_tar"

  echo "$PY_BUILD_TAG/$PY_VERSION" > "$STAMP_FILE"
  echo "  [ok] Python installed at $PYTHON_DIR"
else
  echo "  [ok] Python $PY_VERSION (build $PY_BUILD_TAG) already installed - skipping."
fi

REQ_FILE="$ARTI_HOME/tools/requirements.txt"
if [ -f "$REQ_FILE" ] && [ -d "$PYTHON_DIR" ]; then
  # Non-fatal on purpose: a failed pip (offline, proxy) should still leave a usable
  # install - every tool but arti-docx is stdlib-only. Re-running fixes it later.
  if "$PYTHON_DIR/bin/python3" -m pip install --quiet --disable-pip-version-check -r "$REQ_FILE"; then
    echo "  [ok] pip dependencies reconciled from requirements.txt"
  else
    echo "  WARNING: pip install failed. Everything except arti-docx (.docx export) still works;" >&2
    echo "           re-run this installer once you're online to finish." >&2
  fi
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
    # $d carries a trailing slash from the glob; readlink never does.
    if [ -L "$link" ] && [ "$(readlink "$link")" = "${d%/}" ]; then
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

# --- 5. Desktop icon: "ARTi Framework" -----------------------------------------
# Never fails the install -- a denied Desktop write just gets a warning, same
# rule as the skill-linking step above.

HIDDEN_LAUNCHER="$ARTI_HOME/dashboard/start-arti-framework-hidden.sh"
chmod +x "$HIDDEN_LAUNCHER" 2>/dev/null || true

OS_NAME="$(uname -s)"
if [ "$OS_NAME" = "Darwin" ]; then
  if [ -f "$HIDDEN_LAUNCHER" ]; then
    APP_PATH="$HOME/Desktop/ARTi Framework.app"
    TMP_SCPT="$(mktemp -t arti-framework-app.XXXXXX.applescript)"
    cat > "$TMP_SCPT" <<EOF
do shell script "bash '$HIDDEN_LAUNCHER'"
EOF
    if command -v osacompile >/dev/null 2>&1; then
      rm -rf "$APP_PATH"
      if osacompile -o "$APP_PATH" "$TMP_SCPT" 2>/dev/null; then
        echo "  [ok] Desktop icon created: ARTi Framework.app"
      else
        echo "  WARNING: osacompile failed - skipping Desktop icon." >&2
      fi
    else
      echo "  WARNING: osacompile not found - skipping Desktop icon." >&2
    fi
    rm -f "$TMP_SCPT"
  else
    echo "  WARNING: dashboard/start-arti-framework-hidden.sh not found - skipping Desktop icon." >&2
  fi
else
  if [ -f "$HIDDEN_LAUNCHER" ]; then
    DESKTOP_FILE_CONTENT="[Desktop Entry]
Type=Application
Name=ARTi Framework
Comment=ARTi Framework dashboard
Exec=bash \"$HIDDEN_LAUNCHER\"
Terminal=false
Categories=Development;"
    APPS_DIR="$HOME/.local/share/applications"
    mkdir -p "$APPS_DIR" 2>/dev/null || true
    if [ -d "$APPS_DIR" ]; then
      printf '%s\n' "$DESKTOP_FILE_CONTENT" > "$APPS_DIR/arti-framework.desktop"
      chmod +x "$APPS_DIR/arti-framework.desktop"
      echo "  [ok] Desktop icon created: $APPS_DIR/arti-framework.desktop"
    else
      echo "  WARNING: could not create $APPS_DIR - skipping Desktop icon." >&2
    fi
    if [ -d "$HOME/Desktop" ]; then
      printf '%s\n' "$DESKTOP_FILE_CONTENT" > "$HOME/Desktop/arti-framework.desktop"
      chmod +x "$HOME/Desktop/arti-framework.desktop"
      echo "  [ok] Desktop copy created: ~/Desktop/arti-framework.desktop (GNOME etc. may require a one-time 'Allow Launching' click)"
    fi
  else
    echo "  WARNING: dashboard/start-arti-framework-hidden.sh not found - skipping Desktop icon." >&2
  fi
fi

# --- 6. summary -----------------------------------------------------------------

echo ""
echo "=== ARTi install complete ==="
echo "  Home:      $ARTI_HOME"
echo "  Python:    $PYTHON_DIR/bin/python3"
echo "  Skills:    $SKILLS_DST"
echo "  Re-run this script anytime to update."
