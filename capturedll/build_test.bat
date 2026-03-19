@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
cl.exe /EHsc /std:c++17 /nologo /D_UNICODE /DUNICODE ^
  "C:\desktoptoolDev\mictool\capturedll\test_main.cpp" ^
  /link ole32.lib mmdevapi.lib avrt.lib psapi.lib kernel32.lib user32.lib RuntimeObject.lib ^
  /OUT:"C:\desktoptoolDev\mictool\capturedll\test_capture.exe" /SUBSYSTEM:CONSOLE /MACHINE:X64 ^
  /MANIFEST:EMBED /MANIFESTINPUT:"C:\desktoptoolDev\mictool\capturedll\test_capture.manifest"
if exist "C:\desktoptoolDev\mictool\capturedll\test_capture.exe" (
    echo BUILD OK
) else (
    echo BUILD FAILED
)
