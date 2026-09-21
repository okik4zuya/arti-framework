<#
.SYNOPSIS
  Puts one or more file paths onto the Windows clipboard as a real file-drop
  list (CF_HDROP) -- what Explorer, WhatsApp Desktop, email clients, etc.
  read on Ctrl+V, distinct from a text paste of the path string(s). Invoked
  by server.py -- not meant to be run standalone.

.NOTES
  Clipboard.SetFileDropList() requires an STA apartment thread, hence the
  -STA flag on the powershell.exe invocation (same as this folder's other
  native-op scripts).
#>
param(
    [Parameter(Mandatory=$true)][string]$PayloadB64
)
Add-Type -AssemblyName System.Windows.Forms

$json = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($PayloadB64))
$paths = $json | ConvertFrom-Json

$files = New-Object System.Collections.Specialized.StringCollection
foreach ($p in @($paths)) { [void]$files.Add($p) }
[System.Windows.Forms.Clipboard]::SetFileDropList($files)
