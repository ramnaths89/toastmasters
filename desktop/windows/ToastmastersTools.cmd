@echo off
REM Double-clickable launcher. Not an .exe, so Smart App Control does not
REM block it the way it blocks the unsigned ToastmastersTools.exe.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve.ps1"
if errorlevel 1 pause
