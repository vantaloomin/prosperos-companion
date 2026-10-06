<#
.SYNOPSIS
Updates a copy of the checkout from before the layout move with that copy's own update.bat. Used by CI.

.DESCRIPTION
An existing checkout first meets the Windows/Mac/Program layout through its old update.bat: the old
update.ps1 pulls, then runs the top-level install.ps1, which hands over to the new install. This makes
such a copy (with an old install's leftovers and a desktop shortcut to the old launch.bat), updates it
and checks the result. Needs the full history (fetch-depth 0) and nothing running on 8775.
#>
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
# The last commit with the scripts and code at the top of the checkout.
$BeforeMove = 'f7c3b70d1529ad35746b11fb0cf22ae52ac0ad6c'

function Check([bool]$condition, [string]$message) {
  if (-not $condition) { throw $message }
  Write-Host "ok  $message"
}

function Invoke-TestGit([string[]]$Arguments) {
  & git @Arguments | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed" }
}

$temp = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [IO.Path]::GetTempPath() }
$remote = Join-Path $temp 'move-origin.git'
$copy = Join-Path $temp 'Old Checkout'
Invoke-TestGit @('init', '--quiet', '--bare', $remote)
Invoke-TestGit @('-C', $CheckoutRoot, 'push', '--quiet', $remote, 'HEAD:refs/heads/main')
Invoke-TestGit @('clone', '--quiet', '--branch', 'main', $remote, $copy)
Invoke-TestGit @('-C', $copy, 'reset', '--quiet', '--hard', $BeforeMove)
Check (Test-Path -LiteralPath (Join-Path $copy 'update.bat')) 'the copy has the old layout'

# What an install from before the move leaves at the top, and the shortcut create-shortcut.bat made.
foreach ($leftover in '.venv\pyvenv.cfg', 'node_modules\left\package.json', 'dist\index.html', 'companion\__pycache__\old.pyc') {
  $path = Join-Path $copy $leftover
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $path) | Out-Null
  Set-Content -LiteralPath $path -Value 'left by the old install'
}
New-Item -ItemType Directory -Force -Path (Join-Path $copy 'private-cities') | Out-Null
Set-Content -LiteralPath (Join-Path $copy 'private-cities\mine.json') -Value '{}'
$desktop = [Environment]::GetFolderPath('Desktop')
New-Item -ItemType Directory -Force -Path $desktop | Out-Null
$linkPath = Join-Path $desktop 'Prospero Companion (move test).lnk'
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($linkPath)
$link.TargetPath = Join-Path $copy 'launch.bat'
$link.WorkingDirectory = $copy
$link.Save()

try {
  # cmd.exe may report that update.bat vanished once the pull removed it, so judge by what happened.
  $previous = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  $output = & cmd.exe /d /c (Join-Path $copy 'update.bat') -NoPause 2>&1 | ForEach-Object { "$_" }
  $ErrorActionPreference = $previous
  $output | Out-Host
  $text = $output -join "`n"
  Check ($text -notmatch 'Update failed') 'the old update.bat did not report a failure'
  Check ($text -match 'Ready\.') 'the new install finished'
  Check ($text -match 'now live in the Windows folder') 'the update says where the scripts went'
  Check (Test-Path -LiteralPath (Join-Path $copy 'Windows\launch.bat')) 'the copy has the new layout'
  Check (-not (Test-Path -LiteralPath (Join-Path $copy 'launch.bat'))) 'the old launch.bat is gone'
  Check (Test-Path -LiteralPath (Join-Path $copy 'Program\dist\index.html')) 'the interface was built inside Program'
  foreach ($name in '.venv', 'node_modules', 'dist', 'companion') {
    Check (-not (Test-Path -LiteralPath (Join-Path $copy $name))) "the old top-level $name was tidied away"
  }
  Check (Test-Path -LiteralPath (Join-Path $copy 'Program\private-cities\mine.json')) 'private-cities moved into Program'
  Check ($shell.CreateShortcut($linkPath).TargetPath -eq (Join-Path $copy 'Windows\launch.bat')) 'the desktop shortcut starts Windows\launch.bat'
  Check (-not (& git -C $copy status --porcelain)) 'nothing untracked or changed is left in the copy'

  $python = Join-Path $copy 'Program\.venv\Scripts\python.exe'
  $app = Start-Process -FilePath $python -ArgumentList '-m', 'companion.launch', '--no-browser' -WorkingDirectory (Join-Path $copy 'Program') -PassThru -NoNewWindow
  try {
    $state = $null
    foreach ($attempt in 1..120) {
      $state = (Get-CompanionState 8775).State
      if ($state -eq 'running') { break }
      Start-Sleep -Milliseconds 250
    }
    Check ($state -eq 'running') 'the updated copy launches'
  } finally { & taskkill.exe /PID $app.Id /T /F | Out-Null }
} finally {
  Remove-Item -LiteralPath $linkPath -Force -ErrorAction SilentlyContinue
}
Write-Host 'The update across the layout move works.'
