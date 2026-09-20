<#
.SYNOPSIS
  Shows the native Windows "Save As" dialog (folder navigation, a built-in
  "New folder" button, and filename entry) and prints the chosen absolute
  path to stdout. Prints nothing if the user cancels. Invoked by
  platform_ops.save_file() -- not meant to be run standalone.
#>
param(
    [string]$InitialDir = "",
    [string]$DefaultName = "message.md"
)
Add-Type -AssemblyName System.Windows.Forms

# server.py spawns this script from a background (often windowless) python process,
# which Windows denies foreground-activation rights -- without a TopMost owner window
# the dialog only flashes in the taskbar instead of popping to front.
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.StartPosition = "CenterScreen"
$owner.ShowInTaskbar = $false
$owner.Size = New-Object System.Drawing.Size(0, 0)
$owner.Show()
$owner.Activate()

$dialog = New-Object System.Windows.Forms.SaveFileDialog
$dialog.Title = "Save message as Markdown"
$dialog.Filter = "Markdown files (*.md)|*.md|All files (*.*)|*.*"
$dialog.FileName = $DefaultName
if ($InitialDir -and (Test-Path $InitialDir)) {
    $dialog.InitialDirectory = $InitialDir
}

$result = $dialog.ShowDialog($owner)
$owner.Close()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $dialog.FileName
}
