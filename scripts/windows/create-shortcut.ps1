# Puts a "Prospero Companion" shortcut to this checkout's launch.bat on the desktop.
param([switch]$NoPause, [string]$Destination = [Environment]::GetFolderPath('Desktop'))
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$result = 0
try {
    $target = Join-Path $CompanionRoot 'launch.bat'
    $shell = New-Object -ComObject WScript.Shell
    $path = Join-Path $Destination 'Prospero Companion.lnk'
    # The installed app may already own that name; never repoint its shortcut at the checkout.
    if ((Test-Path -LiteralPath $path) -and $shell.CreateShortcut($path).TargetPath -ne $target) {
        $path = Join-Path $Destination 'Prospero Companion (checkout).lnk'
    }
    $shortcut = $shell.CreateShortcut($path)
    $shortcut.TargetPath = $target
    $shortcut.WorkingDirectory = $CompanionRoot
    $shortcut.Description = 'Start Prospero Companion from this checkout'
    $shortcut.Save()
    Write-Host "Created $path" -ForegroundColor Green
} catch {
    Write-Host "Shortcut failed: $($_.Exception.Message)" -ForegroundColor Red
    $result = 1
}
if (-not $NoPause) { Read-Host 'Press Enter to close' | Out-Null }
exit $result
