@echo off
REM Copies this folder onto this PC and puts a shortcut on the Desktop
REM and in the Start menu. Share the zip or this folder; do not share the .exe
REM if the other PC has Smart App Control.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1"
if errorlevel 1 pause
