@echo off
setlocal
set "RTX_PYTHON=%~dp0.venv\Scripts\pythonw.exe"
if not exist "%RTX_PYTHON%" (
    echo Create the Python environment and install the requirements first. See README.md.
    pause
    exit /b 1
)
start "" "%RTX_PYTHON%" "%~dp0Chrome-RTX-VSR-Native.pyw" %*
