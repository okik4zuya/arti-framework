<#
.SYNOPSIS
  Shows a native Windows folder picker (with "Make New Folder") and prints the
  chosen absolute path to stdout. Prints nothing if the user cancels.
  Invoked by server.py -- not meant to be run standalone.
#>
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

$dialog = New-Object System.Windows.Forms.FolderBrowserDialog
$dialog.Description = "Select a project folder"
$dialog.ShowNewFolderButton = $true

$result = $dialog.ShowDialog($owner)
$owner.Close()
if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
    Write-Output $dialog.SelectedPath
}
