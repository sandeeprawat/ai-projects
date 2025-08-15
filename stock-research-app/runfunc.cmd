@echo off
setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXECUTION

REM ----------------------------------------------------------------------------
REM Azure Functions local runner via venv, with logging to .\.logs\func-host.log
REM ----------------------------------------------------------------------------

REM Move to repo subfolder (this script's directory)
pushd "%~dp0" >nul 2>&1

REM Validate venv exists
if not exist ".venv\Scripts\python.exe" (
	echo [ERR] Virtual environment not found at .venv\Scripts\python.exe
	echo       Create it with: py -3 -m venv .venv
	popd >nul 2>&1
	exit /b 1
)

REM Activate venv
call ".venv\Scripts\activate" || (
	echo [ERR] Failed to activate venv
	popd >nul 2>&1
	exit /b 1
)

REM Ensure Functions Python worker uses this interpreter
set "languageWorkers__python__defaultExecutablePath=%CD%\.venv\Scripts\python.exe"
set "languageWorkers__python__pythonPath=%languageWorkers__python__defaultExecutablePath%"
set "PATH=%CD%\.venv\Scripts;%PATH%"
set "PYTHONPATH=%CD%\.venv\Lib\site-packages"

REM Helpful dev env flags and logging level
set "AZURE_FUNCTIONS_ENVIRONMENT=Development"
set "AzureFunctionsJobHost__logging__logLevel__default=Information"
set "AzureFunctionsJobHost__logging__Console__IsEnabled=true"

REM Prepare logs directory/file
set "LOG_DIR=%CD%\.logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1
set "LOG_FILE=%LOG_DIR%\func-host.log"
echo [INFO] Logging to %LOG_FILE%

REM Start host from the api folder and tee output to log file
pushd api >nul 2>&1
echo [INFO] Starting Azure Functions host on http://localhost:7071/
powershell -NoProfile -ExecutionPolicy Bypass -Command "func host start --port 7071 2^>^&1 ^| Tee-Object -FilePath '%LOG_FILE%' -Append"
set "EXITCODE=%ERRORLEVEL%"
popd >nul 2>&1

popd >nul 2>&1
exit /b %EXITCODE%
