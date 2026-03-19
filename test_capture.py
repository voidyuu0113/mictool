"""Quick DLL diagnostic — run with: venv_rvc\Scripts\python test_capture.py"""
import ctypes, time, numpy as np, os
from pathlib import Path

DLL_PATH = Path(__file__).parent / "MicToolCapture.dll"

class SessionEntry(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('pid', ctypes.c_uint32),
                ('exe_name', ctypes.c_wchar * 260),
                ('peak_level', ctypes.c_float)]

dll = ctypes.CDLL(str(DLL_PATH))
dll.MicTool_ListSessions.restype  = ctypes.c_int
dll.MicTool_ListSessions.argtypes = [ctypes.c_void_p, ctypes.c_int]
dll.MicTool_StartCapture.restype  = ctypes.c_int
dll.MicTool_StartCapture.argtypes = [ctypes.c_uint32, ctypes.c_int]
dll.MicTool_ReadAudio.restype     = ctypes.c_int
dll.MicTool_ReadAudio.argtypes    = [ctypes.c_void_p, ctypes.c_int]
dll.MicTool_GetSampleRate.restype = ctypes.c_uint
dll.MicTool_StopCapture.restype   = None
dll.MicTool_GetLastHR.restype     = ctypes.c_long
dll.MicTool_GetLastHR.argtypes    = []
dll.MicTool_GetCoInitHR.restype    = ctypes.c_long
dll.MicTool_GetCoInitHR.argtypes   = []
dll.MicTool_GetFmtDbg.restype      = ctypes.c_uint
dll.MicTool_GetFmtDbg.argtypes     = []
dll.MicTool_StartCaptureDirect.restype  = ctypes.c_int
dll.MicTool_StartCaptureDirect.argtypes = [ctypes.c_uint32, ctypes.c_int]
dll.MicTool_StartDeviceLoopback.restype  = ctypes.c_int
dll.MicTool_StartDeviceLoopback.argtypes = [ctypes.c_wchar_p]

class DeviceEntry(ctypes.Structure):
    _fields_ = [('id',   ctypes.c_wchar * 260),
                ('name', ctypes.c_wchar * 260)]
dll.MicTool_ListDevices.restype  = ctypes.c_int
dll.MicTool_ListDevices.argtypes = [ctypes.c_void_p, ctypes.c_int]

# ── 0. Environment info ───────────────────────────────────────────────────────
import ctypes as _ct
def is_admin():
    try: return _ct.windll.shell32.IsUserAnAdmin()
    except: return False
print(f"Running as admin: {is_admin()}")
print(f"Python PID: {os.getpid()}")

# ── 1. List sessions ──────────────────────────────────────────────────────────
print("\n=== Active Audio Sessions ===")
entries = (SessionEntry * 64)()
count = dll.MicTool_ListSessions(entries, 64)
print(f"Found {count} session(s)")
for i in range(count):
    print(f"  [{i}] PID={entries[i].pid:6d}  peak={entries[i].peak_level:.3f}  {entries[i].exe_name}")

if count == 0:
    print("No sessions found — is any app playing audio?")
    raise SystemExit

# ── 1b. Also verify the PIDs exist as processes ───────────────────────────────
import subprocess, ctypes as _ctypes2
for i in range(count):
    pid_check = entries[i].pid
    h = _ctypes2.windll.kernel32.OpenProcess(0x1000, False, pid_check)  # PROCESS_QUERY_LIMITED_INFORMATION
    print(f"  PID {pid_check} handle={h}  (0=process not found or access denied)")
    if h: _ctypes2.windll.kernel32.CloseHandle(h)

# ── 1c. Also try our own PID ───────────────────────────────────────────────────
our_pid = os.getpid()
print(f"\nAlso trying our own PID={our_pid} via StartCapture (threaded):")
ret_self = dll.MicTool_StartCapture(our_pid, 0)
hr_self  = dll.MicTool_GetLastHR()
coHR_self= dll.MicTool_GetCoInitHR()
print(f"  StartCapture={ret_self}  HR=0x{hr_self & 0xFFFFFFFF:08X}  CoInitHR=0x{coHR_self & 0xFFFFFFFF:08X}")
dll.MicTool_StopCapture()

