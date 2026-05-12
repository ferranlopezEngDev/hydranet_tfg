param(
    [string]$VenvDir = ".venv"
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path (Join-Path $RootDir $VenvDir) "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Virtual environment Python not found at $PythonExe. Run install_windows.cmd first."
}

& $PythonExe (Join-Path $RootDir "src\main.py")
