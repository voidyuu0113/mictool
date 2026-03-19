// MicToolCapture.dll
// Per-process WASAPI audio capture (same API as OBS Application Audio Capture)
// Requires: Windows 10 Build 19041+ (20H1 / May 2020 Update)
//
// Build:  run build.bat
// Exports (cdecl):
//   int   MicTool_ListSessions(SessionEntry* out, int maxCount)
//   int   MicTool_StartCapture(DWORD pid, int includeChildren)
//   int   MicTool_ReadAudio   (float* buf, int nSamples)
//   UINT  MicTool_GetSampleRate()
//   void  MicTool_StopCapture ()

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX        // prevent windows.h from defining min/max macros
#define INITGUID
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <audiopolicy.h>
#include <endpointvolume.h>
#include <avrt.h>
#include <psapi.h>
#include <roapi.h>        // RoInitialize / RoUninitialize
#include <tlhelp32.h>     // CreateToolhelp32Snapshot / Process32First

#include <atomic>
#include <deque>
#include <mutex>
#include <string>
#include <thread>
#include <algorithm>
#include <unordered_map>
#include <unordered_set>

#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "mmdevapi.lib")
#pragma comment(lib, "avrt.lib")
#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "RuntimeObject.lib")   // RoInitialize
#pragma comment(lib, "propsys.lib")         // PropVariantInit/Clear

// ── Process-loopback constants (SDK 10.0.20348+; define manually for older SDKs) ──
#ifndef AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK

typedef enum AUDIOCLIENT_ACTIVATION_TYPE {
    AUDIOCLIENT_ACTIVATION_TYPE_DEFAULT         = 0,
    AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK = 1,
} AUDIOCLIENT_ACTIVATION_TYPE;

typedef struct AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS {
    DWORD  TargetProcessId;
    UINT32 ProcessLoopbackMode;   // 0 = include children, 1 = exclude children
} AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS;

typedef struct AUDIOCLIENT_ACTIVATION_PARAMS {
    AUDIOCLIENT_ACTIVATION_TYPE ActivationType;
    union {
        AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS ProcessLoopbackParams;
    };
} AUDIOCLIENT_ACTIVATION_PARAMS;

#define PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE 0
#define PROCESS_LOOPBACK_MODE_EXCLUDE_TARGET_PROCESS_TREE 1

static const PCWSTR VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK =
    L"VAD\\Process_Loopback";   // correct value per SDK audioclientactivationparams.h

#endif // AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK

// ── Exported session structure ────────────────────────────────────────────────
#pragma pack(push, 1)
struct SessionEntry {
    DWORD  pid;
    WCHAR  exe_name[260];   // MAX_PATH
    float  peak_level;      // 0.0 – 1.0
};
#pragma pack(pop)

// ── Dynamic loader for ActivateAudioInterfaceAsync ───────────────────────────
// OBS loads this at runtime via GetProcAddress to avoid version lock-in.
typedef HRESULT (STDAPICALLTYPE *PFN_ActivateAudioInterfaceAsync)(
    LPCWSTR, REFIID, PROPVARIANT*,
    IActivateAudioInterfaceCompletionHandler*,
    IActivateAudioInterfaceAsyncOperation**);

static PFN_ActivateAudioInterfaceAsync g_pActivateAudioInterfaceAsync = nullptr;

static bool LoadActivateAudioInterface() {
    if (g_pActivateAudioInterfaceAsync) return true;
    HMODULE hMod = LoadLibraryW(L"Mmdevapi.dll");
    if (!hMod) return false;
    g_pActivateAudioInterfaceAsync =
        (PFN_ActivateAudioInterfaceAsync)GetProcAddress(hMod, "ActivateAudioInterfaceAsync");
    return g_pActivateAudioInterfaceAsync != nullptr;
}

// ── Activation completion handler ─────────────────────────────────────────────
// IMPORTANT: Must implement Free-Threaded Marshaling (FtmBase equivalent)
// so COM can dispatch ActivateCompleted from any thread/apartment.
// Without FTM the async activation returns E_ILLEGAL_METHOD_CALL.
class ActivationHandler : public IActivateAudioInterfaceCompletionHandler {
    volatile LONG m_ref = 1;
    IUnknown*     m_ftm = nullptr;   // free-threaded marshaler
public:
    IAudioClient* pClient  = nullptr;
    HRESULT       hrResult = E_FAIL;
    HANDLE        hDone;

