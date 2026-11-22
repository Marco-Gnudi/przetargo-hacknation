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
  echo PrzetarGO needs Python 3.13 or newer, and it is not installed.
  echo Install it, then run start.bat again:
  echo   winget install -e --id Python.Python.3.13
  echo   or https://www.python.org/downloads/  ^(tick "Add python.exe to PATH"^)
  echo Or point at an existing install: set PYTHON=C:\Path\to\python.exe
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

call :offer_tesseract

if /i "%~1"=="batch" goto batch
if /i "%~1"=="doctor" goto doctor

"%VENV_PY%" doctor.py --startup || exit /b 1
if not defined PORT set "PORT=8000"
echo.
echo PrzetarGO is running at http://127.0.0.1:%PORT%/  (press Ctrl+C to stop)
echo Put case folders in input\. JSON is written to output\.
set "HOST=127.0.0.1"
if not defined PRZETARGO_NO_BROWSER start "" /b powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 40;$i++){ try { Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:%PORT%/api/health' | Out-Null; Start-Process 'http://127.0.0.1:%PORT%/'; break } catch { Start-Sleep -Milliseconds 500 } }"
"%VENV_PY%" back-end2\api.py
exit /b %errorlevel%

:batch
shift
"%VENV_PY%" main.py %1 %2 %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:doctor
"%VENV_PY%" doctor.py %2 %3
exit /b %errorlevel%

:offer_tesseract
set "TESS_BIN="
if defined TESSERACT_CMD if exist "%TESSERACT_CMD%" set "TESS_BIN=%TESSERACT_CMD%"
if not defined TESS_BIN if exist backend\.env (
  for /f "usebackq tokens=1,* delims==" %%A in (`findstr /b /c:"TESSERACT_CMD=" backend\.env`) do set "TESS_BIN=%%B"
)
if not defined TESS_BIN (
  for /f "delims=" %%P in ('where tesseract 2^>nul') do if not defined TESS_BIN set "TESS_BIN=%%P"
)
if not defined TESS_BIN if exist "%ProgramFiles%\Tesseract-OCR\tesseract.exe" set "TESS_BIN=%ProgramFiles%\Tesseract-OCR\tesseract.exe"
if not defined TESS_BIN if exist "%LocalAppData%\Programs\Tesseract-OCR\tesseract.exe" set "TESS_BIN=%LocalAppData%\Programs\Tesseract-OCR\tesseract.exe"
if defined TESS_BIN (
  "%TESS_BIN%" --list-langs 2>nul | findstr /x /c:"pol" >nul && goto :eof
)
echo Tesseract OCR with Polish language data is not installed.
echo Text PDFs still work. Scanned PDFs need Tesseract; nothing is guessed when it is missing.
where winget >nul 2>&1
if errorlevel 1 (
  echo Install Tesseract 5 from https://github.com/UB-Mannheim/tesseract/wiki
  echo Tick Polish under Additional language data, then run start.bat again.
  echo If tesseract.exe is not on PATH, set TESSERACT_CMD in backend\.env.
  goto :eof
)
echo winget can install it. Windows may ask for administrator approval, because Tesseract is a system program.
echo   winget install -e --id UB-Mannheim.TesseractOCR
set /p ANSWER=Install Tesseract now? [y/N] 
if /i "%ANSWER%"=="y" goto install_tesseract
if /i "%ANSWER%"=="yes" goto install_tesseract
echo Skipped. Text PDFs will run.
goto :eof

:install_tesseract
winget install -e --id UB-Mannheim.TesseractOCR --accept-package-agreements --accept-source-agreements
echo If Polish was not included, copy pol.traineddata from https://github.com/tesseract-ocr/tessdata_fast
echo into the tessdata folder next to tesseract.exe, then run start.bat again.
goto :eof
