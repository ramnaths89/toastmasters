@echo off
REM Installs the Programme Sheet Builder for this Windows user:
REM   1. copies this folder to %LOCALAPPDATA%\ProgrammeSheet\app
REM   2. puts a "Programme Sheet Builder" shortcut on the Desktop and in the
REM      Start menu (the shortcut file ships in this folder, ready made)
REM Plain cmd only - no PowerShell, no .exe - so Smart App Control lets it run.
REM Run it again after downloading a newer zip; it replaces the old copy.
setlocal
set "SRC=%~dp0"
set "SRC=%SRC:~0,-1%"
set "DST=%LOCALAPPDATA%\ProgrammeSheet\app"
set "LNK=Programme Sheet Builder.lnk"

if not exist "%SRC%\index.html" (
  echo index.html is missing next to Install.cmd. Extract the whole ProgrammeSheet folder first.
  pause
  exit /b 1
)

if /i "%SRC%"=="%DST%" goto shortcuts
if exist "%DST%" rmdir /s /q "%DST%"
mkdir "%DST%" 2>nul
xcopy "%SRC%\*" "%DST%\" /e /i /y /q >nul
if errorlevel 1 (
  echo Could not copy the files to %DST%.
  pause
  exit /b 1
)

:shortcuts
REM The real Desktop folder - it is often redirected into OneDrive.
set "DESKTOP="
for /f "tokens=2,*" %%A in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders" /v Desktop 2^>nul ^| find /i "Desktop"') do set "DESKTOP=%%B"
if not defined DESKTOP set "DESKTOP=%USERPROFILE%\Desktop"
set "PROGRAMS=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not exist "%PROGRAMS%" mkdir "%PROGRAMS%" 2>nul

copy /y "%DST%\%LNK%" "%DESKTOP%\%LNK%" >nul
copy /y "%DST%\%LNK%" "%PROGRAMS%\%LNK%" >nul

echo.
echo Installed for this Windows user.
echo.
echo   Desktop shortcut:  Programme Sheet Builder
echo   Start menu:        Programme Sheet Builder
echo   Files:             %DST%
echo.
echo If the shortcut ever fails, double-click START.cmd in that folder instead.
echo To share with someone else, send ProgrammeSheet-portable.zip (not the .exe).
echo.
pause
exit /b 0
