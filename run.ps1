# OCR Translator - launcher
# 默认用 pythonw.exe 启动（无控制台黑框）。
# 若程序启动后立即闪退，可把 $useConsole = $true，
# 或打开同目录下的 run.log / run_err.log 查看崩溃原因。

$ErrorActionPreference = "Stop"

$useConsole = $false   # 调试时改 $true 可看控制台输出

$workDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$logOut = Join-Path $workDir "run.log"
$logErr = Join-Path $workDir "run_err.log"

if ($useConsole) {
    $venvPython = Join-Path $workDir ".venv\Scripts\python.exe"
} else {
    $venvPython = Join-Path $workDir ".venv\Scripts\pythonw.exe"
}
$mainPy = Join-Path $workDir "main.py"

if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Virtual environment not found. Run install.bat first."
    Read-Host "Press Enter to exit"
    exit 1
}

# 清空上次日志
if (Test-Path $logOut) { Remove-Item $logOut }
if (Test-Path $logErr) { Remove-Item $logErr }

if ($useConsole) {
    # 有控制台模式：直接跑，用户能看到错误
    $proc = Start-Process -FilePath $venvPython -ArgumentList $mainPy `
        -WorkingDirectory $workDir -RedirectStandardOutput $logOut -RedirectStandardError $logErr `
        -PassThru -Wait
    if ($proc.ExitCode -ne 0 -and (Test-Path $logErr)) {
        Write-Host "--- stderr ---"
        Get-Content $logErr
        Read-Host "Press Enter"
    }
} else {
    # 无控制台模式（默认）：后台启动 + 日志落盘
    $proc = Start-Process -FilePath $venvPython -ArgumentList $mainPy `
        -WorkingDirectory $workDir -RedirectStandardOutput $logOut -RedirectStandardError $logErr `
        -WindowStyle Hidden -PassThru
    Write-Host "App started (PID: $($proc.Id)). Logs: run.log / run_err.log"
}