    ActivationHandler() : hDone(CreateEventW(nullptr, TRUE, FALSE, nullptr)) {
        // Register as free-threaded so ActivateCompleted can fire on any thread
        CoCreateFreeThreadedMarshaler(
            static_cast<IActivateAudioInterfaceCompletionHandler*>(this), &m_ftm);
    }
    ~ActivationHandler() {
        CloseHandle(hDone);
        if (pClient) { pClient->Release(); pClient = nullptr; }
        if (m_ftm)   { m_ftm->Release();   m_ftm   = nullptr; }
    }

    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) override {
        if (riid == __uuidof(IUnknown) ||
            riid == __uuidof(IActivateAudioInterfaceCompletionHandler)) {
            *ppv = static_cast<IActivateAudioInterfaceCompletionHandler*>(this);
            AddRef(); return S_OK;
        }
        // Delegate IMarshal to FTM — this is what makes cross-apartment callbacks work
        if (m_ftm) {
            HRESULT hr = m_ftm->QueryInterface(riid, ppv);
            if (SUCCEEDED(hr)) return hr;
        }
        *ppv = nullptr; return E_NOINTERFACE;
    }
    STDMETHODIMP_(ULONG) AddRef() override  { return InterlockedIncrement(&m_ref); }
    STDMETHODIMP_(ULONG) Release() override {
        ULONG r = InterlockedDecrement(&m_ref);
        if (r == 0) delete this;
        return r;
    }
    STDMETHODIMP ActivateCompleted(IActivateAudioInterfaceAsyncOperation* op) override {
        IUnknown* pUnk = nullptr;
        op->GetActivateResult(&hrResult, &pUnk);
        if (SUCCEEDED(hrResult) && pUnk) {
            pUnk->QueryInterface(__uuidof(IAudioClient), (void**)&pClient);
            pUnk->Release();
        }
        SetEvent(hDone);
        return S_OK;
    }
};

// ── Last error HRESULT (for diagnostics) ──────────────────────────────────────
static HRESULT g_lastHR = S_OK;

// ── Capture state ─────────────────────────────────────────────────────────────
static std::mutex          g_mtx;
static std::deque<float>   g_ring;
static const size_t        RING_MAX = 44100 * 4;   // 4 s at 44.1 kHz

static std::atomic<bool>   g_running{ false };
static std::thread         g_thread;
static UINT32              g_sr = 44100;
static UINT32              g_ch = 2;
static UINT32              g_dbg_formatTag = 0;
static UINT32              g_dbg_bps = 0;

// ── Helper: get exe filename from PID ─────────────────────────────────────────
static std::wstring ExeNameOf(DWORD pid) {
    HANDLE h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!h) return L"";
    WCHAR buf[260] = {};
    DWORD len = 260;
    QueryFullProcessImageNameW(h, 0, buf, &len);
    CloseHandle(h);
    std::wstring p(buf);
    auto pos = p.rfind(L'\\');
    return (pos != std::wstring::npos) ? p.substr(pos + 1) : p;
}

// ── Helper: snapshot the whole process table (pid -> parentPid) ───────────────
static std::unordered_map<DWORD,DWORD> SnapshotParents() {
    std::unordered_map<DWORD,DWORD> m;
    HANDLE hSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnap == INVALID_HANDLE_VALUE) return m;
    PROCESSENTRY32W pe = {}; pe.dwSize = sizeof(pe);
    if (Process32FirstW(hSnap, &pe)) {
        do { m[pe.th32ProcessID] = pe.th32ParentProcessID; }
        while (Process32NextW(hSnap, &pe));
    }
    CloseHandle(hSnap);
    return m;
}

