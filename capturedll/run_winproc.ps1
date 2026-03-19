$logFile = 'C:\desktoptoolDev\mictool\capturedll\winproc_out.txt'
$errFile = 'C:\desktoptoolDev\mictool\capturedll\winproc_err.txt'
$proc = Start-Process `
    -FilePath 'C:\desktoptoolDev\mictool\venv_rvc\Scripts\python.exe' `
    -ArgumentList 'C:\desktoptoolDev\mictool\test_winproc.py' `
    -WorkingDirectory 'C:\desktoptoolDev\mictool' `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $errFile `
    -Wait -PassThru
Write-Output "Exit: $($proc.ExitCode)"
Write-Output "=== OUT ==="
Get-Content $logFile -ErrorAction SilentlyContinue
Write-Output "=== ERR ==="
Get-Content $errFile -ErrorAction SilentlyContinue
