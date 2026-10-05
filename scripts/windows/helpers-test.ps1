<#
.SYNOPSIS
Exercises the checkout helpers (status, stop, create-shortcut, dev, update) after install.ps1. Used by CI.

.DESCRIPTION
Runs each helper through its .bat wrapper where it can, so the wrappers are tested too. Expects
install.ps1 to have finished and COMPANION_DATA_DIR to point at a scratch workspace. The update
check rewires this checkout's origin to a local repository, so run it on a throwaway checkout only.
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Set-Location -LiteralPath $CompanionRoot

function Check([bool]$condition, [string]$message) {
  if (-not $condition) { throw $message }
  Write-Host "ok  $message"
}

function Invoke-Bat([string]$Name, [string[]]$Arguments) {
  & cmd.exe /d /c (Join-Path $CompanionRoot $Name) -NoPause @Arguments | Out-Host
  return $LASTEXITCODE
}

function Wait-State([string]$Expected, [int]$Port = 8775) {
  foreach ($attempt in 1..120) {
    if ((Get-CompanionState $Port).State -eq $Expected) { return $true }
    Start-Sleep -Milliseconds 250
  }
  return $false
}

function Get-Page([string]$Url) {
  $request = [System.Net.WebRequest]::Create($Url)
  $request.Proxy = $null
  $request.Timeout = 3000
  $response = $request.GetResponse()
  try { return (New-Object System.IO.StreamReader($response.GetResponseStream())).ReadToEnd() } finally { $response.Close() }
}

$temp = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [IO.Path]::GetTempPath() }

# status and stop
Check ((Invoke-Bat 'status.bat') -eq 1) 'status.bat reports a stopped Companion with exit code 1'
Check ((Invoke-Bat 'stop.bat') -eq 0) 'stop.bat with nothing running succeeds and stops nothing'
$app = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $CompanionRoot 'start.ps1'), '-NoBrowser', '-NoPause' -PassThru
try {
  Check (Wait-State 'running') 'launch answers on 8775'
  Check ((Invoke-Bat 'status.bat') -eq 0) 'status.bat reports the running Companion with exit code 0'
  Check ((Invoke-Bat 'stop.bat') -eq 0) 'stop.bat stops the running Companion'
  Check ((Get-CompanionState 8775).State -eq 'stopped') 'port 8775 is free after stop.bat'
} finally { if (-not $app.HasExited) { & taskkill.exe /PID $app.Id /T /F | Out-Null } }

# Another program on the port is reported and never stopped.
$python = Join-Path $CompanionRoot '.venv\Scripts\python.exe'
$foreign = Start-Process -FilePath $python -ArgumentList '-m', 'http.server', '8790', '--bind', '127.0.0.1' -PassThru -WindowStyle Hidden
try {
  Check (Wait-State 'foreign' 8790) 'a foreign server holds 8790'
  Check ((Invoke-Bat 'status.bat' @('-Port', '8790')) -eq 2) 'status.bat reports a port held by another program with exit code 2'
  Check ((Invoke-Bat 'stop.bat' @('-Port', '8790')) -eq 1) 'stop.bat refuses to stop another program'
  Check (-not $foreign.HasExited) 'the other program is still running'
} finally { if (-not $foreign.HasExited) { Stop-Process -Id $foreign.Id -Force } }

# create-shortcut
$desktop = Join-Path $temp 'desktop'
New-Item -ItemType Directory -Force -Path $desktop | Out-Null
Check ((Invoke-Bat 'create-shortcut.bat' @('-Destination', $desktop)) -eq 0) 'create-shortcut.bat succeeds'
$link = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'Prospero Companion.lnk'))
Check ($link.TargetPath -eq (Join-Path $CompanionRoot 'launch.bat')) 'the shortcut starts this checkout''s launch.bat'
$other = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'Prospero Companion.lnk'))
$other.TargetPath = "$env:SystemRoot\System32\notepad.exe"
$other.Save()
Check ((Invoke-Bat 'create-shortcut.bat' @('-Destination', $desktop)) -eq 0) 'create-shortcut.bat succeeds beside an installed app''s shortcut'
Check ((New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'Prospero Companion.lnk')).TargetPath -like '*notepad.exe') 'the existing shortcut is left alone'
Check (Test-Path -LiteralPath (Join-Path $desktop 'Prospero Companion (checkout).lnk')) 'the checkout shortcut gets its own name'

