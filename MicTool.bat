@echo off
cd /d "%~dp0"

if exist "%~dp0venv\Scripts\pythonw.exe" (
    "%~dp0venv\Scripts\pythonw.exe" mictool.py
) else (
    echo No venv found. Create one and install requirements.txt first.
    pause
)
