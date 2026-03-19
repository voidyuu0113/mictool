@echo off
cd /d "%~dp0"
echo ============================================================
echo  MicTool — RVC Neural Voice Conversion Setup
echo ============================================================
echo.
echo [Step 1] Creating Python 3.11 venv for RVC...
py -3.11 -m venv venv_rvc
if errorlevel 1 (
    echo ERROR: Python 3.11 not found.
    echo Download from https://www.python.org/downloads/release/python-3119/
    pause & exit /b 1
)

echo [Step 2] Installing PyTorch (CUDA 12.1)...
venv_rvc\Scripts\pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121 -q

echo [Step 3] Installing audio deps...
venv_rvc\Scripts\pip install sounddevice numpy scipy -q

echo [Step 4] Installing fairseq (requires Developer Mode or run as Admin)...
venv_rvc\Scripts\pip install fairseq==0.12.2 --no-build-isolation -q
if errorlevel 1 (
    echo.
    echo *** fairseq install failed ***
    echo Fix options:
    echo   A) Enable Windows Developer Mode:
    echo      Settings - Privacy ^& Security - For Developers - Developer Mode ON
    echo      Then re-run this script.
    echo   B) Right-click this bat and Run as Administrator
    echo.
    pause & exit /b 1
)

echo [Step 5] Installing rvc-python...
venv_rvc\Scripts\pip install rvc-python -q

echo [Step 6] Installing remaining MicTool deps...
venv_rvc\Scripts\pip install librosa soundfile praat-parselmouth pyworld faiss-cpu torchcrepe typeguard ffmpeg-python -q

echo.
echo ============================================================
echo  Done! Updating MicTool.bat to use RVC venv...
echo ============================================================

:: Patch MicTool.bat to use venv_rvc
(
echo @echo off
echo cd /d "%%~dp0"
echo if exist "%%~dp0venv_rvc\Scripts\pythonw.exe" ^(
echo     "%%~dp0venv_rvc\Scripts\pythonw.exe" mictool.py
echo ^) else if exist "%%~dp0venv\Scripts\pythonw.exe" ^(
echo     "%%~dp0venv\Scripts\pythonw.exe" mictool.py
echo ^) else ^(
echo     echo No venv found. Run install.bat or install_rvc.bat first.
echo     pause
echo ^)
) > MicTool.bat

echo Launch MicTool.bat to start with full RVC support.
pause