print(f"\nAlso trying our own PID={our_pid} via StartCaptureDirect (caller thread):")
ret_d  = dll.MicTool_StartCaptureDirect(our_pid, 0)
hr_d   = dll.MicTool_GetLastHR()
coHR_d = dll.MicTool_GetCoInitHR()
print(f"  StartCaptureDirect={ret_d}  HR=0x{hr_d & 0xFFFFFFFF:08X}  CoInitHR=0x{coHR_d & 0xFFFFFFFF:08X}")
dll.MicTool_StopCapture()

# ── 2. Try ALL sessions, not just the loudest ─────────────────────────────────
success_idx = -1
for i in range(count):
    pid  = entries[i].pid
    name = entries[i].exe_name
    print(f"\n=== Trying [{i}] PID={pid} ({name}) ===")
    ret     = dll.MicTool_StartCapture(pid, 1)
    hr      = dll.MicTool_GetLastHR()
    coInitHR= dll.MicTool_GetCoInitHR()
    fmtDbg  = dll.MicTool_GetFmtDbg()
    print(f"  StartCapture={ret}  HR=0x{hr & 0xFFFFFFFF:08X}  CoInitHR=0x{coInitHR & 0xFFFFFFFF:08X}  fmt=0x{fmtDbg:08X}")
    if ret == 0:
        success_idx = i
        break
    dll.MicTool_StopCapture()

if success_idx < 0:
    print("All process-loopback sessions failed — skipping to device loopback test.")
    # Jump ahead to device loopback test
    import sys
    # We continue below (don't exit yet)

if success_idx >= 0:
    sr = dll.MicTool_GetSampleRate()
    print(f"Capture sample rate: {sr} Hz")

    # ── 3. Read audio and check for non-silence ─────────────────────────────
    print("\nReading 2 seconds of audio...")
    time.sleep(0.5)

    buf = (ctypes.c_float * 88200)()
    got = dll.MicTool_ReadAudio(buf, 88200)
    print(f"Samples read: {got}")

    if got > 0:
        arr = np.frombuffer(buf, dtype=np.float32, count=got)
        rms  = float(np.sqrt(np.mean(arr**2)))
        peak = float(np.max(np.abs(arr)))
        print(f"RMS={rms:.6f}  Peak={peak:.6f}")
        if peak > 0.001:
            print("[OK] Audio captured successfully!")
        else:
            print("[FAIL] Audio is silent (all zeros or near-zero)")
    else:
        print("[FAIL] No samples returned at all")

    dll.MicTool_StopCapture()

# ── 4. Device loopback fallback ───────────────────────────────────────────────
print("\n=== Testing Device Loopback (all system audio) ===")
devs = (DeviceEntry * 16)()
ndev = dll.MicTool_ListDevices(devs, 16)
print(f"Found {ndev} render device(s):")
for i in range(ndev):
    print(f"  [{i}] {devs[i].name}")

print("\nStarting device loopback on default render device...")
ret_dev = dll.MicTool_StartDeviceLoopback(None)
hr_dev  = dll.MicTool_GetLastHR()
print(f"  StartDeviceLoopback={ret_dev}  HR=0x{hr_dev & 0xFFFFFFFF:08X}")
if ret_dev == 0:
    time.sleep(0.5)
    buf2 = (ctypes.c_float * 88200)()
    got2 = dll.MicTool_ReadAudio(buf2, 88200)
    print(f"  Samples read: {got2}")
    if got2 > 0:
        arr2 = np.frombuffer(buf2, dtype=np.float32, count=got2)
        rms2  = float(np.sqrt(np.mean(arr2**2)))
        peak2 = float(np.max(np.abs(arr2)))
        print(f"  RMS={rms2:.6f}  Peak={peak2:.6f}")
        if peak2 > 0.001:
            print("  [OK] Device loopback working!")
        else:
            print("  [FAIL] Device loopback: silence (nothing playing?)")
dll.MicTool_StopCapture()
print("\nDone.")