// ── Helper: walk parent chain to find the topmost ancestor sharing the same
//   executable name.  Handles Chrome / Firefox / Zen which play audio via a
//   sandboxed utility child process — by returning the root browser PID we
//   cover the entire process tree with INCLUDE_TARGET_PROCESS_TREE.
// ─────────────────────────────────────────────────────────────────────────────
static DWORD GetRootPid(DWORD pid,
                         const std::unordered_map<DWORD,DWORD>& parents) {
    std::wstring myExe = ExeNameOf(pid);
    if (myExe.empty()) return pid;

    DWORD cur = pid;
    std::unordered_set<DWORD> visited;
    while (true) {
        if (visited.count(cur)) break;   // cycle guard
        visited.insert(cur);

        auto it = parents.find(cur);
        if (it == parents.end()) break;
        DWORD par = it->second;
        if (par == 0 || par == cur) break;

        // Only keep walking if the parent exe matches (same browser family)
        std::wstring parExe = ExeNameOf(par);
        if (parExe.empty() || parExe != myExe) break;

        cur = par;
    }
    return cur;
}

// ── Capture thread ────────────────────────────────────────────────────────────
// hCaptureEvent: auto-reset event set by WASAPI each time new audio data is
//   ready (AUDCLNT_STREAMFLAGS_EVENTCALLBACK mode). Pass NULL to fall back to
//   the old Sleep(5) polling path (used by device-loopback which does not use
//   EVENTCALLBACK).
static void CaptureThread(IAudioClient* client, UINT32 sr, UINT32 ch,
                           HANDLE hCaptureEvent) {
    DWORD taskIdx = 0;
    HANDLE hTask = AvSetMmThreadCharacteristicsW(L"Audio", &taskIdx);

    IAudioCaptureClient* pCap = nullptr;
    HRESULT hr = client->GetService(__uuidof(IAudioCaptureClient), (void**)&pCap);
    if (FAILED(hr)) {
        g_running = false;
        client->Release();
        if (hCaptureEvent) CloseHandle(hCaptureEvent);
        return;
    }

    client->Start();

    while (g_running) {
        // ── event-driven (process loopback) ──────────────────────────────────
        if (hCaptureEvent) {
            // 200 ms timeout so we can re-check g_running periodically
            DWORD w = WaitForSingleObject(hCaptureEvent, 200);
            if (w == WAIT_TIMEOUT) continue;
            if (w != WAIT_OBJECT_0) break;   // unexpected error
        } else {
            // ── polling (device loopback fallback) ───────────────────────────
            Sleep(5);
        }

        // Drain all available packets from the capture endpoint buffer
        UINT32 pktSize = 0;
        while (SUCCEEDED(pCap->GetNextPacketSize(&pktSize)) && pktSize > 0) {
            BYTE*  pData;
            UINT32 frames;
            DWORD  flags;
            if (FAILED(pCap->GetBuffer(&pData, &frames, &flags, nullptr, nullptr))) break;

            bool silent = (flags & AUDCLNT_BUFFERFLAGS_SILENT) != 0;
            float* f    = reinterpret_cast<float*>(pData);

            {
                std::lock_guard<std::mutex> lk(g_mtx);
                for (UINT32 i = 0; i < frames; i++) {
                    float mono = 0.f;
                    if (!silent) {
                        for (UINT32 c = 0; c < ch; c++)
                            mono += f[i * ch + c];
                        mono /= static_cast<float>(ch);
                    }
                    g_ring.push_back(mono);
                }
                while (g_ring.size() > RING_MAX)
                    g_ring.pop_front();
            }

            pCap->ReleaseBuffer(frames);
        }
    }

    client->Stop();
    pCap->Release();
    client->Release();
    if (hCaptureEvent) CloseHandle(hCaptureEvent);
    if (hTask) AvRevertMmThreadCharacteristics(hTask);
}

// ═════════════════════════════════════════════════════════════════════════════
//  EXPORTED C API
// ═════════════════════════════════════════════════════════════════════════════

// Forward declarations
extern "C" __declspec(dllexport) void  __cdecl MicTool_StopCapture();
extern "C" __declspec(dllexport) LONG  __cdecl MicTool_GetLastHR();
extern "C" __declspec(dllexport) LONG  __cdecl MicTool_GetCoInitHR();
extern "C" __declspec(dllexport) int   __cdecl MicTool_StartCaptureDirect(DWORD, int);
extern "C" __declspec(dllexport) int   __cdecl MicTool_StartDeviceLoopback(const WCHAR*);

