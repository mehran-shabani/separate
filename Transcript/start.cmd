@echo off
setlocal
cd /d "%~dp0"
set "TRANSCRIPT_PYTHON=%~dp0..\.venv\Scripts\python.exe"
if not exist "%TRANSCRIPT_PYTHON%" (
  echo Project Python environment not found: ..\.venv\Scripts\python.exe
  pause
  exit /b 1
)
"%TRANSCRIPT_PYTHON%" "%~dp0app.py" %*
if errorlevel 1 pause
