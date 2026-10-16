# precheck.ps1 - check a license key BEFORE the installer writes anything (run by arti-installer.nsi).
#
# Needs no Python (it is not installed yet). The key comes in $env:ARTI_PRECHECK_KEY (never on the command
# line, so a typed quote cannot break the quoting). Steps:
#   1. offline: format and checksum, same rules as tools/_shared/license.py (catches every typo)
#   2. online, read only: POST /activations (does not bind a seat). Refuses an unknown or revoked key,
#      an expired one, and one whose every seat is held by another computer.
# Prints one plain sentence and exits 0 (usable) or non-zero (do not install). Activation itself still
# happens after the install, as before; this only stops a doomed install from starting.
#   exit 0 ok | 2 bad key | 3 unknown, revoked or expired | 4 seats full | 5 server unreachable
param([string]$Api = "https://lisensi.arti.ai.id/v1")

$ErrorActionPreference = "Stop"
if ($env:ARTI_LICENSE_API) { $Api = $env:ARTI_LICENSE_API }
$Api = $Api.TrimEnd('/')

function Stop-With([int]$Code, [string]$Message) {
  [Console]::Out.WriteLine($Message)
  exit $Code
}

# ---- 1. format and checksum --------------------------------------------------------------------
$alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
$raw = [string]$env:ARTI_PRECHECK_KEY
$s = ($raw -replace "[\s-]", "").ToUpperInvariant()
if ($s.StartsWith("ARTI")) { $s = $s.Substring(4) }
$s = $s.Replace("I", "1").Replace("L", "1").Replace("O", "0")
$ok = ($s.Length -eq 16)
if ($ok) { foreach ($c in $s.ToCharArray()) { if ($alphabet.IndexOf($c) -lt 0) { $ok = $false } } }
if ($ok) {
  $sum = 0
  for ($i = 0; $i -lt 15; $i++) { $sum += $alphabet.IndexOf($s[$i]) * (2 * $i + 1) }
  if ($alphabet[$sum % 32] -ne $s[15]) { $ok = $false }
}
if (-not $ok) { Stop-With 2 "That key has a typo. Check it and try again." }
$key = "ARTI-" + ($s.Substring(0, 4), $s.Substring(4, 4), $s.Substring(8, 4), $s.Substring(12, 4) -join "-")

# ---- 2. online, read only ------------------------------------------------------------------------
try {
  [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
  $reg = [Microsoft.Win32.RegistryKey]::OpenBaseKey("LocalMachine", "Registry64")
  $guid = $reg.OpenSubKey("SOFTWARE\Microsoft\Cryptography").GetValue("MachineGuid")
  $sha = [Security.Cryptography.SHA256]::Create()
  $mine = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes("arti-v1" + $guid))) -replace "-", "").ToLowerInvariant()
} catch {
  $mine = ""   # cannot tell which seat is ours: fall back to the plain seat count below
}

try {
  $body = @{ key = $key } | ConvertTo-Json -Compress
  $r = Invoke-RestMethod -Uri "$Api/activations" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 15
} catch {
  $code = $null
  try {
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) {
      $code = ($_.ErrorDetails.Message | ConvertFrom-Json).code   # Windows PowerShell 5.1 puts the body here
    } elseif ($_.Exception.Response) {
      $stream = $_.Exception.Response.GetResponseStream()
      if ($stream.CanSeek) { $stream.Position = 0 }
      $code = ((New-Object IO.StreamReader($stream)).ReadToEnd() | ConvertFrom-Json).code
    }
  } catch { }
  switch ($code) {
    "not_found"    { Stop-With 3 "No such license key. Check it and try again." }
    "bad_checksum" { Stop-With 2 "That key has a typo. Check it and try again." }
    "key_revoked"  { Stop-With 3 "This license was revoked. Contact support." }
    "rate_limited" { Stop-With 5 "Too many requests. Wait a minute and try again." }
    default        { Stop-With 5 "Cannot reach the licensing server. Check the internet connection and try again." }
  }
}

if ($r.status -eq "revoked") { Stop-With 3 "This license was revoked. Contact support." }
if ($r.expires -and ([datetime]::Parse($r.expires).ToUniversalTime() -lt (Get-Date).ToUniversalTime())) {
  Stop-With 3 "This license has expired. Renew it first, then run the installer again."
}
$active = @($r.activations | Where-Object { -not $_.deactivated })
$ours = @($active | Where-Object { $mine -and $_.machine_hash -eq $mine })
if ($ours.Count -eq 0 -and $active.Count -ge [int]$r.seats) {
  Stop-With 4 "This key is already active on another computer and every seat is in use. Deactivate it on that computer (Settings > License there), or contact support to move it."
}
Stop-With 0 "Key accepted."