extern "C" {

// List active audio sessions on the default render endpoint.
// Returns the ROOT process PID for each session (walks parent chain so that
// Chrome / Firefox utility children map back to the main browser process).
// Deduplicates so that multiple sessions from the same process tree appear
// as a single entry with the maximum peak across those sessions.
__declspec(dllexport) int __cdecl
MicTool_ListSessions(SessionEntry* out, int maxCount) {
    if (!out || maxCount <= 0) return 0;

    CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);

    IMMDeviceEnumerator* pEnum = nullptr;
    CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                     __uuidof(IMMDeviceEnumerator), (void**)&pEnum);
    if (!pEnum) { CoUninitialize(); return 0; }

    IMMDevice* pDev = nullptr;
    pEnum->GetDefaultAudioEndpoint(eRender, eConsole, &pDev);
    pEnum->Release();
    if (!pDev) { CoUninitialize(); return 0; }

    IAudioSessionManager2* pMgr = nullptr;
    pDev->Activate(__uuidof(IAudioSessionManager2), CLSCTX_ALL,
                   nullptr, (void**)&pMgr);
    pDev->Release();
    if (!pMgr) { CoUninitialize(); return 0; }

    IAudioSessionEnumerator* pSessEnum = nullptr;
    pMgr->GetSessionEnumerator(&pSessEnum);
    pMgr->Release();
    if (!pSessEnum) { CoUninitialize(); return 0; }

    // Snapshot parent table once — avoids O(n²) snapshot calls
    auto parents = SnapshotParents();

    // Collect: rootPid -> max peak
    struct Entry { DWORD rootPid; std::wstring name; float peak; };
    std::vector<Entry> collected;
    std::unordered_map<DWORD,int> rootIdx; // rootPid -> index in collected

    int total = 0;
    pSessEnum->GetCount(&total);

    for (int i = 0; i < total; i++) {
        IAudioSessionControl*   pCtrl  = nullptr;
        IAudioSessionControl2*  pCtrl2 = nullptr;
        IAudioMeterInformation* pMeter = nullptr;

        if (FAILED(pSessEnum->GetSession(i, &pCtrl))) continue;
        pCtrl->QueryInterface(__uuidof(IAudioSessionControl2),  (void**)&pCtrl2);
        pCtrl->QueryInterface(__uuidof(IAudioMeterInformation), (void**)&pMeter);
        pCtrl->Release();
        if (!pCtrl2) { if (pMeter) pMeter->Release(); continue; }

        DWORD sessionPid = 0;
        pCtrl2->GetProcessId(&sessionPid);
        pCtrl2->Release();

        if (sessionPid == 0) { if (pMeter) pMeter->Release(); continue; }

        // Walk up to root process (same exe name) — OBS-equivalent approach
        DWORD rootPid = GetRootPid(sessionPid, parents);
        std::wstring name = ExeNameOf(rootPid);
        if (name.empty()) name = ExeNameOf(sessionPid); // fallback
        if (name.empty()) { if (pMeter) pMeter->Release(); continue; }

        float peak = 0.f;
        if (pMeter) { pMeter->GetPeakValue(&peak); pMeter->Release(); }

        auto it = rootIdx.find(rootPid);
        if (it == rootIdx.end()) {
            rootIdx[rootPid] = (int)collected.size();
            collected.push_back({ rootPid, name, peak });
        } else {
            // Same process tree — keep highest peak
            if (peak > collected[it->second].peak)
                collected[it->second].peak = peak;
        }
    }

    pSessEnum->Release();

    int written = 0;
    for (auto& e : collected) {
        if (written >= maxCount) break;
        out[written].pid = e.rootPid;
        wcsncpy_s(out[written].exe_name, 260, e.name.c_str(), _TRUNCATE);
        out[written].peak_level = e.peak;
        written++;
    }

    CoUninitialize();
    return written;
}

// ── Worker: MTA thread + FTM handler + dynamic load (OBS pattern) ─────────────
static HRESULT g_coInitHR = E_FAIL;

