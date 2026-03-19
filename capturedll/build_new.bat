@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
cl.exe /LD /O2 /EHsc /std:c++17 /nologo /D_UNICODE /DUNICODE ^
  "C:\desktoptoolDev\mictool\capturedll\capture.cpp" ^
  /link ole32.lib mmdevapi.lib avrt.lib psapi.lib kernel32.lib user32.lib propsys.lib ^
  /OUT:"C:\desktoptoolDev\mictool\MicToolCapture_new.dll" /DLL /MACHINE:X64
if exist "C:\desktoptoolDev\mictool\MicToolCapture_new.dll" (
    echo BUILD OK
) else (
    echo BUILD FAILED
)
