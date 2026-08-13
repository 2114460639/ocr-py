# OCR Translator - DEBUG launcher
# Opens a console window so you can see tracebacks / crashes immediately.

$ErrorActionPreference = "Stop"

$workDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPython = Join-Path $workDir ".venv\Scripts\python.exe"
$mainPy = Join-Path $workDir "main.py"

if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Virtual environment not found. Run install.bat first."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[DEBUG] Launching with console. Press Ctrl+C to stop."
& $venvPython $mainPy
if ($LASTEXITCODE -ne 0) {
    Write-Host "[DEBUG] Exit code: $LASTEXITCODE"
    Read-Host "Press Enter to exit"
}
