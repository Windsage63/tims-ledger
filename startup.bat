@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
set "FRONTEND_URL=http://127.0.0.1:5173"
set "BACKEND_HOST=127.0.0.1"
set "BACKEND_PORT=8000"
set "FRONTEND_HOST=127.0.0.1"
set "FRONTEND_PORT=5173"

if not exist "%PYTHON%" (
    echo Could not find "%PYTHON%".
    echo Create the repo virtual environment before running this script.
    exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
    echo npm is not available on PATH.
    echo Install Node.js and make sure npm is available before running this script.
    exit /b 1
)

if defined WINDSAGE_STARTUP_DRY_RUN (
    echo [dry-run] start "Windsage Ledger API" /D "%ROOT%\backend" "%PYTHON%" -m uvicorn app.main:app --reload --host %BACKEND_HOST% --port %BACKEND_PORT%
    echo [dry-run] start "Windsage Ledger Frontend" /D "%ROOT%\frontend" npm run dev -- --host %FRONTEND_HOST% --port %FRONTEND_PORT%
    echo [dry-run] start "" "%FRONTEND_URL%"
    exit /b 0
)

start "Windsage Ledger API" /D "%ROOT%\backend" "%PYTHON%" -m uvicorn app.main:app --reload --host %BACKEND_HOST% --port %BACKEND_PORT%
start "Windsage Ledger Frontend" /D "%ROOT%\frontend" npm run dev -- --host %FRONTEND_HOST% --port %FRONTEND_PORT%

timeout /t 5 /nobreak >nul
start "" "%FRONTEND_URL%"

endlocal