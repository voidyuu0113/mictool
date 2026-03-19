// Standalone test: try ActivateAudioInterfaceAsync process loopback.
// Build: build_test.bat
// Run: test_capture.exe <PID>
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define INITGUID
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <audiopolicy.h>
#include <avrt.h>
#include <psapi.h>
#include <roapi.h>
#include <stdio.h>

#ifndef AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK
typedef enum AUDIOCLIENT_ACTIVATION_TYPE {
    AUDIOCLIENT_ACTIVATION_TYPE_DEFAULT          = 0,
    AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK = 1,
} AUDIOCLIENT_ACTIVATION_TYPE;
typedef struct AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS {
    DWORD  TargetProcessId;
    UINT32 ProcessLoopbackMode;
} AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS;
typedef struct AUDIOCLIENT_ACTIVATION_PARAMS {
    AUDIOCLIENT_ACTIVATION_TYPE ActivationType;
    union { AUDIOCLIENT_PROCESS_LOOPBACK_PARAMS ProcessLoopbackParams; };
} AUDIOCLIENT_ACTIVATION_PARAMS;
#define PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE 0
#define PROCESS_LOOPBACK_MODE_EXCLUDE_TARGET_PROCESS_TREE 1
static const PCWSTR VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK =
    L"VAD\\{2eef81be-33fa-4800-9670-1cd474972c3f}";
#endif

#pragma comment(lib, "ole32.lib")
#pragma comment(lib, "mmdevapi.lib")
#pragma comment(lib, "avrt.lib")
#pragma comment(lib, "psapi.lib")
#pragma comment(lib, "RuntimeObject.lib")
#pragma comment(lib, "user32.lib")

class ActivationHandler : public IActivateAudioInterfaceCompletionHandler {
    volatile LONG m_ref = 1;
public:
    IAudioClient* pClient  = nullptr;
    HRESULT       hrResult = E_FAIL;
    HANDLE        hDone;
    ActivationHandler() : hDone(CreateEventW(nullptr, TRUE, FALSE, nullptr)) {}
    ~ActivationHandler() { CloseHandle(hDone); if (pClient) pClient->Release(); }
    STDMETHODIMP QueryInterface(REFIID riid, void** ppv) override {
        if (riid == __uuidof(IUnknown) || riid == __uuidof(IActivateAudioInterfaceCompletionHandler))
        { *ppv = (IActivateAudioInterfaceCompletionHandler*)this; AddRef(); return S_OK; }
        *ppv = nullptr; return E_NOINTERFACE;
    }
    STDMETHODIMP_(ULONG) AddRef() override  { return InterlockedIncrement(&m_ref); }
    STDMETHODIMP_(ULONG) Release() override { ULONG r = InterlockedDecrement(&m_ref); if (!r) delete this; return r; }
    STDMETHODIMP ActivateCompleted(IActivateAudioInterfaceAsyncOperation* op) override {
        IUnknown* pUnk = nullptr;
        op->GetActivateResult(&hrResult, &pUnk);
        if (SUCCEEDED(hrResult) && pUnk) { pUnk->QueryInterface(__uuidof(IAudioClient),(void**)&pClient); pUnk->Release(); }
        SetEvent(hDone);
        return S_OK;
    }
};

