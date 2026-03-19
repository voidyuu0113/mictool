@echo off
:: Build MicToolCapture.dll  —  requires Visual Studio 2019 / 2022 (x64)
setlocal

:: Find vcvarsall.bat automatically
set "VCVARS="
for /d %%i in (
    "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build"
    "C:\Program Files\Microsoft Visual Studio\2022\Professional\VC\Auxiliary\Build"
    "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build"
    "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build"
    "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build"
) do (
    if exist "%%~i\vcvarsall.bat" (
        set "VCVARS=%%~i\vcvarsall.bat"
        goto :found
    )
)
echo ERROR: Could not find Visual Studio. Install VS 2019/2022 with C++ tools.
exit /b 1

:found
echo Using: %VCVARS%
call "%VCVARS%" x64 > nul 2>&1

echo Compiling capture.cpp ...
cl.exe ^
    /LD /O2 /EHsc /std:c++17 /W3 /nologo ^
    /D_UNICODE /DUNICODE ^
    capture.cpp ^
    /link ^
    ole32.lib mmdevapi.lib avrt.lib psapi.lib kernel32.lib ^
    /OUT:..\MicToolCapture.dll ^
    /IMPLIB:..\MicToolCapture.lib ^
    /DLL /MACHINE:X64 /NODEFAULTLIB:MSVCRT

if errorlevel 1 (
    echo.
    echo BUILD FAILED.
    pause
    exit /b 1
)

echo.
echo SUCCESS: MicToolCapture.dll created in parent folder.
del /q *.obj *.exp 2>nul
pause
