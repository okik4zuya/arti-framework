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

# TODO: fill in once the GitHub repo exists, e.g. 'https://github.com/<you>/arti.git'.
# Until then this script operates purely on local files (safe no-op for the
# clone/pull step) - useful for bootstrapping ~/.arti from a local checkout.
$RepoUrl = ''

$ArtiHome  = Join-Path $HOME '.arti'
$ScriptDir = $PSScriptRoot
$TrackedItems = @('tools', 'skills', 'install.ps1', 'install.sh', 'install.bat', 'VERSION', '.gitignore')

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
      if (Test-Path $src) {
        Copy-Item $src -Destination $ArtiHome -Recurse -Force
      }
    }
  }
} elseif ($ScriptDir -and ($ScriptDir -ne $ArtiHome)) {
  # Bootstrapping from a local checkout that isn't ~/.arti itself yet
  # (e.g. a manually placed copy of this repo) - copy tracked items over.
  Write-Host "No RepoUrl configured - syncing tracked files from local checkout ($ScriptDir)..."
  foreach ($item in $TrackedItems) {
    $src = Join-Path $ScriptDir $item
    if (Test-Path $src) {
      Copy-Item $src -Destination $ArtiHome -Recurse -Force
    }
  }
} else {
  Write-Host "Running in place at ~/.arti with no RepoUrl configured - nothing to sync."
}

# --- 2. researcher-content subfolders (created empty if missing, never overwritten) --

foreach ($dir in @('voice-profiles', 'workflow-sessions')) {
  $p = Join-Path $ArtiHome $dir
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

# --- 3. vendored Python (python-build-standalone) ------------------------------

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
  Write-Host "Fetching Python $pyVersion (build $pyBuildTag) via python-build-standalone..."
  $arch = if ([Environment]::Is64BitOperatingSystem) { 'x86_64' } else { 'i686' }
  $asset = "cpython-$pyVersion+$pyBuildTag-$arch-pc-windows-msvc-install_only.tar.gz"
  $url = "https://github.com/astral-sh/python-build-standalone/releases/download/$pyBuildTag/$asset"
  $tarPath = Join-Path $env:TEMP $asset
  Invoke-WebRequest -Uri $url -OutFile $tarPath

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

  Set-Content -Path $stampFile -Value "$pyBuildTag/$pyVersion" -NoNewline

  $reqFile = Join-Path $ArtiHome 'tools\requirements.txt'
  if (Test-Path $reqFile) {
    $pyExe = Join-Path $pythonDir 'python.exe'
    & $pyExe -m pip install --quiet -r $reqFile
  }
  Write-Host "  [ok] Python installed at $pythonDir"
} else {
  Write-Host "  [ok] Python $pyVersion (build $pyBuildTag) already installed - skipping."
}

# --- 4. wire skills into ~/.claude/skills --------------------------------------

$skillsSrc = Join-Path $ArtiHome 'skills'
$skillsDst = Join-Path $HOME '.claude\skills'
if (Test-Path $skillsSrc) {
  if (-not (Test-Path $skillsDst)) { New-Item -ItemType Directory -Path $skillsDst -Force | Out-Null }
  Get-ChildItem $skillsSrc -Directory | ForEach-Object {
    Copy-Item $_.FullName -Destination $skillsDst -Recurse -Force
    Write-Host "  [ok] skill installed: $($_.Name)"
  }
}

# --- 5. summary -----------------------------------------------------------------

Write-Host ""
Write-Host "=== ARTi install complete ==="
Write-Host "  Home:      $ArtiHome"
Write-Host "  Python:    $(Join-Path $pythonDir 'python.exe')"
Write-Host "  Skills:    $skillsDst"
Write-Host "  Re-run this script anytime to update."
