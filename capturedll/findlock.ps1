$target = "MicToolCapture.dll"
Get-Process | ForEach-Object {
    $proc = $_
    try {
        $proc.Modules | Where-Object { $_.FileName -like "*$target*" } | ForEach-Object {
            Write-Host "Locked by: $($proc.Name) (PID $($proc.Id))"
        }
    } catch { }
}
