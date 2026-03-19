$logFile = 'C:\desktoptoolDev\mictool\capturedll\test_out.txt'
$errFile = 'C:\desktoptoolDev\mictool\capturedll\test_err.txt'
$proc = Start-Process `
    -FilePath 'C:\desktoptoolDev\mictool\venv_rvc\Scripts\python.exe' `
    -ArgumentList 'C:\desktoptoolDev\mictool\test_capture.py' `
    -WorkingDirectory 'C:\desktoptoolDev\mictool' `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $errFile `
    -Wait -PassThru
Write-Output "Exit: $($proc.ExitCode)"
Write-Output "=== STDOUT ==="
Get-Content $logFile -ErrorAction SilentlyContinue
Write-Output "=== STDERR ==="
Get-Content $errFile -ErrorAction SilentlyContinue
