@echo off
setlocal
rem SETLOCAL also restores the starting folder when this script ends.
cd /d "%~dp0..\Program" || exit /b 1
rem One block, so cmd has read all of it before a ZIP update replaces this file.
(
    powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\Program\scripts\windows\update.ps1" %*
    exit /b
)
