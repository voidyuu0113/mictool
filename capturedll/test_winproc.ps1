$logFile = 'C:\desktoptoolDev\mictool\capturedll\winproc_out.txt'
$errFile = 'C:\desktoptoolDev\mictool\capturedll\winproc_err.txt'

$script = @'
import ctypes, os
from pathlib import Path

DLL_PATH = Path(r"C:\desktoptoolDev\mictool\MicToolCapture.dll")
dll = ctypes.CDLL(str(DLL_PATH))

class SessionEntry(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('pid', ctypes.c_uint32), ('exe_name', ctypes.c_wchar * 260), ('peak_level', ctypes.c_float)]

class WindowProcEntry(ctypes.Structure):
    _fields_ = [('pid', ctypes.c_uint32), ('exe_name', ctypes.c_wchar * 260)]

dll.MicTool_ListSessions.restype  = ctypes.c_int
dll.MicTool_ListSessions.argtypes = [ctypes.c_void_p, ctypes.c_int]
dll.MicTool_ListWindowProcesses.restype  = ctypes.c_int
dll.MicTool_ListWindowProcesses.argtypes = [ctypes.c_void_p, ctypes.c_int]

print("=== Sessions (root-PID resolved) ===")
sess = (SessionEntry * 64)()
n = dll.MicTool_ListSessions(sess, 64)
for i in range(n):
    print(f"  PID={sess[i].pid:6d}  peak={sess[i].peak_level:.3f}  {sess[i].exe_name}")

print(f"\n=== Window Processes ({0} entries) ===".format(0))
wins = (WindowProcEntry * 256)()
nw = dll.MicTool_ListWindowProcesses(wins, 256)
print(f"  Found {nw} window processes")
browsers = [w for w in wins[:nw] if any(b in w.exe_name.lower() for b in ('chrome','firefox','zen','msedge','brave','opera'))]
print(f"  Browsers found: {len(browsers)}")
for w in browsers:
    print(f"    PID={w.pid:6d}  {w.exe_name}")
'@

$proc = Start-Process `
    -FilePath 'C:\desktoptoolDev\mictool\venv_rvc\Scripts\python.exe' `
    -ArgumentList "-c `"$script`"" `
    -WorkingDirectory 'C:\desktoptoolDev\mictool' `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError $errFile `
    -Wait -PassThru
Write-Output "Exit: $($proc.ExitCode)"
Write-Output "=== OUT ==="
Get-Content $logFile -ErrorAction SilentlyContinue
Write-Output "=== ERR ==="
Get-Content $errFile -ErrorAction SilentlyContinue
