<#
  arti-render - figure spec (JSON) -> .drawio
  NOTE: keep this file pure ASCII. Windows PowerShell 5.1 reads a BOM-less
  UTF-8 script as ANSI, and any multi-byte character becomes a parse error.

  Zero-install: pure PowerShell, no browser, no external binary. Emits only
  the editable .drawio file - open it in draw.io to view, export, or fix by
  hand (wrong wrapping, overflowing text, a box that needs resizing). There
  is no auto-fix loop here on purpose: draw.io's own editor is where that
  happens.

  Usage:
    .\render.ps1 -Spec ..\..\figures\src\Fig_1.json -OutDir ..\..\figures\out

  Params:
    -Spec     path to the figure spec JSON
    -OutDir   directory for the generated .drawio (created if missing)
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Spec,
  [string]$OutDir = '.'
)

$ErrorActionPreference = 'Stop'

function Esc-Xml([string]$s) {
  return $s.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;').Replace('"', '&quot;')
}

# --- load spec ---------------------------------------------------------------

$specPath = (Resolve-Path $Spec).Path
$specText = Get-Content $specPath -Raw -Encoding UTF8
$s = $specText | ConvertFrom-Json
$name = $s.figure
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
$out = (Resolve-Path $OutDir).Path

Write-Host "arti-render: $name  ($($s.canvas.width) x $($s.canvas.height))"

# --- .drawio emitter -----------------------------------------------------
# drawio does its own text wrapping, so this emitter only needs geometry.

$sb = New-Object System.Text.StringBuilder
[void]$sb.AppendLine('<mxfile host="arti-render" version="28.0.6">')
[void]$sb.AppendLine("  <diagram name=""$(Esc-Xml $name)"" id=""arti-$name"">")
[void]$sb.AppendLine("    <mxGraphModel dx=""2182"" dy=""1158"" grid=""1"" gridSize=""10"" guides=""1"" tooltips=""1"" connect=""1"" arrows=""1"" fold=""1"" page=""1"" pageScale=""1"" pageWidth=""$($s.canvas.width)"" pageHeight=""$($s.canvas.height)"" math=""0"" shadow=""0"">")
[void]$sb.AppendLine('      <root>')
[void]$sb.AppendLine('        <mxCell id="0" />')
[void]$sb.AppendLine('        <mxCell id="1" parent="0" />')

$d = $s.defaults
$byId = @{}
foreach ($n in $s.nodes) { $byId[$n.id] = $n }

# edges first, so they sit behind the boxes
$i = 0
foreach ($e in $s.edges) {
  $i++
  $style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;entryDx=0;entryDy=0;strokeWidth=$($d.strokeWidth);fontSize=$($d.fontSize);"
  [void]$sb.AppendLine("        <mxCell id=""e$i"" style=""$style"" edge=""1"" parent=""1"" source=""$($e.from)"" target=""$($e.to)"">")
  if ($e.route -eq 'vhv') {
    $a = $byId[$e.from]; $b = $byId[$e.to]
    $ax = $a.x + $a.w / 2; $bx = $b.x + $b.w / 2
    [void]$sb.AppendLine('          <mxGeometry relative="1" as="geometry">')
    [void]$sb.AppendLine('            <Array as="points">')
    [void]$sb.AppendLine("              <mxPoint x=""$ax"" y=""$($e.midY)"" />")
    [void]$sb.AppendLine("              <mxPoint x=""$bx"" y=""$($e.midY)"" />")
    [void]$sb.AppendLine('            </Array>')
    [void]$sb.AppendLine('          </mxGeometry>')
  } else {
    [void]$sb.AppendLine('          <mxGeometry relative="1" as="geometry" />')
  }
  [void]$sb.AppendLine('        </mxCell>')
}

foreach ($n in $s.nodes) {
  $st = $s.styles.($n.style)
  $parts = @()
  foreach ($ln in $n.lines) {
    $t = Esc-Xml $ln.t
    if ($ln.b) { $parts += "&lt;b&gt;$t&lt;/b&gt;" } else { $parts += $t }
  }
  $value = ($parts -join '&lt;br&gt;')
  $cellStyle = "text;html=1;align=center;verticalAlign=middle;whiteSpace=wrap;rounded=0;strokeColor=$($st.stroke);strokeWidth=$($d.strokeWidth);fontSize=$($d.fontSize);spacingLeft=$($d.padX);spacingRight=$($d.padX);fillColor=$($st.fill);fontColor=$($st.text);"
  [void]$sb.AppendLine("        <mxCell id=""$($n.id)"" value=""$value"" style=""$cellStyle"" vertex=""1"" parent=""1"">")
  [void]$sb.AppendLine("          <mxGeometry x=""$($n.x)"" y=""$($n.y)"" width=""$($n.w)"" height=""$($n.h)"" as=""geometry"" />")
  [void]$sb.AppendLine('        </mxCell>')
}

[void]$sb.AppendLine('      </root>')
[void]$sb.AppendLine('    </mxGraphModel>')
[void]$sb.AppendLine('  </diagram>')
[void]$sb.AppendLine('</mxfile>')

$drawioPath = Join-Path $out "$name.drawio"
[System.IO.File]::WriteAllText($drawioPath, $sb.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "  [ok] $drawioPath"

# --- optional PNG, only if the draw.io desktop app happens to be installed --
# This is a convenience, not a dependency: if drawio.exe is missing we just
# skip it and say so - no browser fallback, no chasing another renderer.
$drawioExe = $null
foreach ($c in @(
  "${env:ProgramFiles}\draw.io\draw.io.exe",
  "${env:ProgramFiles(x86)}\draw.io\draw.io.exe",
  "$env:LOCALAPPDATA\Programs\draw.io\draw.io.exe"
)) { if (Test-Path $c) { $drawioExe = $c; break } }

if ($drawioExe) {
  $pngPath = Join-Path $out "$name.png"
  $errLog = Join-Path ([System.IO.Path]::GetTempPath()) "arti-drawio-cli.log"
  Start-Process -FilePath $drawioExe -ArgumentList @('-x', '-f', 'png', '-s', '4', '-o', $pngPath, $drawioPath) `
    -NoNewWindow -Wait -RedirectStandardError $errLog | Out-Null
  if (Test-Path $pngPath) { Write-Host "  [ok] $pngPath  (scale 4x, via draw.io CLI)" }
  else { Write-Host "  draw.io CLI export failed - open $drawioPath by hand and export instead." }
} else {
  Write-Host "  draw.io desktop not found - skipping PNG. Open $drawioPath in draw.io to export yourself."
}
