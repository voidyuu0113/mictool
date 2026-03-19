@echo off
cd /d "%~dp0"

:: Prefer venv_rvc (has TTS neural VC + PyTorch), fall back to venv (DSP only)
if exist "%~dp0venv_rvc\Scripts\pythonw.exe" (
    "%~dp0venv_rvc\Scripts\pythonw.exe" mictool.py
) else if exist "%~dp0venv\Scripts\pythonw.exe" (
    "%~dp0venv\Scripts\pythonw.exe" mictool.py
) else (
    echo No venv found. Run install.bat first.
    pause
)
