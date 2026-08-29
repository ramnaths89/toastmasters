@echo off
REM Frameless desktop window around the Toastmasters Tools hub.
cd /d "%~dp0\.."
python desktop\launch.py
if errorlevel 1 py desktop\launch.py
