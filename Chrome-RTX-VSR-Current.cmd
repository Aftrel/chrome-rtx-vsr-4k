@echo off
setlocal
set "RTX_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%RTX_PYTHON%" (
    echo Create the Python environment and install the requirements first. See README.md.
    pause
    exit /b 1
)
set "VSR_MODE=%~1"
if not defined VSR_MODE set "VSR_MODE=enable"
"%RTX_PYTHON%" "%~dp0Chrome-RTX-VSR-Current.pyw" "%VSR_MODE%"
set "VSR_STATUS=%ERRORLEVEL%"
if not "%VSR_STATUS%"=="0" pause
exit /b %VSR_STATUS%
