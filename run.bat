@echo off
REM Launcher: calls PowerShell to start app with pythonw (no console window)
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0run.ps1"
