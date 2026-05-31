@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "HOST=%WINDS_LEDGER_HOST%"
set "PORT=%WINDS_LEDGER_PORT%"
set "WINDOW_TITLE=%WINDS_LEDGER_WINDOW_TITLE%"

if not defined HOST set "HOST=127.0.0.1"
if not defined PORT set "PORT=8004"
if not defined WINDOW_TITLE set "WINDOW_TITLE=Winds Ledger Backend"

set "APP_URL=http://%HOST%:%PORT%/"
set "HEALTH_URL=http://%HOST%:%PORT%/api/health"

set "PYTHON_EXE="
if exist "%ROOT_DIR%.venv\Scripts\python.exe" set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"
if not defined PYTHON_EXE if exist "%BACKEND_DIR%\.venv\Scripts\python.exe" set "PYTHON_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"
if not defined PYTHON_EXE set "PYTHON_EXE=python"

if not exist "%BACKEND_DIR%" (
    echo Backend directory not found: "%BACKEND_DIR%"
    exit /b 1
)

pushd "%BACKEND_DIR%"

echo Starting Winds Ledger backend on %APP_URL%
echo Using Python: %PYTHON_EXE%

if /I "%WINDS_LEDGER_FOREGROUND%"=="1" (
    "%PYTHON_EXE%" -m uvicorn app.main:app --reload --host %HOST% --port %PORT%
    set "EXIT_CODE=%ERRORLEVEL%"
    popd
    exit /b %EXIT_CODE%
)

start "%WINDOW_TITLE%" cmd /k ""%PYTHON_EXE%" -m uvicorn app.main:app --reload --host %HOST% --port %PORT%"

if /I "%WINDS_LEDGER_SKIP_BROWSER%"=="1" (
    popd
    exit /b 0
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "$url = '%HEALTH_URL%'; for ($i = 0; $i -lt 40; $i++) { try { $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1; if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { exit 0 } } catch { } Start-Sleep -Milliseconds 500 }; exit 1"
if errorlevel 1 (
    echo Backend did not become ready before browser launch. Open %APP_URL% manually after startup completes.
    popd
    exit /b 0
)

start "" "%APP_URL%"

popd
exit /b 0