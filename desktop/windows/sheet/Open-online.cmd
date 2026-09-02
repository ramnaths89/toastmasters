@echo off
REM Opens the live Programme Sheet Builder from GitHub Pages in an Edge app
REM window. Needs internet. Smart App Control does not block this - it is a
REM shortcut into Microsoft Edge.
set "EDGE="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined EDGE if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined EDGE (
  echo Microsoft Edge was not found.
  pause
  exit /b 1
)
start "" "%EDGE%" --app=https://ramnaths89.github.io/toastmasters/programme-sheet-builder/
