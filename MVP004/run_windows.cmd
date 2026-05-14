@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "VENV_DIR=%ROOT_DIR%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
  echo Virtual environment not found. Bootstrapping MVP004 first...
  call "%ROOT_DIR%install_windows.cmd"
  if errorlevel 1 exit /b 1
)

if "%~1"=="" (
  "%VENV_PYTHON%" "%ROOT_DIR%src\main.py"
  exit /b %ERRORLEVEL%
)

"%VENV_PYTHON%" "%ROOT_DIR%src\main.py" %*