static int ActivateAndStartCapture(DWORD pid, int includeChildren) {
    // 1. Dynamically load ActivateAudioInterfaceAsync (avoids static-link quirks)
    if (!LoadActivateAudioInterface()) {
        g_lastHR = E_NOTIMPL;
        return -1;
    }

    // 2. Init MTA on this dedicated thread (same as OBS CaptureThread)
    g_coInitHR = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(g_coInitHR) && g_coInitHR != S_FALSE) {
        g_lastHR = g_coInitHR;
        return -1;
    }

    AUDIOCLIENT_ACTIVATION_PARAMS p = {};
    p.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
    p.ProcessLoopbackParams.TargetProcessId  = pid;
    p.ProcessLoopbackParams.ProcessLoopbackMode =
        includeChildren ? PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE
                        : PROCESS_LOOPBACK_MODE_EXCLUDE_TARGET_PROCESS_TREE;

    PROPVARIANT pv = {};
    pv.vt             = VT_BLOB;
    pv.blob.cbSize    = sizeof(p);
    pv.blob.pBlobData = reinterpret_cast<BYTE*>(&p);

    // 3. Create handler with FTM so the async callback can fire from any apartment
    ActivationHandler* handler = new ActivationHandler();
    IActivateAudioInterfaceAsyncOperation* pOp = nullptr;

    HRESULT hr = g_pActivateAudioInterfaceAsync(
        VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK,
        __uuidof(IAudioClient),
        &pv, handler, &pOp);

    if (FAILED(hr)) {
        g_lastHR = hr;
        handler->Release();
        CoUninitialize();
        return -1;
    }
    if (pOp) pOp->Release();

    // 4. Wait for async completion (FTM lets callback fire on any thread)
    DWORD waitResult = WaitForSingleObject(handler->hDone, 5000);

    if (waitResult != WAIT_OBJECT_0 ||
        FAILED(handler->hrResult) || !handler->pClient) {
        g_lastHR = handler->hrResult;
        handler->Release();
        CoUninitialize();
        return -2;
    }

    IAudioClient* client = handler->pClient;
    handler->pClient = nullptr;
    handler->Release();

    // 5. Get the mix format from the *default render device* — NOT from the
    //    process-loopback IAudioClient.  The process-loopback client's
    //    GetMixFormat may return a format that Initialize then rejects
    //    (AUDCLNT_E_UNSUPPORTED_FORMAT).  OBS reads the format from the render
    //    endpoint and feeds it to the process-loopback Initialize.
    WAVEFORMATEX* pMix = nullptr;
    {
        IMMDeviceEnumerator* pEnum2 = nullptr;
        CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                         __uuidof(IMMDeviceEnumerator), (void**)&pEnum2);
        if (pEnum2) {
            IMMDevice* pRender = nullptr;
            pEnum2->GetDefaultAudioEndpoint(eRender, eConsole, &pRender);
            pEnum2->Release();
            if (pRender) {
                IAudioClient* pTmpClient = nullptr;
                pRender->Activate(__uuidof(IAudioClient), CLSCTX_ALL,
                                  nullptr, (void**)&pTmpClient);
                pRender->Release();
                if (pTmpClient) {
                    pTmpClient->GetMixFormat(&pMix);
                    pTmpClient->Release();
                }
            }
        }
    }
    // If we still have no format fall back to process-loopback client's own report.
    if (!pMix) client->GetMixFormat(&pMix);

    WAVEFORMATEXTENSIBLE wfx = {};
    WAVEFORMATEX* pFmt = nullptr;

    if (pMix && pMix->nSamplesPerSec > 0) {
        pFmt = pMix;
    } else {
        // Last-resort: 48 kHz 2ch 32-bit IEEE float
        static const GUID KSDATAFORMAT_SUBTYPE_IEEE_FLOAT_GUID =
            {0x00000003,0x0000,0x0010,{0x80,0x00,0x00,0xaa,0x00,0x38,0x9b,0x71}};
        wfx.Format.wFormatTag      = WAVE_FORMAT_EXTENSIBLE;
        wfx.Format.nChannels       = 2;
        wfx.Format.nSamplesPerSec  = 48000;
        wfx.Format.wBitsPerSample  = 32;
        wfx.Format.nBlockAlign     = 2 * 4;
        wfx.Format.nAvgBytesPerSec = 48000 * 2 * 4;
        wfx.Format.cbSize          = sizeof(WAVEFORMATEXTENSIBLE) - sizeof(WAVEFORMATEX);
        wfx.Samples.wValidBitsPerSample = 32;
        wfx.dwChannelMask          = SPEAKER_FRONT_LEFT | SPEAKER_FRONT_RIGHT;
        wfx.SubFormat              = KSDATAFORMAT_SUBTYPE_IEEE_FLOAT_GUID;
        pFmt = &wfx.Format;
    }

    UINT32 sr = pFmt->nSamplesPerSec;
    UINT32 ch = pFmt->nChannels;
    g_sr = sr;
    g_ch = ch;
    g_dbg_formatTag = pFmt->wFormatTag;
    g_dbg_bps       = pFmt->wBitsPerSample;

    // 6. Process-loopback Initialize REQUIRES AUDCLNT_STREAMFLAGS_EVENTCALLBACK.
    //    Buffer duration = 200 ms (2000000 × 100ns) — using 0 may be rejected.
    HANDLE hCaptureEvent = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    if (!hCaptureEvent) {
        g_lastHR = HRESULT_FROM_WIN32(GetLastError());
        if (pMix) CoTaskMemFree(pMix);
        client->Release();
        CoUninitialize();
        return -3;
    }

    // Process loopback requires BOTH AUDCLNT_STREAMFLAGS_LOOPBACK and
    // AUDCLNT_STREAMFLAGS_EVENTCALLBACK (per MSDN process-loopback sample).
    // Use 200 ms buffer; format is the default render endpoint mix format.
    hr = client->Initialize(AUDCLNT_SHAREMODE_SHARED,
                             AUDCLNT_STREAMFLAGS_LOOPBACK |
                             AUDCLNT_STREAMFLAGS_EVENTCALLBACK,
                             2000000, 0, pFmt, nullptr);

    if (pMix) CoTaskMemFree(pMix);

    if (FAILED(hr)) {
        g_lastHR = hr;
        CloseHandle(hCaptureEvent);
        client->Release();
        CoUninitialize();
        return -3;
    }

    // 7. Bind the auto-reset event to the audio engine buffer.
    hr = client->SetEventHandle(hCaptureEvent);
    if (FAILED(hr)) {
        g_lastHR = hr;
        CloseHandle(hCaptureEvent);
        client->Release();
        CoUninitialize();
        return -3;
    }

    {
        std::lock_guard<std::mutex> lk(g_mtx);
        g_ring.clear();
    }
    g_running = true;
    // CaptureThread takes ownership of hCaptureEvent and closes it on exit.
    g_thread  = std::thread(CaptureThread, client, sr, ch, hCaptureEvent);
    g_lastHR  = S_OK;
    return 0;
}

