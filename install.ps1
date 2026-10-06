# A bridge for checkouts from before the scripts moved into Windows\, Mac\ and Program\ (October 2026).
# The update.bat they have pulls the new layout and then runs this file, which hands over to the new
# install. Delete it once no checkout from before the move is left to update.
param([switch]$NoPause)
& (Join-Path $PSScriptRoot 'Program\scripts\windows\install.ps1') -NoPause:$NoPause
exit $LASTEXITCODE
