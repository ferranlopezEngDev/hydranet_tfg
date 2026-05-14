@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "VENV_DIR=%ROOT_DIR%.venv"
set "RUN_CHECKS=0"
set "REQUIRED_PYTHON_VERSION=3.11"
set "LOCAL_TOOLS_DIR=%ROOT_DIR%.tools\bin"
set "LOCAL_UV_BIN=%LOCAL_TOOLS_DIR%\uv.exe"

if /I "%~1"=="-RunChecks" (
  set "RUN_CHECKS=1"
) else if not "%~1"=="" (
  set "VENV_DIR=%~1"
)

if /I "%~2"=="-RunChecks" (
  set "RUN_CHECKS=1"
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PYTHON_EXE=py"
  set "PYTHON_ARGS=-3"
) else (
  set "PYTHON_EXE=python"
  set "PYTHON_ARGS="
)

call :ensure_python
if errorlevel 1 exit /b 1

"%PYTHON_EXE%" %PYTHON_ARGS% -m venv "%VENV_DIR%"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

"%VENV_PYTHON%" -m pip install --upgrade pip setuptools wheel
"%VENV_PYTHON%" -m pip install -e "%ROOT_DIR%"
"%VENV_PYTHON%" -m pip check
"%VENV_PYTHON%" -c "import hydranet, numpy, scipy, tkinter; print('Dependency smoke check OK.')"
if errorlevel 1 exit /b 1

if "%RUN_CHECKS%"=="1" (
  echo Running optional verification checks...
  "%VENV_PYTHON%" -m compileall "%ROOT_DIR%\src" "%ROOT_DIR%\tests"
  if errorlevel 1 exit /b 1
  "%VENV_PYTHON%" -m unittest discover -s "%ROOT_DIR%\tests" -p "test_*.py"
  if errorlevel 1 exit /b 1
)

echo MVP004 installation complete.
echo.
echo Virtual environment:
echo   %VENV_DIR%
echo.
echo Open the desktop app:
echo   "%VENV_PYTHON%" "%ROOT_DIR%src\main.py"
echo   or after activating the environment:
echo   python "%ROOT_DIR%src\main.py"
echo   or
echo   run_windows.cmd
echo   or
echo   hydranet
echo.
echo Run the technical CLI demo:
echo   "%VENV_PYTHON%" "%ROOT_DIR%src\main.py" demo
echo   or after activating the environment:
echo   hydranet demo
exit /b 0

:ensure_python
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if %ERRORLEVEL%==0 exit /b 0

echo Compatible Python not found. Bootstrapping local uv...
call :ensure_uv
if errorlevel 1 exit /b 1

echo Installing Python %REQUIRED_PYTHON_VERSION% with uv...
"%LOCAL_UV_BIN%" python install %REQUIRED_PYTHON_VERSION%
if errorlevel 1 exit /b 1

for /f "usebackq delims=" %%I in (`"%LOCAL_UV_BIN%" python find %REQUIRED_PYTHON_VERSION%`) do (
  set "PYTHON_EXE=%%I"
  set "PYTHON_ARGS="
  goto :python_found
)

echo Error: uv did not return a usable Python executable.
exit /b 1

:python_found
"%PYTHON_EXE%" %PYTHON_ARGS% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Error: the bootstrapped Python interpreter does not meet the required version.
  exit /b 1
)
exit /b 0

:ensure_uv
if exist "%LOCAL_UV_BIN%" exit /b 0

mkdir "%LOCAL_TOOLS_DIR%" >nul 2>nul
powershell -ExecutionPolicy ByPass -Command "$env:UV_INSTALL_DIR='%LOCAL_TOOLS_DIR%'; $env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/install.ps1 | iex"
if errorlevel 1 (
  echo Error: could not bootstrap uv automatically.
  exit /b 1
)

if not exist "%LOCAL_UV_BIN%" (
  echo Error: uv bootstrap completed but "%LOCAL_UV_BIN%" was not created.
  exit /b 1
)
exit /b 0