// Start per-process loopback capture.
// includeChildren: 1 = also capture child processes (e.g. Chrome renderer)
// Returns 0 on success, negative on error.
__declspec(dllexport) int __cdecl
MicTool_StartCapture(DWORD pid, int includeChildren) {
    MicTool_StopCapture();

    // Activation MUST happen on an MTA thread.
    // The calling thread (Python/tkinter) is already COM STA, so we spawn a
    // dedicated worker thread that can freely call CoInitializeEx(MTA).
    int result = -1;
    std::thread t([&]() { result = ActivateAndStartCapture(pid, includeChildren); });
    t.join();
    return result;
}

// Read captured mono float32 samples into caller's buffer.
// Returns number of samples actually written (may be < nSamples on underrun).
__declspec(dllexport) int __cdecl
MicTool_ReadAudio(float* buf, int nSamples) {
    if (!buf || nSamples <= 0) return 0;
    std::lock_guard<std::mutex> lk(g_mtx);
    int n = std::min(nSamples, (int)g_ring.size());
    for (int i = 0; i < n; i++) { buf[i] = g_ring.front(); g_ring.pop_front(); }
    return n;
}

// Returns the native sample rate of the captured stream.
__declspec(dllexport) UINT __cdecl
MicTool_GetSampleRate() { return g_sr; }

// Stop capture and release all resources.
__declspec(dllexport) void __cdecl
MicTool_StopCapture() {
    if (g_running.exchange(false))
        if (g_thread.joinable()) g_thread.join();
    std::lock_guard<std::mutex> lk(g_mtx);
    g_ring.clear();
}

