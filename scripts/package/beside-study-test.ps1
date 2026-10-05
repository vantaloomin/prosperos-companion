<#
.SYNOPSIS
Runs the installed Companion beside a running Prospero's Study (PRD "Standalone delivery").

.DESCRIPTION
Starts the Study from its checkout on its own port 8765, installs the Companion setup, and checks
that the two never collide: a Companion pointed at the Study's port refuses and stops nothing, the
Companion launches on 8775 while the Study keeps answering, each keeps its data in its own place,
and the Study's database never gains the Companion's identity marker. Used by CI.
#>
param(
  [Parameter(Mandatory = $true)][string]$Setup,
  [Parameter(Mandatory = $true)][string]$Study
)
$ErrorActionPreference = 'Stop'
$Setup = (Resolve-Path -LiteralPath $Setup).Path
$Study = (Resolve-Path -LiteralPath $Study).Path
$installed = Join-Path $env:LOCALAPPDATA 'Programs\Prospero Companion'
$workspace = Join-Path $env:LOCALAPPDATA 'ProsperoCompanion'
$studyData = Join-Path $Study 'data'

function Check([bool]$condition, [string]$message) {
  if (-not $condition) { throw $message }
  Write-Host "ok  $message"
}

function StudyHealth {
  try { return Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2 } catch { return $null }
}

$studyLog = Join-Path ([System.IO.Path]::GetTempPath()) 'study.log'
$studyApp = Start-Process -FilePath (Join-Path $Study '.venv\Scripts\python.exe') -ArgumentList 'scripts\launch_interface.py', '--no-browser' `
  -WorkingDirectory $Study -RedirectStandardOutput $studyLog -PassThru -WindowStyle Hidden
try {
  $health = $null
  foreach ($attempt in 1..120) { $health = StudyHealth; if ($health) { break }; Start-Sleep -Milliseconds 500 }
  if (-not $health) { Get-Content -LiteralPath $studyLog -ErrorAction SilentlyContinue; throw 'The Study did not start.' }
  Check ($health.application -eq 'Roleplay') "Prospero's Study runs on 8765"

  $process = Start-Process -FilePath $Setup -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CURRENTUSER' -PassThru -Wait
  Check ($process.ExitCode -eq 0) 'the Companion installs while the Study runs'

  $launcher = Join-Path $installed 'Prospero Companion.cmd'
  $refused = & $env:ComSpec /d /c "`"$launcher`" --port 8765 --no-browser" 2>&1 | Out-String
  Check ($LASTEXITCODE -ne 0 -and $refused -match 'Nothing was stopped') 'a Companion pointed at the Study port refuses and stops nothing'
  Check ((StudyHealth).application -eq 'Roleplay') 'the Study still answers after that refusal'

  & (Join-Path $PSHOME 'pwsh.exe') -NoProfile -File (Join-Path $PSScriptRoot 'smoke-test.ps1') -Bundle $installed -StudyRunning
  if ($LASTEXITCODE -ne 0) { throw 'The Companion failed its smoke test beside the Study.' }

  Check (Test-Path -LiteralPath (Join-Path $studyData 'roleplay.sqlite3')) "the Study keeps its database in its own data folder"
  $studyFiles = @(Get-ChildItem -LiteralPath $studyData -Recurse -File | ForEach-Object { $_.Name })
  Check (-not ($studyFiles | Where-Object { $_ -like 'companion*' })) "the Study's data folder holds no Companion files"
  $companionFiles = @(Get-ChildItem -LiteralPath $workspace -Recurse -File | ForEach-Object { $_.Name })
  Check (-not ($companionFiles | Where-Object { $_ -like 'roleplay*' })) "the Companion's workspace holds no Study files"
  $probe = "import sqlite3,sys; c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro', uri=True); " +
           "print(','.join(r[0] for r in c.execute(`"SELECT name FROM sqlite_master WHERE type='table'`")))"
  $tables = & (Join-Path $installed 'runtime\python.exe') -I -c $probe (Join-Path $studyData 'roleplay.sqlite3')
  Check ($LASTEXITCODE -eq 0 -and $tables -and $tables -notmatch 'app_identity') "the Study's database never gains the Companion marker"
} finally {
  & "$env:SystemRoot\System32\taskkill.exe" /T /F /PID $studyApp.Id | Out-Null
}
Write-Host 'Beside-the-Study test passed.'