int wmain(int argc, wchar_t** argv) {
    DWORD pid = (argc > 1) ? (DWORD)_wtoi(argv[1]) : GetCurrentProcessId();
    wprintf(L"Testing process loopback for PID=%lu\n", pid);
    wprintf(L"Current process PID=%lu\n", GetCurrentProcessId());

    // Try 1: MTA via RoInitialize
    wprintf(L"\n--- Try 1: RoInitialize (MTA) ---\n");
    HRESULT coHR = RoInitialize(RO_INIT_MULTITHREADED);
    wprintf(L"RoInitialize HR=0x%08X\n", (unsigned)coHR);

    AUDIOCLIENT_ACTIVATION_PARAMS p = {};
    p.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
    p.ProcessLoopbackParams.TargetProcessId   = pid;
    p.ProcessLoopbackParams.ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
    PROPVARIANT pv = {}; pv.vt = VT_BLOB; pv.blob.cbSize = sizeof(p); pv.blob.pBlobData = (BYTE*)&p;

    ActivationHandler* h = new ActivationHandler();
    IActivateAudioInterfaceAsyncOperation* pOp = nullptr;
    HRESULT hr = ActivateAudioInterfaceAsync(VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK, __uuidof(IAudioClient), &pv, h, &pOp);
    wprintf(L"ActivateAudioInterfaceAsync HR=0x%08X\n", (unsigned)hr);
    if (SUCCEEDED(hr)) {
        if (pOp) pOp->Release();
        // Pump messages + wait
        DWORD res = WAIT_TIMEOUT;
        DWORD deadline = GetTickCount() + 5000;
        while (true) {
            int rem = (int)(deadline - GetTickCount());
            if (rem <= 0) break;
            res = MsgWaitForMultipleObjects(1, &h->hDone, FALSE, rem, QS_ALLINPUT);
            if (res == WAIT_OBJECT_0) break;
            if (res == WAIT_OBJECT_0 + 1) { MSG msg; while (PeekMessageW(&msg,nullptr,0,0,PM_REMOVE)) { TranslateMessage(&msg); DispatchMessageW(&msg); } }
            else break;
        }
        wprintf(L"Wait result=%lu  callback HR=0x%08X  client=%p\n", res, (unsigned)h->hrResult, h->pClient);
    }
    h->Release();
    if (SUCCEEDED(coHR)) RoUninitialize();

    // Try 2: STA via CoInitialize with message pump
    wprintf(L"\n--- Try 2: CoInitialize STA ---\n");
    coHR = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    wprintf(L"CoInitializeEx(STA) HR=0x%08X\n", (unsigned)coHR);
    MSG dummy; PeekMessageW(&dummy, nullptr, WM_USER, WM_USER, PM_NOREMOVE);

    p = {}; p.ActivationType = AUDIOCLIENT_ACTIVATION_TYPE_PROCESS_LOOPBACK;
    p.ProcessLoopbackParams.TargetProcessId = pid;
    p.ProcessLoopbackParams.ProcessLoopbackMode = PROCESS_LOOPBACK_MODE_INCLUDE_TARGET_PROCESS_TREE;
    pv = {}; pv.vt = VT_BLOB; pv.blob.cbSize = sizeof(p); pv.blob.pBlobData = (BYTE*)&p;

    ActivationHandler* h2 = new ActivationHandler();
    pOp = nullptr;
    hr = ActivateAudioInterfaceAsync(VIRTUAL_AUDIO_DEVICE_PROCESS_LOOPBACK, __uuidof(IAudioClient), &pv, h2, &pOp);
    wprintf(L"ActivateAudioInterfaceAsync HR=0x%08X\n", (unsigned)hr);
    if (SUCCEEDED(hr)) {
        if (pOp) pOp->Release();
        DWORD res = WAIT_TIMEOUT;
        DWORD deadline = GetTickCount() + 5000;
        while (true) {
            int rem = (int)(deadline - GetTickCount());
            if (rem <= 0) break;
            res = MsgWaitForMultipleObjects(1, &h2->hDone, FALSE, rem, QS_ALLINPUT);
            if (res == WAIT_OBJECT_0) break;
            if (res == WAIT_OBJECT_0+1) { MSG msg; while(PeekMessageW(&msg,nullptr,0,0,PM_REMOVE)){TranslateMessage(&msg);DispatchMessageW(&msg);} }
            else break;
        }
        wprintf(L"Wait result=%lu  callback HR=0x%08X  client=%p\n", res, (unsigned)h2->hrResult, h2->pClient);
    }
    h2->Release();
    if (SUCCEEDED(coHR)) CoUninitialize();

    wprintf(L"\nDone. Press Enter...\n");
    getchar();
    return 0;
}