// Returns the last HRESULT from StartCapture (0 = success / not yet called).
__declspec(dllexport) LONG __cdecl
MicTool_GetLastHR() { return (LONG)g_lastHR; }

// Diagnostic: calls ActivateAndStartCapture directly on the calling thread
// (no std::thread wrapper) — useful to isolate thread-vs-direct behaviour.
__declspec(dllexport) int __cdecl
MicTool_StartCaptureDirect(DWORD pid, int includeChildren) {
    MicTool_StopCapture();
    return ActivateAndStartCapture(pid, includeChildren);
}

// Returns the CoInitializeEx HRESULT from the activation thread (diagnostic).
__declspec(dllexport) LONG __cdecl
MicTool_GetCoInitHR() { return (LONG)g_coInitHR; }

// Returns format diagnostics (wFormatTag<<16 | wBitsPerSample) from last capture attempt.
__declspec(dllexport) UINT __cdecl
MicTool_GetFmtDbg() { return (g_dbg_formatTag << 16) | g_dbg_bps; }


// ── Device loopback (render-endpoint loopback) ────────────────────────────────
// Captures all audio rendered to a device — same as OBS "Desktop Audio".
// deviceId: device interface path (from MicTool_ListDevices) or NULL/empty for default.
// Returns 0 on success, -1 on failure.
__declspec(dllexport) int __cdecl
MicTool_StartDeviceLoopback(const WCHAR* deviceId) {
    MicTool_StopCapture();

    CoInitializeEx(nullptr, COINIT_MULTITHREADED);

    IMMDeviceEnumerator* pEnum = nullptr;
    CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                     __uuidof(IMMDeviceEnumerator), (void**)&pEnum);
    if (!pEnum) { g_lastHR = E_NOINTERFACE; return -1; }

    IMMDevice* pDev = nullptr;
    if (deviceId && deviceId[0])
        pEnum->GetDevice(deviceId, &pDev);
    else
        pEnum->GetDefaultAudioEndpoint(eRender, eConsole, &pDev);
    pEnum->Release();
    if (!pDev) { g_lastHR = E_NOINTERFACE; return -1; }

    IAudioClient* client = nullptr;
    HRESULT hr = pDev->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr, (void**)&client);
    pDev->Release();
    if (FAILED(hr) || !client) { g_lastHR = hr; return -1; }

    WAVEFORMATEX* pFmt = nullptr;
    client->GetMixFormat(&pFmt);
    if (!pFmt) { g_lastHR = E_POINTER; client->Release(); return -1; }
    UINT32 sr = pFmt->nSamplesPerSec;
    UINT32 ch = pFmt->nChannels;
    g_sr = sr; g_ch = ch;

    // Loopback capture: must pass the device mix format explicitly;
    // hnsBufferDuration = 0 lets the engine pick the minimum.
    hr = client->Initialize(AUDCLNT_SHAREMODE_SHARED,
                             AUDCLNT_STREAMFLAGS_LOOPBACK,
                             0, 0, pFmt, nullptr);
    CoTaskMemFree(pFmt);
    if (FAILED(hr)) { g_lastHR = hr; client->Release(); return -1; }

    { std::lock_guard<std::mutex> lk(g_mtx); g_ring.clear(); }
    g_running = true;
    // Device loopback uses polling (nullptr event = Sleep(5) path in CaptureThread)
    g_thread  = std::thread(CaptureThread, client, sr, ch, (HANDLE)nullptr);
    g_lastHR  = S_OK;
    return 0;
}

// ── Enumerate render devices (for device loopback) ────────────────────────────
struct DeviceEntry { WCHAR id[260]; WCHAR name[260]; };

