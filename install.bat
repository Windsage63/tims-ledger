@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0"
set "VENV_DIR=%ROOT_DIR%.venv"
set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "REQUIREMENTS=%ROOT_DIR%backend\requirements.txt"
set "PYTHON_EXE="

echo Tim's Ledger installer
echo.

if not exist "%REQUIREMENTS%" (
    echo Requirements file not found: "%REQUIREMENTS%"
    exit /b 1
)

call :find_python
if not defined PYTHON_EXE (
    call :install_python
    if errorlevel 1 exit /b 1
    call :find_python
)

if not defined PYTHON_EXE (
    echo Python was installed, but this terminal cannot find it yet.
    echo Close this window, open a new Command Prompt or PowerShell window, and run install.bat again.
    exit /b 1
)

echo Using Python: %PYTHON_EXE%
echo.

if not exist "%VENV_PYTHON%" (
    echo Creating virtual environment at "%VENV_DIR%"...
    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo Failed to create the virtual environment.
        exit /b 1
    )
) else (
    echo Reusing existing virtual environment at "%VENV_DIR%".
)

echo.
echo Ensuring pip is available inside the virtual environment...
"%VENV_PYTHON%" -m ensurepip --upgrade
if errorlevel 1 (
    echo Failed to prepare pip in the virtual environment.
    exit /b 1
)

echo.
echo Installing Tim's Ledger backend requirements...
"%VENV_PYTHON%" -m pip install -r "%REQUIREMENTS%"
if errorlevel 1 (
    echo Failed to install backend requirements.
    exit /b 1
)

echo.
echo Verifying installed packages...
"%VENV_PYTHON%" -c "import fastapi, pydantic, uvicorn; print('FastAPI', fastapi.__version__); print('Pydantic', pydantic.__version__)"
if errorlevel 1 (
    echo Package verification failed.
    exit /b 1
)

echo.
echo Install complete. Run startup.bat to start Tim's Ledger.
exit /b 0

:find_python
set "PYTHON_EXE="

call :check_python_path "%VENV_PYTHON%"
if defined PYTHON_EXE exit /b 0

call :check_python_command "py -3.13"
if defined PYTHON_EXE exit /b 0

call :check_python_command "py -3"
if defined PYTHON_EXE exit /b 0

call :check_python_command "python"
if defined PYTHON_EXE exit /b 0

call :check_python_path "%LocalAppData%\Programs\Python\Python313\python.exe"
if defined PYTHON_EXE exit /b 0

exit /b 0

:check_python_path
set "CANDIDATE=%~1"
if not exist "%CANDIDATE%" exit /b 0
"%CANDIDATE%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 exit /b 0
set "PYTHON_EXE=%CANDIDATE%"
exit /b 0

:check_python_command
set "CANDIDATE=%~1"
%CANDIDATE% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
if errorlevel 1 exit /b 0
for /f "delims=" %%P in ('%CANDIDATE% -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
exit /b 0

:install_python
echo Python 3.10 or newer was not found.
echo Trying to install Python 3.13 with winget...
echo.

where winget >nul 2>nul
if errorlevel 1 (
    echo winget is not available on this computer, so Python cannot be installed automatically.
    echo Install Python 3.13 or newer from https://www.python.org/downloads/windows/
    echo Then open a new terminal and run install.bat again.
    exit /b 1
)

winget install --exact --id Python.Python.3.13 --source winget --scope user --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    echo.
    echo The winget Python install failed.
    echo Install Python 3.13 or newer from https://www.python.org/downloads/windows/
    echo Then open a new terminal and run install.bat again.
    exit /b 1
)

echo.
echo Python install finished. Continuing setup...
exit /b 0
