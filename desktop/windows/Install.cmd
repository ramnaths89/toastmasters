@echo off
REM Copies this folder onto this PC and puts a shortcut on the Desktop
REM and in the Start menu. Needs PowerShell unconstrained: under Smart App
REM Control this fails - use ProgrammeSheet-portable.zip or the website there.
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install.ps1"
if errorlevel 1 pause
