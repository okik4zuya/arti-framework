<#
  ARTi installer / updater (Windows)

  Sets up ~/.arti as the single cross-project home for ARTi tooling
  (vendored Python + tools/ + skills/) - never inside a Drive-synced folder.
  Re-running this script later is how you update: it re-syncs repo files,
  skips re-downloading Python if VERSION already matches, and re-copies
  skills into ~/.claude/skills.

  Does NOT touch researcher content (researcher-profile.md, voice-profiles/,
  workflow-sessions/, etc.) - that is created/populated by the ARTi-setup
  skill on first run, or by a one-time manual migration.

  Usage: right-click > "Run with PowerShell", or double-click install.bat.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# Invoke-WebRequest is roughly an order of magnitude slower in Windows PowerShell 5.1
# with the progress bar on, and the Python tarball is ~25 MB.
$ProgressPreference = 'SilentlyContinue'
# Older Win10 boxes still default to TLS 1.0/1.1, which github.com refuses.
try {
  [Net.ServicePointManager]::SecurityProtocol =
    [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch { }
# Files extracted from a downloaded .zip carry a Mark-of-the-Web that can make
# PowerShell block them. Clearing it is a no-op when the flag isn't there.
if ($PSCommandPath) { Unblock-File -LiteralPath $PSCommandPath -ErrorAction SilentlyContinue }

# TODO: fill in once the GitHub repo exists, e.g. 'https://github.com/<you>/arti.git'.
# Until then this script operates purely on local files (safe no-op for the
# clone/pull step) - useful for bootstrapping ~/.arti from a local checkout.
$RepoUrl = ''

$ArtiHome  = Join-Path $HOME '.arti'
$ScriptDir = $PSScriptRoot
$TrackedItems = @('tools', 'skills', 'dashboard', 'logo', 'CLAUDE.md', 'README.md', 'install.ps1', 'install.sh', 'install.bat', 'VERSION', '.gitignore')

function Write-StubFile {
  # Set-Content -Encoding UTF8 emits a BOM in Windows PowerShell 5.1, which then
  # shows up as a stray glyph at the top of every seeded Markdown file. Write the
  # bytes ourselves with a BOM-less UTF-8 encoder instead.
  param([string]$Path, [string]$Content)
  [IO.File]::WriteAllText($Path, $Content, (New-Object Text.UTF8Encoding($false)))
}

function Copy-TrackedItem {
  <#
    Copy one tracked item into $DestRoot under its own name.

    Copy-Item -Recurse against a destination directory that ALREADY exists nests
    the source inside it (~/.arti/tools/tools) rather than merging, so every
    re-run of this installer would bury the tree one level deeper. Clearing the
    destination first fixes that and additionally drops files deleted upstream,
    which a merge would leave behind forever.
  #>
  param([string]$Source, [string]$DestRoot, [string]$Name)
  $dest = Join-Path $DestRoot $Name
  if (Test-Path $Source -PathType Container) {
    if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
    Copy-Item $Source -Destination $dest -Recurse -Force
  } else {
    Copy-Item $Source -Destination $dest -Force
  }
}

Write-Host "=== ARTi installer ==="
Write-Host "Target: $ArtiHome"

# --- 1. sync tracked repo content into ~/.arti --------------------------------

if (-not (Test-Path $ArtiHome)) {
  New-Item -ItemType Directory -Path $ArtiHome -Force | Out-Null
}

$haveGit = [bool](Get-Command git -ErrorAction SilentlyContinue)

if ($RepoUrl) {
  if (Test-Path (Join-Path $ArtiHome '.git')) {
    if ($haveGit) {
      Write-Host "Updating existing ~/.arti checkout (git pull)..."
      Push-Location $ArtiHome
      git pull --ff-only
      Pop-Location
    } else {
      Write-Warning "git not found - cannot pull updates. Install git or re-run later."
    }
  } elseif ($haveGit) {
    Write-Host "Cloning $RepoUrl into ~/.arti..."
    git clone $RepoUrl $ArtiHome
  } else {
    Write-Host "git not found - downloading zipball instead..."
    $zipUrl = ($RepoUrl -replace '\.git$', '') + '/archive/refs/heads/main.zip'
    $zipPath = Join-Path $env:TEMP 'arti-repo.zip'
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
    $extractDir = Join-Path $env:TEMP 'arti-repo-extract'
    if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force }
    Expand-Archive -Path $zipPath -DestinationPath $extractDir
    $srcRoot = Get-ChildItem $extractDir | Select-Object -First 1
    foreach ($item in $TrackedItems) {
      $src = Join-Path $srcRoot.FullName $item
      if (Test-Path $src) { Copy-TrackedItem -Source $src -DestRoot $ArtiHome -Name $item }
    }
  }
} elseif ($ScriptDir -and ($ScriptDir -ne $ArtiHome)) {
  # Bootstrapping from a local checkout that isn't ~/.arti itself yet
  # (e.g. a manually placed copy of this repo) - copy tracked items over.
  Write-Host "No RepoUrl configured - syncing tracked files from local checkout ($ScriptDir)..."
  foreach ($item in $TrackedItems) {
    $src = Join-Path $ScriptDir $item
    if (Test-Path $src) { Copy-TrackedItem -Source $src -DestRoot $ArtiHome -Name $item }
  }
} else {
  Write-Host "Running in place at ~/.arti with no RepoUrl configured - nothing to sync."
}

# --- 2. researcher-content subfolders (created empty if missing, never overwritten) --

foreach ($dir in @('memory', 'memory\memories', 'voice-profiles', 'workflow-sessions', 'wdyt\archive')) {
  $p = Join-Path $ArtiHome $dir
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

# Minimal tracker stubs (created only if missing - never overwrites real content).
# Covers a fresh/rebuilt ~/.arti so the package tracker isn't silently absent. Both files live in
# ~/.arti/memory/, alongside every other memory-system file.
$memoryStub = @'
# ~/.arti/memory Index

Plain pointers-only index of this ~/.arti home's researcher-facing state and package files. See
`todo-list.md` for the live package build/scope checklist and `status.md` for the live narrative
(current state + archive). Add a one-line pointer row here for each new topic file, per the
`[[slug]]`-link convention.

## Index

## Change log
'@

$todoStub = @'
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
'@

$statusStub = @'
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
'@

# wdyt/ is the researcher's raw-idea inbox. Its contents are git-ignored (the maintainer's own
# ideas never ship), so a fresh install seeds the two index files it needs, missing-only.
$wdytIndexStub = @'
# ~/.arti/wdyt/ index

Cross-project raw-idea inbox - for capture about the ARTi framework/skills themselves (new skill
ideas, workflow friction, tooling gaps), distinct from `~/.arti/memory/research-idea-bank.md`
(research ideas for future papers) and from `~/.arti/wdyt/idea-index.md` (the general cross-project
aggregator of every project's triaged `wdyt/` ideas, this file's own entries included). Unprefixed
filename = not yet reviewed. Triaged files (OK/SKIP/PARKED) are capped at 10 outside `archive/`;
untriaged ones are uncapped and never archived.

| File | Type | Status | One-line hook | Used in | Date added |
|---|---|---|---|---|---|
'@

$ideaIndexStub = @'
# Idea List Index

**File location:** `~/.arti/wdyt/idea-index.md` - a `progress-index.md`-style aggregator: one row
per raw idea captured in any project's `wdyt/` folder (this `~/.arti` home's own `wdyt/` included),
so "what's my idea list and status" is answered by reading this one file, no per-project scanning
needed.

> Claude upserts a row here the moment an idea is triaged (OK/SKIP/PARKED) in any project's
> `wdyt/index.md`.

| Idea | Project | Status | One-line hook | Date added |
|---|---|---|---|---|
'@

$wdytIndexPath = Join-Path $ArtiHome 'wdyt\index.md'
$ideaIndexPath = Join-Path $ArtiHome 'wdyt\idea-index.md'
if (-not (Test-Path $wdytIndexPath)) {
  Write-StubFile -Path $wdytIndexPath -Content $wdytIndexStub
  Write-Host "  [ok] stub created: wdyt\index.md"
}
if (-not (Test-Path $ideaIndexPath)) {
  Write-StubFile -Path $ideaIndexPath -Content $ideaIndexStub
  Write-Host "  [ok] stub created: wdyt\idea-index.md"
}

$memoryPath = Join-Path $ArtiHome 'memory\MEMORY.md'
$todoPath   = Join-Path $ArtiHome 'memory\todo-list.md'
$statusPath = Join-Path $ArtiHome 'memory\status.md'
if (-not (Test-Path $memoryPath)) {
  Write-StubFile -Path $memoryPath -Content $memoryStub
  Write-Host "  [ok] stub created: memory\MEMORY.md"
}
if (-not (Test-Path $todoPath)) {
  Write-StubFile -Path $todoPath -Content $todoStub
  Write-Host "  [ok] stub created: memory\todo-list.md"
}
if (-not (Test-Path $statusPath)) {
  Write-StubFile -Path $statusPath -Content $statusStub
  Write-Host "  [ok] stub created: memory\status.md"
}

# figure-style.md is seeded from the tracked generic default (missing-only), then owned and
# customized by the researcher from there - the installer never touches it again after this.
$figureStyleDefault = Join-Path $ArtiHome 'skills\ARTi-figure\references\figure-style-default.md'
$figureStylePath    = Join-Path $ArtiHome 'memory\figure-style.md'
if ((Test-Path $figureStyleDefault) -and (-not (Test-Path $figureStylePath))) {
  Copy-Item $figureStyleDefault -Destination $figureStylePath
  Write-Host "  [ok] stub created: memory\figure-style.md (seeded from ARTi-figure's default)"
}

# working-preferences.md is seeded from the tracked framework-default (missing-only), the same
# pattern as figure-style.md above - so every install ships with the framework-level rules (e.g.
# cross-project discovery) even before any researcher-specific rule has been captured. The
# installer never touches it again after this; Claude grows it in place per its own header.
$workingPrefsDefault = Join-Path $ArtiHome 'skills\ARTi-setup\references\working-preferences-default.md'
$workingPrefsPath    = Join-Path $ArtiHome 'memory\working-preferences.md'
if ((Test-Path $workingPrefsDefault) -and (-not (Test-Path $workingPrefsPath))) {
  Copy-Item $workingPrefsDefault -Destination $workingPrefsPath
  Write-Host "  [ok] stub created: memory\working-preferences.md (seeded from ARTi-setup's default)"
}

# --- 3. vendored Python (python-build-standalone) + pip dependencies ----------
# Always reconciles requirements.txt against the vendored interpreter, even when
# Python itself doesn't need reinstalling - so re-running the installer is enough
# to pick up a newly-added tool dependency.

$versionFile = Join-Path $ArtiHome 'VERSION'
$pyBuildTag = $null
$pyVersion  = $null
if (Test-Path $versionFile) {
  foreach ($line in Get-Content $versionFile) {
    if ($line -match '^PYTHON_BUILD_TAG=(.+)$') { $pyBuildTag = $Matches[1].Trim() }
    if ($line -match '^PYTHON_VERSION=(.+)$')   { $pyVersion  = $Matches[1].Trim() }
  }
}
if (-not $pyBuildTag -or -not $pyVersion) {
  throw "VERSION file missing or malformed at $versionFile - expected PYTHON_BUILD_TAG= and PYTHON_VERSION= lines."
}

$pythonDir = Join-Path $ArtiHome 'python'
$stampFile = Join-Path $pythonDir 'INSTALLED_VERSION'
$needPython = $true
if ((Test-Path $stampFile)) {
  $installed = Get-Content $stampFile -Raw
  if ($installed.Trim() -eq "$pyBuildTag/$pyVersion") { $needPython = $false }
}

if ($needPython) {
  if (-not (Get-Command tar -ErrorAction SilentlyContinue)) {
    throw "tar.exe not found. It ships with Windows 10 build 1803 and later - update Windows, then re-run this installer."
  }
  Write-Host "Fetching Python $pyVersion (build $pyBuildTag) via python-build-standalone (~25 MB, this is the slow step)..."
  $arch = if ([Environment]::Is64BitOperatingSystem) { 'x86_64' } else { 'i686' }
  $asset = "cpython-$pyVersion+$pyBuildTag-$arch-pc-windows-msvc-install_only.tar.gz"
  $url = "https://github.com/astral-sh/python-build-standalone/releases/download/$pyBuildTag/$asset"
  $tarPath = Join-Path $env:TEMP $asset
  try {
    Invoke-WebRequest -Uri $url -OutFile $tarPath
  } catch {
    throw "Could not download Python from $url - $($_.Exception.Message). Check your internet connection (a proxy or firewall blocking github.com is the usual cause) and re-run this installer."
  }

  if (Test-Path $pythonDir) { Remove-Item $pythonDir -Recurse -Force }
  New-Item -ItemType Directory -Path $pythonDir -Force | Out-Null
  # python-build-standalone's install_only archives extract to a top-level "python/" dir.
  $extractParent = Join-Path $env:TEMP 'arti-python-extract'
  if (Test-Path $extractParent) { Remove-Item $extractParent -Recurse -Force }
  New-Item -ItemType Directory -Path $extractParent -Force | Out-Null
  tar -xzf $tarPath -C $extractParent
  Copy-Item (Join-Path $extractParent 'python\*') -Destination $pythonDir -Recurse -Force
  Remove-Item $extractParent -Recurse -Force
  Remove-Item $tarPath -Force

  Write-StubFile -Path $stampFile -Content "$pyBuildTag/$pyVersion"
  Write-Host "  [ok] Python installed at $pythonDir"
} else {
  Write-Host "  [ok] Python $pyVersion (build $pyBuildTag) already installed - skipping."
}

$reqFile = Join-Path $ArtiHome 'tools\requirements.txt'
if ((Test-Path $reqFile) -and (Test-Path $pythonDir)) {
  $pyExe = Join-Path $pythonDir 'python.exe'
  # Non-fatal on purpose: a failed pip (offline, proxy) should still leave a usable
  # install - every tool but arti-docx is stdlib-only. Re-running fixes it later.
  try {
    & $pyExe -m pip install --quiet --disable-pip-version-check -r $reqFile
    if ($LASTEXITCODE -ne 0) { throw "pip exited with code $LASTEXITCODE" }
    Write-Host "  [ok] pip dependencies reconciled from requirements.txt"
  } catch {
    Write-Warning "pip install failed ($($_.Exception.Message)). Everything except arti-docx (.docx export) still works; re-run this installer once you're online to finish."
  }
}

# --- 4. wire skills into ~/.claude/skills --------------------------------------
# Junctions, not copies: ~/.arti/skills/<name> is the only place a skill is ever edited.
# A junction makes ~/.claude/skills/<name> the same directory on disk, so there is no
# separate copy to fall out of sync and no re-run-the-installer step after an edit.
# Junctions need no admin rights on Windows (unlike symlinks) but do require the link
# and target to be on the same volume - true for the default ~/.arti and ~/.claude paths.
# If that ever isn't true (or junction creation fails for any other reason), fall back
# to a plain copy so the skill still gets installed, just without the live-edit property.

$skillsSrc = Join-Path $ArtiHome 'skills'
$skillsDst = Join-Path $HOME '.claude\skills'
if (Test-Path $skillsSrc) {
  if (-not (Test-Path $skillsDst)) { New-Item -ItemType Directory -Path $skillsDst -Force | Out-Null }
  Get-ChildItem $skillsSrc -Directory | ForEach-Object {
    $target = $_.FullName
    $link = Join-Path $skillsDst $_.Name
    $existing = Get-Item $link -Force -ErrorAction SilentlyContinue
    if ($existing -and $existing.LinkType -eq 'Junction' -and $existing.Target -eq $target) {
      Write-Host "  [ok] skill already linked: $($_.Name)"
      return
    }
    if (Test-Path $link) {
      $stale = Get-Item $link -Force
      if ($stale.PSIsContainer -and ($stale.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        # Remove-Item -Recurse on a junction can delete the TARGET's contents in
        # Windows PowerShell 5.1 - here that target is the only copy of the skill.
        # Directory.Delete(path, recursive:$false) unlinks the reparse point only.
        [IO.Directory]::Delete($stale.FullName, $false)
      } else {
        Remove-Item $link -Recurse -Force
      }
    }
    try {
      New-Item -ItemType Junction -Path $link -Target $target -ErrorAction Stop | Out-Null
      Write-Host "  [ok] skill linked: $($_.Name)"
    } catch {
      Write-Warning "Junction failed for $($_.Name) ($($_.Exception.Message)) - falling back to a copy."
      Copy-Item $target -Destination $skillsDst -Recurse -Force
      Write-Host "  [ok] skill copied (no live-edit link): $($_.Name)"
    }
  }
}

# --- 5. Desktop shortcut: "ARTi Framework" -------------------------------------
# Idempotent (overwritten every run) and never fails the install -- a denied
# Desktop write just gets a warning, same rule as the skill-linking step above.

try {
  $desktopDir = [Environment]::GetFolderPath('Desktop')
  $shortcutPath = Join-Path $desktopDir 'ARTi Framework.lnk'
  $vbsTarget = Join-Path $ArtiHome 'dashboard\start-arti-framework.vbs'
  if (Test-Path $vbsTarget) {
    $wshShell = New-Object -ComObject WScript.Shell
    $shortcut = $wshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = 'wscript.exe'
    $shortcut.Arguments = '"' + $vbsTarget + '"'
    $shortcut.WorkingDirectory = Join-Path $ArtiHome 'dashboard'
    $shortcut.Description = 'ARTi Framework dashboard'
    $iconPath = Join-Path $ArtiHome 'logo\export\icon\arti-launcher.ico'
    if (Test-Path $iconPath) { $shortcut.IconLocation = $iconPath }
    $shortcut.Save()
    Write-Host "  [ok] Desktop shortcut created: ARTi Framework.lnk"
  } else {
    Write-Warning "dashboard\start-arti-framework.vbs not found - skipping Desktop shortcut."
  }
} catch {
  Write-Warning "Could not create Desktop shortcut: $($_.Exception.Message)"
}

# --- 6. summary -----------------------------------------------------------------

Write-Host ""
Write-Host "=== ARTi install complete ==="
Write-Host "  Home:      $ArtiHome"
Write-Host "  Python:    $(Join-Path $pythonDir 'python.exe')"
Write-Host "  Skills:    $skillsDst"
Write-Host "  Re-run this script anytime to update."
