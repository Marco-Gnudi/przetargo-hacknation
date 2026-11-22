@echo off
rem PrzetarGO for Windows.
rem   start.bat               set up (first run only) and open the web page on http://127.0.0.1:8000
rem   start.bat batch [args]  set up, then run the batch CLI: input\ -> output\
rem   start.bat doctor        set up, then check Python, packages, Tesseract and the Mistral settings
setlocal
cd /d "%~dp0"
set "VENV_PY=.venv\Scripts\python.exe"

if exist "%VENV_PY%" goto have_venv
set "PY="
if defined PYTHON set "PY=%PYTHON%"
if not defined PY (
  py -3.13 -c "import sys" >nul 2>&1 && set "PY=py -3.13"
)
if not defined PY (
  python -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)" >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo PrzetarGO needs Python 3.13 or newer.
  echo Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^)
  echo or run: winget install -e --id Python.Python.3.13
  echo Then run start.bat again.
  exit /b 1
)
echo Creating .venv ...
%PY% -m venv .venv || exit /b 1

:have_venv
"%VENV_PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)"
if errorlevel 1 (
  echo .venv was made with an older Python. Delete the .venv folder and run start.bat again.
  exit /b 1
)

fc /b requirements.txt .venv\requirements.installed >nul 2>&1
if errorlevel 1 (
  echo Installing Python packages ^(first run takes a minute^)...
  "%VENV_PY%" -m pip install --disable-pip-version-check -q -r requirements.txt || exit /b 1
  copy /y requirements.txt .venv\requirements.installed >nul
)

if /i "%~1"=="batch" goto batch
if /i "%~1"=="doctor" goto doctor

"%VENV_PY%" doctor.py --startup || exit /b 1
if not defined PORT set "PORT=8000"
echo.
echo PrzetarGO is running at http://127.0.0.1:%PORT%/  (press Ctrl+C to stop)
set "HOST=127.0.0.1"
"%VENV_PY%" back-end2\api.py
exit /b %errorlevel%

:batch
shift
"%VENV_PY%" main.py %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:doctor
"%VENV_PY%" doctor.py %2 %3
exit /b %errorlevel%