# dev: backend plus Vite, with /api forwarded to the backend
$dev = Start-Process -FilePath 'powershell.exe' -ArgumentList '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'dev.ps1'), '-NoBrowser' -PassThru
try {
  Check (Wait-State 'running') 'dev mode starts the backend on 8775'
  $page = $null
  foreach ($attempt in 1..120) {
    try { $page = Get-Page 'http://127.0.0.1:5175/'; break } catch { Start-Sleep -Milliseconds 500 }
  }
  Check ($page -match 'Prospero Companion') 'Vite serves the interface on 5175'
  Check ((Get-Page 'http://127.0.0.1:5175/api/health' | ConvertFrom-Json).app_id -eq $CompanionAppId) 'Vite forwards /api to the backend'
} finally { & taskkill.exe /PID $dev.Id /T /F | Out-Null }
Check (Wait-State 'stopped') 'closing dev mode stops its backend'

# update: fast-forward from a local origin, then reinstall. CI checkouts are shallow, so the
# local origin accepts shallow pushes.
function Invoke-TestGit([string[]]$Arguments) {
  & git @Arguments | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed" }
}
Invoke-TestGit @('config', '--global', 'user.email', 'ci@example.invalid')
Invoke-TestGit @('config', '--global', 'user.name', 'CI')
$remote = Join-Path $temp 'update-origin.git'
$clone = Join-Path $temp 'update-clone'
Invoke-TestGit @('init', '--quiet', '--bare', $remote)
Invoke-TestGit @('-C', $remote, 'config', 'receive.shallowUpdate', 'true')
Invoke-TestGit @('checkout', '--quiet', '-B', 'main')
Invoke-TestGit @('push', '--quiet', $remote, 'HEAD:refs/heads/main')
Invoke-TestGit @('clone', '--quiet', '--branch', 'main', $remote, $clone)
Set-Content -LiteralPath (Join-Path $clone 'update-marker.txt') -Value 'pulled'
Invoke-TestGit @('-C', $clone, 'add', 'update-marker.txt')
Invoke-TestGit @('-C', $clone, 'commit', '--quiet', '-m', 'Marker for the update test')
Invoke-TestGit @('-C', $clone, 'push', '--quiet', 'origin', 'main')
Invoke-TestGit @('remote', 'set-url', 'origin', $remote)
Check ((Invoke-Bat 'update.bat') -eq 0) 'update.bat pulls main and reinstalls'
Check (Test-Path -LiteralPath (Join-Path $CompanionRoot 'update-marker.txt')) 'the new commit was pulled'
Check (Test-Path -LiteralPath 'dist\index.html') 'the interface was rebuilt'
$app = Start-Process -FilePath $python -ArgumentList '-m', 'companion.launch', '--no-browser' -PassThru -NoNewWindow
try {
  Check (Wait-State 'running') 'the Companion launches after updating'
  Check ((Invoke-Bat 'update.bat') -eq 1) 'update.bat refuses while the Companion runs'
} finally { & taskkill.exe /PID $app.Id /T /F | Out-Null }
Invoke-TestGit @('checkout', '--quiet', '-b', 'elsewhere')
Check ((Invoke-Bat 'update.bat') -eq 1) 'update.bat refuses a branch other than main'

# The last check expects exit code 1 from update.bat; don't let it become this script's result.
Write-Host 'All checkout helper checks passed.'
exit 0
