@echo off
REM Launcher: calls PowerShell script to avoid CMD UTF-8 encoding issues
chcp 65001 >nul
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"
