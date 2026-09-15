<#
.SYNOPSIS
  Starts an app and brings its window to the foreground, printing nothing.
  Invoked by server.py -- not meant to be run standalone.

.NOTES
  server.py runs (once hidden via pythonw.exe) as a background process with no
  foreground-activation rights, so a plain subprocess.Popen call from it only
  flashes the new window's taskbar icon instead of bringing it forward. Owning
  a TopMost window here (and activating it) gives this script's process --
  and the child it starts -- enough standing to actually take focus.

  Exe/Arguments arrive as a single base64-encoded JSON payload, not as
  separate -File arguments: PowerShell's legacy argument re-tokenizing for
  scripts invoked via -File mangles backslashes and splits on spaces even
  when the caller quotes the argument correctly, which breaks paths like
  "G:\My Drive\project".

  Start-Process defaults to UseShellExecute, which naively joins
  -ArgumentList elements with spaces instead of quoting each one -- with a
  single argument that accidentally still works, but two or more arguments
  (e.g. "-n" plus a path containing a space) fall apart into extra tokens.
  Each argument that contains whitespace is wrapped in quotes here so it
  survives that join as one token.
#>
param(
    [Parameter(Mandatory=$true)][string]$PayloadB64
)
Add-Type -AssemblyName System.Windows.Forms

$json = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($PayloadB64))
$payload = $json | ConvertFrom-Json

$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$owner.Size = New-Object System.Drawing.Size(0, 0)
$owner.Show()
$owner.Activate()

$quotedArgs = @($payload.args) | ForEach-Object {
    if ($_ -match '\s') { '"' + $_ + '"' } else { $_ }
}
if ($payload.hidden) {
    Start-Process -FilePath $payload.exe -ArgumentList $quotedArgs -WindowStyle Hidden
} else {
    Start-Process -FilePath $payload.exe -ArgumentList $quotedArgs
}

Start-Sleep -Milliseconds 300
$owner.Close()
