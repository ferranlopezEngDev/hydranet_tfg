param(
    [string]$PythonLauncher = "py",
    [string]$VenvDir = ".venv"
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $RootDir $VenvDir

if (-not (Get-Command $PythonLauncher -ErrorAction SilentlyContinue)) {
    Write-Error "Python launcher '$PythonLauncher' not found. Install Python 3 or run with -PythonLauncher python."
}

Write-Host "Creating virtual environment at $VenvPath"
& $PythonLauncher -m venv $VenvPath

$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Error "Could not find virtual environment Python at $PythonExe"
}

Write-Host "Upgrading pip"
& $PythonExe -m pip install --upgrade pip

Write-Host "Installing requirements"
& $PythonExe -m pip install -r (Join-Path $RootDir "requirements.txt")

Write-Host ""
Write-Host "MVP001 installation complete."
Write-Host ""
Write-Host "Activate the environment:"
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Run the CLI menu:"
Write-Host "  python src\app_cli.py"
Write-Host ""
Write-Host "Run the full test suite:"
Write-Host "  python -m unittest discover -s test -p 'test_*.py'"
