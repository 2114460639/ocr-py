@echo off
REM Debug launcher: uses python.exe so you see the console / crash output.
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0run_debug.ps1"
