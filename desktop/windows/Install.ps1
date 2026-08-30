# Install Toastmasters Tools for this Windows user: copy the folder into
# LocalAppData and pin a Desktop + Start Menu shortcut. No unsigned .exe.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

$src = $PSScriptRoot
$dst = Join-Path $env:LOCALAPPDATA 'ToastmastersTools\app'
Get-ChildItem -LiteralPath $src -Recurse -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue

$srcFull = [IO.Path]::GetFullPath($src).TrimEnd('\')
$dstFull = [IO.Path]::GetFullPath($dst).TrimEnd('\')
if ($srcFull -ne $dstFull) {
  if (Test-Path -LiteralPath $dst) {
    Remove-Item -LiteralPath $dst -Recurse -Force
  }
  New-Item -ItemType Directory -Force -Path $dst | Out-Null
  Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force
}

Get-ChildItem -LiteralPath $dst -Recurse -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue

$serve = Join-Path $dst 'serve.ps1'
if (-not (Test-Path -LiteralPath $serve)) {
  [System.Windows.Forms.MessageBox]::Show('serve.ps1 is missing. Extract the whole ToastmastersTools folder.', 'Toastmasters Tools') | Out-Null
  exit 1
}

$ps = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$args = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$serve`""

function New-Shortcut($path) {
  $w = New-Object -ComObject WScript.Shell
  $lnk = $w.CreateShortcut($path)
  $lnk.TargetPath = $ps
  $lnk.Arguments = $args
  $lnk.WorkingDirectory = $dst
  $lnk.WindowStyle = 7
  $edge = Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'
  if (-not (Test-Path -LiteralPath $edge)) {
    $edge = Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'
  }
  if (Test-Path -LiteralPath $edge) {
    $lnk.IconLocation = "$edge,0"
  }
  $lnk.Description = 'Toastmasters Tools'
  $lnk.Save()
}

$desktop = [Environment]::GetFolderPath('Desktop')
$programs = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
New-Item -ItemType Directory -Force -Path $programs | Out-Null
New-Shortcut (Join-Path $desktop 'Toastmasters Tools.lnk')
New-Shortcut (Join-Path $programs 'Toastmasters Tools.lnk')

[System.Windows.Forms.MessageBox]::Show(
  "Installed for this Windows user.`r`n`r`nUse the Desktop shortcut: Toastmasters Tools.`r`nIt is also in the Start menu.`r`n`r`nTo share with someone else, send ToastmastersTools-portable.zip (not the .exe).",
  'Toastmasters Tools'
) | Out-Null
