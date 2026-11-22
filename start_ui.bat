@echo off
setlocal
cd /d "%~dp0"
if not exist "back-end2\.venv\Scripts\python.exe" (
  echo Missing back-end2\.venv. From back-end2\ run: python -m venv .venv
  echo Then: .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 1
)
start "PrzetarGO" /D "%~dp0back-end2" cmd /k ".venv\Scripts\python.exe api.py"
echo App  http://localhost:8000/
ping -n 3 127.0.0.1 >nul
start "" http://localhost:8000/
