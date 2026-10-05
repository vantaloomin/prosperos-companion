# Adapted from prosperos-study start.ps1 at bbcbde4: Companion launcher module and port.
param([switch]$NoBrowser, [switch]$NoPause, [ValidateRange(1024, 65535)][int]$Port = 8775)
$ErrorActionPreference = 'Stop'
# npm, Vite and Python write UTF-8; decode their captured output as UTF-8 so symbols such as the
# build's checkmark render instead of mojibake. A host without a console may refuse; that is fine.
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch { }
Set-Location -LiteralPath $PSScriptRoot
$result = 0
try {
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'Dependencies are missing. Double-click install.bat first.' }
    if (-not (Test-Path -LiteralPath 'dist\index.html')) { throw 'The interface is not built. Double-click install.bat first.' }
    $arguments = @('-m', 'companion.launch', '--port', [string]$Port)
    if ($NoBrowser) { $arguments += '--no-browser' }
    # The server logs to stderr; judge it by exit code, not by what it writes (see install.ps1).
    $ErrorActionPreference = 'Continue'
    & $python @arguments
    $result = $LASTEXITCODE
} catch {
    Write-Host "Launch failed: $($_.Exception.Message)" -ForegroundColor Red
    $result = 1
}
if ($result -ne 0 -and -not $NoPause) { Read-Host 'Press Enter to close' | Out-Null }
exit $result
