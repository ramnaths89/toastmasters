# Serves the bundled hub on 127.0.0.1 and opens Edge/Chrome --app.
# Not an .exe, but under Smart App Control PowerShell runs in Constrained
# Language Mode and Add-Type / HttpListener below are refused - this pack is
# for PCs without SAC. The sheet-only pack (desktop/windows/sheet) avoids
# PowerShell entirely.
# Close the app window to stop the server.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms

$Root = $PSScriptRoot
Get-ChildItem -LiteralPath $Root -Recurse -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue
$Port = 8765
$ProfileDir = Join-Path $env:LOCALAPPDATA 'ToastmastersTools\edge-profile'

function Fail($msg) {
  [System.Windows.Forms.MessageBox]::Show($msg, 'Toastmasters Tools') | Out-Null
  exit 1
}

function Find-Browser {
  $candidates = @(
    (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $env:ProgramFiles 'Microsoft\Edge\Application\msedge.exe'),
    (Join-Path $env:ProgramFiles 'Google\Chrome\Application\chrome.exe'),
    (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
    (Join-Path $env:LOCALAPPDATA 'Google\Chrome\Application\chrome.exe')
  )
  foreach ($p in $candidates) {
    if ($p -and (Test-Path -LiteralPath $p)) { return $p }
  }
  return $null
}

function Mime($path) {
  switch ([IO.Path]::GetExtension($path).ToLowerInvariant()) {
    '.html' { 'text/html; charset=utf-8' }
    '.js'   { 'text/javascript; charset=utf-8' }
    '.css'  { 'text/css; charset=utf-8' }
    '.json' { 'application/json' }
    '.svg'  { 'image/svg+xml' }
    '.png'  { 'image/png' }
    '.ico'  { 'image/x-icon' }
    '.woff2'{ 'font/woff2' }
    default { 'application/octet-stream' }
  }
}

function Safe-File($rel) {
  $rel = [Uri]::UnescapeDataString(($rel -replace '\\', '/'))
  if ($rel.StartsWith('/')) { $rel = $rel.Substring(1) }
  if (-not $rel -or $rel.EndsWith('/')) { $rel += 'index.html' }
  $full = [IO.Path]::GetFullPath((Join-Path $Root $rel))
  $rootFull = [IO.Path]::GetFullPath($Root).TrimEnd('\', '/') + '\'
  if (-not $full.StartsWith($rootFull, [StringComparison]::OrdinalIgnoreCase)) { return $null }
  if (Test-Path -LiteralPath $full -PathType Container) {
    $full = Join-Path $full 'index.html'
  }
  if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { return $null }
  return $full
}

$browser = Find-Browser
if (-not $browser) {
  Fail 'Microsoft Edge or Chrome was not found. Install Edge, then double-click ToastmastersTools.cmd again.'
}

$listener = New-Object System.Net.HttpListener
$bound = $false
foreach ($tryPort in 8765, 8766, 8767, 8768, 8769) {
  if ($listener.IsListening) {
    try { $listener.Stop() } catch { }
  }
  try { $listener.Close() } catch { }
  $listener = New-Object System.Net.HttpListener
  $listener.Prefixes.Add("http://127.0.0.1:$tryPort/")
  try {
    $listener.Start()
    $Port = $tryPort
    $bound = $true
    break
  } catch { }
}
if (-not $bound) {
  Fail 'Could not listen on 127.0.0.1:8765-8769. Close anything using those ports and try again.'
}

$url = "http://127.0.0.1:$Port/"
New-Item -ItemType Directory -Force -Path $ProfileDir | Out-Null
$proc = Start-Process -FilePath $browser -ArgumentList @(
  "--app=$url",
  "--user-data-dir=$ProfileDir",
  '--no-first-run',
  '--no-default-browser-check'
) -PassThru

try {
  $async = $listener.BeginGetContext($null, $null)
  while (-not $proc.HasExited) {
    if ($async.AsyncWaitHandle.WaitOne(250)) {
      $ctx = $listener.EndGetContext($async)
      $async = $listener.BeginGetContext($null, $null)
      $req = $ctx.Request
      $res = $ctx.Response
      try {
        $file = Safe-File $req.Url.AbsolutePath
        if (-not $file) {
          $res.StatusCode = 404
          $buf = [Text.Encoding]::UTF8.GetBytes('Not found')
          $res.ContentLength64 = $buf.Length
          $res.OutputStream.Write($buf, 0, $buf.Length)
        } else {
          $bytes = [IO.File]::ReadAllBytes($file)
          $res.StatusCode = 200
          $res.ContentType = Mime $file
          $res.Headers['Cache-Control'] = 'no-store'
          $res.ContentLength64 = $bytes.Length
          if ($req.HttpMethod -ne 'HEAD') {
            $res.OutputStream.Write($bytes, 0, $bytes.Length)
          }
        }
      } catch {
        try { $res.StatusCode = 500 } catch { }
      } finally {
        $res.OutputStream.Close()
      }
    }
  }
} finally {
  if ($listener.IsListening) { $listener.Stop() }
  $listener.Close()
}
