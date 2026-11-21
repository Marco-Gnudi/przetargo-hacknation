@echo off
setlocal
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Missing backend\.venv. From backend\ run: python -m venv .venv
  echo Then: .venv\Scripts\python.exe -m pip install -r requirements.txt
  exit /b 1
)
start "PrzetarGO API" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn odwolania.api:app --host 127.0.0.1 --port 8000"
start "PrzetarGO UI" /D "%~dp0front-end" cmd /k "python -m http.server 8080 --bind 127.0.0.1"
echo API  http://127.0.0.1:8000/api/health
echo UI   http://127.0.0.1:8080/
