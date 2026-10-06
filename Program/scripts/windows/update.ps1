# Updates this checkout: pulls main, then reruns install.ps1 (locked dependencies and a fresh interface build).
param([switch]$NoPause)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
Set-Location -LiteralPath $CompanionRoot

function Invoke-Git {
    param([string[]]$Arguments)
    # Git reports progress on stderr; Windows PowerShell would treat that as a failure under 'Stop'.
    $ErrorActionPreference = 'Continue'
    $output = & git @Arguments 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { throw "git $($Arguments -join ' ') failed: $($output -join ' ')" }
    return $output
}

$result = 0
try {
    Write-Host 'Prospero Companion - update'
    if (-not (Get-Command git.exe -CommandType Application -ErrorAction SilentlyContinue)) {
        throw 'Git was not found. Install Git for Windows, or update by downloading the project again.'
    }
    if ((Get-CompanionState 8775).State -eq 'running') {
        throw 'Prospero Companion is running. Close its window (or double-click stop.bat), then update again.'
    }
    $branch = [string](Invoke-Git @('rev-parse', '--abbrev-ref', 'HEAD'))
    if ($branch -ne 'main') { throw "This checkout is on '$branch'. update.bat only updates main; switch with 'git switch main' first." }
    $before = [string](Invoke-Git @('rev-parse', 'HEAD'))
    Invoke-Git @('pull', '--ff-only', 'origin', 'main') | Out-Host
    $after = [string](Invoke-Git @('rev-parse', 'HEAD'))
    if ($before -eq $after) {
        Write-Host 'Already up to date. Reinstalling to make sure everything matches.'
    } else {
        Write-Host "Updated $($before.Substring(0, 7)) to $($after.Substring(0, 7)):"
        Invoke-Git @('log', '--oneline', '--no-decorate', "$before..$after") | Out-Host
    }
    & (Join-Path $PSScriptRoot 'install.ps1') -NoPause
    if ($LASTEXITCODE -ne 0) { throw 'The reinstall failed; see above.' }
} catch {
    Write-Host "Update failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Your workspace in %LOCALAPPDATA%\ProsperoCompanion was not touched.'
    $result = 1
}
if (-not $NoPause) { Read-Host 'Press Enter to close' | Out-Null }
exit $result
