# Adapted from prosperos-study install.ps1 at bbcbde4: Companion name and dependency checks.
param([switch]$NoPause, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
# npm, Vite and Python write UTF-8; decode their captured output as UTF-8 so symbols such as the
# build's checkmark render instead of mojibake. A host without a console may refuse; that is fine.
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch { }
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Checked {
    param([string]$Executable, [string[]]$Arguments)
    # Judge tools by exit code. When this window's stderr is captured, Windows PowerShell 5.1 turns
    # npm and pip notices into errors, which 'Stop' would make fatal.
    $ErrorActionPreference = 'Continue'
    & $Executable @Arguments 2>&1 | ForEach-Object { "$_" } | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "$Executable failed with exit code $LASTEXITCODE. Fix the error above and rerun install.bat." }
}

function Find-Executable {
    param([string]$Name)
    $command = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) { return $command.Source }
}

function Test-Python {
    param([string]$Executable, [string[]]$Prefix = @())
    $ErrorActionPreference = 'Continue'
    if (-not $Executable -or -not (Test-Path -LiteralPath $Executable)) { return }
    if ($Executable -match 'Microsoft\\WindowsApps\\python[0-9.]*\.exe$') { return }
    try {
        $result = & $Executable @Prefix -c 'import sys; sys.exit(1) if sys.version_info < (3,12) else print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0) { return [string]$result }
    } catch { return }
}

function Find-Python {
    $candidates = @(
        (Join-Path $PSScriptRoot '.venv\Scripts\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Find-Executable 'python.exe')
    )
    foreach ($candidate in $candidates) {
        $found = Test-Python $candidate
        if ($found) { return $found }
    }
    return Test-Python (Find-Executable 'py.exe') @('-3.12')
}

function Find-Node {
    $executable = Find-Executable 'node.exe'
    if (-not $executable) { return }
    $ErrorActionPreference = 'Continue'
    try {
        $version = & $executable -p 'process.versions.node' 2>$null
        if ($LASTEXITCODE -eq 0 -and [version]$version -ge [version]'22.12.0') { return $executable }
    } catch { return }
}

function Install-Prerequisite {
    param([string]$PackageId)
    $winget = Find-Executable 'winget.exe'
    if (-not $winget) {
        throw 'WinGet is unavailable. Install App Installer from Microsoft Store, or install Python 3.12+ and Node.js 22.12+ manually, then rerun install.bat.'
    }
    Write-Host "Installing missing prerequisite: $PackageId. Windows may request administrator approval."
    Invoke-Checked $winget @('install', '--exact', '--id', $PackageId, '--source', 'winget', '--silent', '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity')
    $machinePath = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machinePath;$userPath;$env:Path"
}

function Get-Prerequisites {
    $python = Find-Python
    if (-not $python -and -not $CheckOnly) { Install-Prerequisite 'Python.Python.3.12'; $python = Find-Python }
    if (-not $python) { throw 'Python 3.12+ was not found. Reopen this installer after installing Python.' }
    $node = Find-Node
    if (-not $node -and -not $CheckOnly) { Install-Prerequisite 'OpenJS.NodeJS.LTS'; $node = Find-Node }
    if (-not $node) { throw 'Node.js 22.12+ was not found. Reopen this installer after installing Node.js.' }
    $npm = Join-Path (Split-Path -Parent $node) 'npm.cmd'
    if (-not (Test-Path -LiteralPath $npm)) { throw 'npm.cmd is missing beside Node.js. Repair the Node.js installation and retry.' }
    return @{ Python = $python; Npm = $npm }
}

function Test-ProjectInstallation {
    param([string]$Python, [string]$Npm)
    if (-not (Test-Path -LiteralPath $Python)) { throw 'The project environment is missing. Run install.bat first.' }
    Invoke-Checked $Python @('-m', 'pip', 'check')
    Invoke-Checked $Python @('-c', 'import fastapi, uvicorn, httpx, pydantic, keyring')
    Invoke-Checked $Npm @('ls', '--depth=0')
    if (-not (Test-Path -LiteralPath 'dist\index.html')) { throw 'The interface has not been built. Run install.bat.' }
}

function Install-Project {
    param([hashtable]$Runtime)
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath '.venv') {
        if (-not (Test-Python $python)) { throw 'The existing .venv is broken or uses an older Python. Rename that environment folder and rerun install.bat. Your companion''s data lives separately in %LOCALAPPDATA%\ProsperoCompanion.' }
    } else {
        Invoke-Checked $Runtime.Python @('-m', 'venv', '.venv')
    }
    Invoke-Checked $python @('-m', 'pip', 'install', '--disable-pip-version-check', '--no-input', '-r', 'requirements.lock.txt')
    Invoke-Checked $Runtime.Npm @('ci', '--no-audit', '--no-fund')
    Invoke-Checked $Runtime.Npm @('run', 'build')
    Test-ProjectInstallation $python $Runtime.Npm
}

$result = 0
try {
    Write-Host "Prospero Companion - dependency setup"
    $runtime = Get-Prerequisites
    if ($CheckOnly) {
        Test-ProjectInstallation (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') $runtime.Npm
    } else {
        Install-Project $runtime
    }
    Write-Host 'Ready. Double-click launch.bat to open Prospero Companion.' -ForegroundColor Green
    Write-Host 'Connect a model in Settings inside the app. Nothing is downloaded until you choose to.'
} catch {
    Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    $result = 1
}
if (-not $NoPause) { Read-Host 'Press Enter to close' | Out-Null }
exit $result
