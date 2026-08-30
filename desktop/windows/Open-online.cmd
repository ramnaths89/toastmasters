@echo off
REM Opens the live GitHub Pages hub in an Edge app window. Needs internet.
REM Smart App Control does not block this — it is a shortcut into Edge.
set EDGE=
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe
if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe
if "%EDGE%"=="" (
  echo Microsoft Edge was not found.
  pause
  exit /b 1
)
start "" "%EDGE%" --app=https://ramnaths89.github.io/toastmasters/
