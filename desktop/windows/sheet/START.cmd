@echo off
REM Opens the Programme Sheet Builder in a Microsoft Edge app window.
REM No .exe, no PowerShell, no local server: the page is opened straight from
REM this folder. Smart App Control does not police cmd.exe, and Edge is signed
REM by Microsoft, so this runs where the unsigned .exe cannot.
REM Close the window to quit. Your work is saved inside the Edge profile at
REM %LOCALAPPDATA%\ProgrammeSheet\edge-profile for this Windows user.
setlocal
cd /d "%~dp0"

set "PAGE=%~dp0index.html"
if not exist "%PAGE%" (
  echo index.html is missing. Extract the whole ProgrammeSheet folder, then run this again.
  pause
  exit /b 1
)
set "PAGE=%PAGE:\=/%"
set "PROFILE=%LOCALAPPDATA%\ProgrammeSheet\edge-profile"

set "BROWSER="
if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set "BROWSER=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER (
  echo Microsoft Edge or Google Chrome was not found. Install Microsoft Edge, then run this again.
  pause
  exit /b 1
)

if not exist "%PROFILE%" mkdir "%PROFILE%"
start "" "%BROWSER%" --app="file:///%PAGE%" --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check
exit /b 0
