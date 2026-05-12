param(
    [string]$PythonCommand = "",
    [string]$VenvDir = ".venv",
    [switch]$RunChecks
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $RootDir $VenvDir

function Get-PythonInvocation {
    param([string]$RequestedCommand)

    if ($RequestedCommand) {
        if (-not (Get-Command $RequestedCommand -ErrorAction SilentlyContinue)) {
            throw "Python command '$RequestedCommand' not found."
        }

        return @($RequestedCommand)
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @("py", "-3")
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return @("python")
    }

    throw "No suitable Python command found. Install Python 3.11+ or pass -PythonCommand python."
}

function Invoke-WithPython {
    param(
        [string[]]$PythonInvocation,
        [string[]]$Arguments
    )

    $Command = $PythonInvocation[0]
    $BaseArguments = @()
    if ($PythonInvocation.Count -gt 1) {
        $BaseArguments = $PythonInvocation[1..($PythonInvocation.Count - 1)]
    }

    & $Command @BaseArguments @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed: $Command $($BaseArguments + $Arguments -join ' ')"
    }
}

$PythonInvocation = Get-PythonInvocation -RequestedCommand $PythonCommand
Write-Host "Using Python command: $($PythonInvocation -join ' ')"

$VersionCheck = @'
import sys
if sys.version_info < (3, 11):
    raise SystemExit(
        "Python 3.11 or newer is required for MVP002. "
        f"Detected: {sys.version.split()[0]}"
    )
print(f"Using Python {sys.version.split()[0]}")
'@
Invoke-WithPython -PythonInvocation $PythonInvocation -Arguments @("-c", $VersionCheck)

Write-Host "Creating virtual environment at $VenvPath"
Invoke-WithPython -PythonInvocation $PythonInvocation -Arguments @("-m", "venv", $VenvPath)

$PythonExe = Join-Path $VenvPath "Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Could not find virtual environment Python at $PythonExe"
}

Write-Host "Upgrading pip, setuptools and wheel"
& $PythonExe -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip, setuptools and wheel."
}

Write-Host "Installing requirements"
& $PythonExe -m pip install -r (Join-Path $RootDir "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install requirements."
}

Write-Host "Checking installed packages"
& $PythonExe -m pip check
if ($LASTEXITCODE -ne 0) {
    throw "pip check reported dependency issues."
}

$SmokeCheck = @'
import importlib

required_modules = ("numpy", "scipy", "matplotlib", "tkinter")
missing_modules = []

for module_name in required_modules:
    try:
        importlib.import_module(module_name)
    except Exception as exc:
        missing_modules.append((module_name, str(exc)))

if missing_modules:
    print("Dependency smoke check failed:")
    for module_name, error_text in missing_modules:
        print(f"  - {module_name}: {error_text}")
    raise SystemExit(1)

print("Dependency smoke check OK.")
'@
& $PythonExe -c $SmokeCheck
if ($LASTEXITCODE -ne 0) {
    throw "Dependency smoke check failed."
}

if ($RunChecks) {
    Write-Host "Running optional verification checks"
    & $PythonExe -m compileall (Join-Path $RootDir "src") (Join-Path $RootDir "test")
    if ($LASTEXITCODE -ne 0) {
        throw "compileall failed."
    }

    Push-Location $RootDir
    try {
        & $PythonExe -m unittest discover -s test -p test_*.py
        if ($LASTEXITCODE -ne 0) {
            throw "unittest suite failed."
        }
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "MVP002 installation complete."
Write-Host ""
Write-Host "Activate the environment:"
Write-Host "  .venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Run the GUI:"
Write-Host "  .\run_windows.cmd"
Write-Host "  or"
Write-Host "  & '$PythonExe' '$RootDir\src\main.py'"
Write-Host ""
Write-Host "Optional full verification:"
Write-Host "  .\install_windows.cmd -RunChecks"
