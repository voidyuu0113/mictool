"""Quick test for MicTool_ListWindowProcesses"""
import ctypes
from pathlib import Path

DLL_PATH = Path(__file__).parent / "MicToolCapture.dll"
dll = ctypes.CDLL(str(DLL_PATH))

class SessionEntry(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('pid', ctypes.c_uint32), ('exe_name', ctypes.c_wchar * 260),
                ('peak_level', ctypes.c_float)]

class WindowProcEntry(ctypes.Structure):
    _fields_ = [('pid', ctypes.c_uint32), ('exe_name', ctypes.c_wchar * 260)]

dll.MicTool_ListSessions.restype  = ctypes.c_int
dll.MicTool_ListSessions.argtypes = [ctypes.c_void_p, ctypes.c_int]
dll.MicTool_ListWindowProcesses.restype  = ctypes.c_int
dll.MicTool_ListWindowProcesses.argtypes = [ctypes.c_void_p, ctypes.c_int]

print("=== Sessions (root-PID resolved) ===")
sess = (SessionEntry * 64)()
n = dll.MicTool_ListSessions(sess, 64)
print(f"  {n} session(s)")
for i in range(n):
    print(f"  PID={sess[i].pid:6d}  peak={sess[i].peak_level:.3f}  {sess[i].exe_name}")

print("\n=== Window Processes ===")
wins = (WindowProcEntry * 256)()
nw = dll.MicTool_ListWindowProcesses(wins, 256)
print(f"  Found {nw} window processes total")

BROWSERS = ('chrome', 'firefox', 'zen', 'msedge', 'brave', 'opera', 'vivaldi')
browsers = [wins[i] for i in range(nw)
            if any(b in wins[i].exe_name.lower() for b in BROWSERS)]
print(f"  Browsers: {len(browsers)}")
for w in browsers:
    print(f"    PID={w.pid:6d}  {w.exe_name}")

print("\n=== All window processes (first 20) ===")
for i in range(min(nw, 20)):
    print(f"  PID={wins[i].pid:6d}  {wins[i].exe_name}")