__declspec(dllexport) int __cdecl
MicTool_ListDevices(DeviceEntry* out, int maxCount) {
    if (!out || maxCount <= 0) return 0;
    CoInitializeEx(nullptr, COINIT_MULTITHREADED);

    IMMDeviceEnumerator* pEnum = nullptr;
    CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                     __uuidof(IMMDeviceEnumerator), (void**)&pEnum);
    if (!pEnum) { CoUninitialize(); return 0; }

    IMMDeviceCollection* pColl = nullptr;
    pEnum->EnumAudioEndpoints(eRender, DEVICE_STATE_ACTIVE, &pColl);
    pEnum->Release();
    if (!pColl) { CoUninitialize(); return 0; }

    UINT total = 0, written = 0;
    pColl->GetCount(&total);
    for (UINT i = 0; i < total && (int)written < maxCount; i++) {
        IMMDevice* pDev = nullptr;
        if (FAILED(pColl->Item(i, &pDev))) continue;

        LPWSTR id = nullptr;
        pDev->GetId(&id);
        if (id) { wcsncpy_s(out[written].id, 260, id, _TRUNCATE); CoTaskMemFree(id); }

        IPropertyStore* pProps = nullptr;
        pDev->OpenPropertyStore(STGM_READ, &pProps);
        if (pProps) {
            PROPVARIANT pv; PropVariantInit(&pv);
            PROPERTYKEY PKEY_Device_FriendlyName = {
                {0xa45c254e,0xdf1c,0x4efd,{0x80,0x20,0x67,0xd1,0x46,0xa8,0x50,0xe0}}, 14};
            pProps->GetValue(PKEY_Device_FriendlyName, &pv);
            if (pv.vt == VT_LPWSTR && pv.pwszVal)
                wcsncpy_s(out[written].name, 260, pv.pwszVal, _TRUNCATE);
            PropVariantClear(&pv);
            pProps->Release();
        }
        pDev->Release();
        written++;
    }
    pColl->Release();
    CoUninitialize();
    return (int)written;
}

// ── Enumerate top-level windows → root process PIDs ──────────────────────────
// This is the OBS approach: enumerate visible windows rather than audio sessions
// so the user can pre-select Chrome/Firefox/Zen before they start playing audio,
// and so we get the MAIN process PID (not a sandboxed utility subprocess PID).
//
// Returns unique (rootPid, exeName) pairs for all visible, titled top-level
// windows, sorted by exe name.  No audio session is required.
struct WindowProcEntry { DWORD pid; WCHAR exe_name[260]; };

struct EnumWindowsCtx {
    std::unordered_map<DWORD,DWORD>* parents;
    std::unordered_map<DWORD,std::wstring>* seen; // rootPid -> exeName
};

static BOOL CALLBACK EnumWindowsProc(HWND hwnd, LPARAM lp) {
    if (!IsWindowVisible(hwnd)) return TRUE;
    // Must have a non-empty title (filters system/tray/invisible windows)
    WCHAR title[8] = {};
    if (GetWindowTextW(hwnd, title, 8) == 0) return TRUE;
    // Must be a top-level window (no owner)
    if (GetWindow(hwnd, GW_OWNER) != nullptr) return TRUE;

    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    if (pid == 0) return TRUE;

    auto* ctx = reinterpret_cast<EnumWindowsCtx*>(lp);
    DWORD rootPid = GetRootPid(pid, *ctx->parents);
    if (ctx->seen->count(rootPid)) return TRUE; // already recorded

    std::wstring name = ExeNameOf(rootPid);
    if (name.empty()) name = ExeNameOf(pid);
    if (name.empty()) return TRUE;

    (*ctx->seen)[rootPid] = name;
    return TRUE;
}

__declspec(dllexport) int __cdecl
MicTool_ListWindowProcesses(WindowProcEntry* out, int maxCount) {
    if (!out || maxCount <= 0) return 0;
    auto parents = SnapshotParents();
    std::unordered_map<DWORD,std::wstring> seen;
    EnumWindowsCtx ctx{ &parents, &seen };
    EnumWindows(EnumWindowsProc, reinterpret_cast<LPARAM>(&ctx));

    // Sort by exe name for a consistent, readable list
    std::vector<std::pair<DWORD,std::wstring>> v(seen.begin(), seen.end());
    std::sort(v.begin(), v.end(),
        [](auto& a, auto& b){ return a.second < b.second; });

    int written = 0;
    for (auto& [pid, name] : v) {
        if (written >= maxCount) break;
        out[written].pid = pid;
        wcsncpy_s(out[written].exe_name, 260, name.c_str(), _TRUNCATE);
        written++;
    }
    return written;
}

} // extern "C"

BOOL WINAPI DllMain(HINSTANCE, DWORD, LPVOID) { return TRUE; }
