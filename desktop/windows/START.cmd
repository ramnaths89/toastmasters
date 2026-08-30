@echo off
REM Starts the tools in an Edge app window. Not an .exe.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0serve.ps1"
if errorlevel 1 (
  echo Toastmasters Tools could not start.
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve.ps1"
  pause
)
