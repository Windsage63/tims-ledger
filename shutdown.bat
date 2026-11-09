@echo off
setlocal

set "PORT=%TIMS_LEDGER_PORT%"
if not defined PORT set "PORT=8004"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop-server.ps1" -Port "%PORT%"
exit /b %ERRORLEVEL%
