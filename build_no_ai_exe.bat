@echo off
cd /d "%~dp0"

if not exist "%~dp0venv_build\Scripts\python.exe" (
    echo Creating isolated build venv...
    py -3.12 -m venv venv_build
    if errorlevel 1 (
        echo Failed to create venv_build.
        pause
        exit /b 1
    )
)

echo Installing build dependencies...
"%~dp0venv_build\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo Failed to install build dependencies.
    pause
    exit /b 1
)

"%~dp0venv_build\Scripts\python.exe" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --noconsole ^
  --onedir ^
  --name MicTool-NoAI ^
  --icon "%~dp0ico\f3bte-osrj6-001.ico" ^
  --add-binary "%~dp0MicToolCapture.dll;." ^
  --add-data "%~dp0ico;ico" ^
  mictool.py

if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build complete: dist\MicTool-NoAI\MicTool-NoAI.exe
pause
