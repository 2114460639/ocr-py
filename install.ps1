# OCR Translator - installer (target machine)
# PowerShell natively handles UTF-8; all messages use ASCII to avoid any
# platform codepage issues. Rich Chinese UI strings live in Python instead.

$ErrorActionPreference = "Stop"

Write-Host "========================================================"
Write-Host "  OCR Translator - Installer"
Write-Host "  Dependencies are installed from pypi.org"
Write-Host "  Models are bundled in this package"
Write-Host "========================================================"
Write-Host ""

$workDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workDir

# ---- 1. Detect Python ----
Write-Host "[1/4] Detecting Python ..."
$pyCmd = $null
try {
    py -3.12 --version 2>$null | Out-Null
    $pyCmd = "py -3.12"
} catch {
    try {
        python --version 2>$null | Out-Null
        $pyCmd = "python"
    } catch {
        Write-Host "[ERROR] Python not found. Install Python 3.10-3.12 from python.org"
        Write-Host "        Make sure to check 'Add Python to PATH' during install."
        Read-Host "Press Enter to exit"
        exit 1
    }
}
Write-Host "      Using: $pyCmd"
Invoke-Expression "$pyCmd --version"
Write-Host ""

# ---- 2. Create venv ----
Write-Host "[2/4] Creating virtual environment .venv ..."
$venvPython = Join-Path $workDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Invoke-Expression "$pyCmd -m venv .venv"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment."
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "      Virtual environment created."
} else {
    Write-Host "      Virtual environment already exists, skipping."
}
Write-Host ""

# ---- 3. Install dependencies (from pypi.org) ----
Write-Host "[3/4] Installing dependencies from pypi.org (this may take a while) ..."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] pip upgrade failed."
    Read-Host "Press Enter to exit"
    exit 1
}
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Dependency installation failed. Check network to pypi.org."
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "      Dependencies installed."
Write-Host ""

# ---- 4. Verify environment & model ----
Write-Host "[4/4] Verifying environment ..."
& $venvPython check_env.py
Write-Host ""

# Check translator model files
$modelFile = Join-Path $workDir "models\translator\Qwen2.5-1.5B-Instruct-openvino\openvino_model.xml"
if (-not (Test-Path $modelFile)) {
    Write-Host "[WARN] Translator model is missing!"
    Write-Host "       Make sure you copied the models\translator\ directory."
    Write-Host "       Or run prepare_offline.py on the dev machine first."
} else {
    Write-Host "[OK] Translator model found."
}

Write-Host ""
Write-Host "========================================================"
Write-Host "  Install complete! Double-click run.bat to start."
Write-Host "========================================================"
Write-Host ""
Read-Host "Press Enter to exit"
