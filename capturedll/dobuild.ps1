$vcvars = "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"
$src    = "C:\desktoptoolDev\mictool\capturedll\capture.cpp"
$out    = "C:\desktoptoolDev\mictool\MicToolCapture.dll"

# Source vcvars then compile in one cmd call
$cmd = "`"$vcvars`" x64 && cl.exe /LD /O2 /EHsc /std:c++17 /nologo /D_UNICODE /DUNICODE `"$src`" /link ole32.lib mmdevapi.lib avrt.lib psapi.lib kernel32.lib user32.lib /OUT:`"$out`" /DLL /MACHINE:X64"

Write-Host "Building MicToolCapture.dll ..."
$result = cmd /c $cmd 2>&1
$result | ForEach-Object { Write-Host $_ }

if (Test-Path $out) {
    Write-Host "`nSUCCESS: $out"
} else {
    Write-Host "`nFAILED — DLL not found."
}
