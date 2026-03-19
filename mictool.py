#!/usr/bin/env python3
"""
MicTool — Real-time Microphone Audio Processor
  • Speaking mode : HP + Parametric EQ + Compressor  (no reverb)
  • Singing  mode : HP + Tone EQ + Compressor + Reverb
  • Bypass         : pass-through for A/B comparison
  • Outputs to any audio device (e.g. VB-Audio Virtual Cable → OBS)

Dependencies:
    pip install sounddevice numpy scipy
"""

import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import scipy.signal as sci_signal
import json
import queue
import threading
import ctypes
from ctypes import wintypes
import webbrowser
from pathlib import Path

try:
    import soundfile as sf
except Exception:
    sf = None

try:
    from pynput import keyboard as pynput_keyboard, mouse as pynput_mouse
except Exception:
    pynput_keyboard = None
    pynput_mouse = None

SETTINGS_FILE = Path(__file__).parent / "settings.json"

WM_APP = 0x8000
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
TRAY_CALLBACK_MSG = WM_APP + 1
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
IDI_APPLICATION = 32512
GWL_WNDPROC = -4
MF_STRING = 0x00000000
TPM_RETURNCMD = 0x0100
TPM_NONOTIFY = 0x0080
TRAY_CMD_RESTORE = 1001
TRAY_CMD_QUIT = 1002
LONG_PTR = ctypes.c_ssize_t
LRESULT = LONG_PTR


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]

# ══════════════════════════════════════════════════════════════════════════════
#  i18n — Internationalisation
# ══════════════════════════════════════════════════════════════════════════════

_LANG = 'zh_tw'   # default; overridden from settings at startup

_STRINGS: dict[str, dict[str, str]] = {
    # ── Tab names ─────────────────────────────────────────────────────────────
    'tab_speaking': {'zh_tw': '說話', 'en': 'Speaking', 'ja': '話す', 'ko': '말하기'},
    'tab_singing':  {'zh_tw': '唱歌', 'en': 'Singing',  'ja': '歌う', 'ko': '노래'},
    'tab_voice':    {'zh_tw': '變聲', 'en': 'Voice',    'ja': 'ボイス', 'ko': '보이스'},
    'tab_soundboard': {'zh_tw': '音效板', 'en': 'Soundboard', 'ja': 'サウンドボード', 'ko': '사운드보드'},
    'tab_hotkeys':  {'zh_tw': '快捷鍵', 'en': 'Hotkeys', 'ja': 'ホットキー', 'ko': '단축키'},
    'tab_help':     {'zh_tw': '說明', 'en': 'Help',     'ja': 'ヘルプ', 'ko': '도움말'},
    'tab_about':    {'zh_tw': '關於', 'en': 'About',    'ja': '情報',  'ko': '정보'},
    # ── Section headers ───────────────────────────────────────────────────────
    'sec_noise_gate':    {'zh_tw': 'Noise Gate', 'en': 'Noise Gate', 'ja': 'Noise Gate', 'ko': 'Noise Gate'},
    'sec_hp_filter':     {'zh_tw': 'High-Pass Filter', 'en': 'High-Pass Filter', 'ja': 'High-Pass Filter', 'ko': 'High-Pass Filter'},
    'sec_low_shelf':     {'zh_tw': 'Low Shelf EQ', 'en': 'Low Shelf EQ', 'ja': 'Low Shelf EQ', 'ko': 'Low Shelf EQ'},
    'sec_mid_peak':      {'zh_tw': 'Mid Peaking EQ', 'en': 'Mid Peaking EQ', 'ja': 'Mid Peaking EQ', 'ko': 'Mid Peaking EQ'},
    'sec_high_shelf':    {'zh_tw': 'High Shelf EQ', 'en': 'High Shelf EQ', 'ja': 'High Shelf EQ', 'ko': 'High Shelf EQ'},
    'sec_de_esser':      {'zh_tw': 'De-Esser  (防齒音)', 'en': 'De-Esser', 'ja': 'De-Esser', 'ko': 'De-Esser'},
    'sec_compressor':    {'zh_tw': 'Compressor', 'en': 'Compressor', 'ja': 'Compressor', 'ko': 'Compressor'},
    'sec_output_gain':   {'zh_tw': 'Output Gain', 'en': 'Output Gain', 'ja': 'Output Gain', 'ko': 'Output Gain'},
    'sec_warmth':        {'zh_tw': 'Warmth  (Low-Mid Boost)', 'en': 'Warmth  (Low-Mid Boost)', 'ja': 'Warmth  (Low-Mid Boost)', 'ko': 'Warmth  (Low-Mid Boost)'},
    'sec_presence':      {'zh_tw': 'Presence  (Upper-Mid)', 'en': 'Presence  (Upper-Mid)', 'ja': 'Presence  (Upper-Mid)', 'ko': 'Presence  (Upper-Mid)'},
    'sec_air':           {'zh_tw': 'Air  (High Shelf)', 'en': 'Air  (High Shelf)', 'ja': 'Air  (High Shelf)', 'ko': 'Air  (High Shelf)'},
    'sec_reverb':        {'zh_tw': 'Reverb  (Dattorro Plate)', 'en': 'Reverb  (Dattorro Plate)', 'ja': 'Reverb  (Dattorro Plate)', 'ko': 'Reverb  (Dattorro Plate)'},
    'sec_voice_mode':    {'zh_tw': 'Voice Changer Mode', 'en': 'Voice Changer Mode', 'ja': 'Voice Changer Mode', 'ko': 'Voice Changer Mode'},
    'sec_robot':         {'zh_tw': 'Robot — 載波頻率', 'en': 'Robot — Carrier Frequency', 'ja': 'Robot — Carrier Frequency', 'ko': 'Robot — 캐리어 주파수'},
    'sec_custom_pitch':  {'zh_tw': 'Custom Pitch Shift', 'en': 'Custom Pitch Shift', 'ja': 'Custom Pitch Shift', 'ko': 'Custom Pitch Shift'},
    'sec_gender_tune':   {'zh_tw': 'Gender Fine-Tune  (Female / Male)', 'en': 'Gender Fine-Tune  (Female / Male)', 'ja': 'Gender Fine-Tune  (Female / Male)', 'ko': 'Gender Fine-Tune  (Female / Male)'},
    'sec_app_loopback':  {'zh_tw': '🔊  App Audio Loopback', 'en': '🔊  App Audio Loopback', 'ja': '🔊  App Audio Loopback', 'ko': '🔊  App Audio Loopback'},
    # ── Slider labels ─────────────────────────────────────────────────────────
    'lbl_threshold': {'zh_tw': 'Threshold', 'en': 'Threshold', 'ja': 'Threshold', 'ko': 'Threshold'},
    'lbl_attack':    {'zh_tw': 'Attack',    'en': 'Attack',    'ja': 'Attack',    'ko': 'Attack'},
    'lbl_hold':      {'zh_tw': 'Hold',      'en': 'Hold',      'ja': 'Hold',      'ko': 'Hold'},
    'lbl_release':   {'zh_tw': 'Release',   'en': 'Release',   'ja': 'Release',   'ko': 'Release'},
    'lbl_cutoff':    {'zh_tw': 'Cutoff',    'en': 'Cutoff',    'ja': 'Cutoff',    'ko': 'Cutoff'},
    'lbl_freq':      {'zh_tw': 'Freq',      'en': 'Freq',      'ja': 'Freq',      'ko': 'Freq'},
    'lbl_gain':      {'zh_tw': 'Gain',      'en': 'Gain',      'ja': 'Gain',      'ko': 'Gain'},
    'lbl_q':         {'zh_tw': 'Q',         'en': 'Q',         'ja': 'Q',         'ko': 'Q'},
    'lbl_ratio':     {'zh_tw': 'Ratio',     'en': 'Ratio',     'ja': 'Ratio',     'ko': 'Ratio'},
    'lbl_makeup':    {'zh_tw': 'Makeup',    'en': 'Makeup',    'ja': 'Makeup',    'ko': 'Makeup'},
    'lbl_reduction': {'zh_tw': 'Reduction', 'en': 'Reduction', 'ja': 'Reduction', 'ko': 'Reduction'},
    'lbl_wet_mix':   {'zh_tw': 'Wet Mix',   'en': 'Wet Mix',   'ja': 'Wet Mix',   'ko': 'Wet Mix'},
    'lbl_pre_delay': {'zh_tw': 'Pre-delay', 'en': 'Pre-delay', 'ja': 'Pre-delay', 'ko': 'Pre-delay'},
    'lbl_decay':     {'zh_tw': 'Decay',     'en': 'Decay',     'ja': 'Decay',     'ko': 'Decay'},
    'lbl_brightness':{'zh_tw': 'Brightness','en': 'Brightness','ja': 'Brightness','ko': 'Brightness'},
    'lbl_damping':   {'zh_tw': 'Damping',   'en': 'Damping',   'ja': 'Damping',   'ko': 'Damping'},
    'lbl_mod_rate':  {'zh_tw': 'Mod Rate',  'en': 'Mod Rate',  'ja': 'Mod Rate',  'ko': 'Mod Rate'},
    'lbl_mod_depth': {'zh_tw': 'Mod Depth', 'en': 'Mod Depth', 'ja': 'Mod Depth', 'ko': 'Mod Depth'},
    'lbl_carrier':   {'zh_tw': 'Carrier',   'en': 'Carrier',   'ja': 'Carrier',   'ko': 'Carrier'},
    'lbl_semitones': {'zh_tw': 'Semitones', 'en': 'Semitones', 'ja': 'Semitones', 'ko': 'Semitones'},
    'lbl_formant':   {'zh_tw': 'Formant Shift', 'en': 'Formant Shift', 'ja': 'Formant Shift', 'ko': 'Formant Shift'},
    'lbl_pitch':     {'zh_tw': 'Pitch',     'en': 'Pitch',     'ja': 'Pitch',     'ko': 'Pitch'},
    # ── Buttons ───────────────────────────────────────────────────────────────
    'btn_start':     {'zh_tw': '▶  開始', 'en': '▶  Start', 'ja': '▶  開始', 'ko': '▶  시작'},
    'btn_stop':      {'zh_tw': '■  停止', 'en': '■  Stop',  'ja': '■  停止', 'ko': '■  정지'},
    'btn_save':      {'zh_tw': 'Save',   'en': 'Save',   'ja': 'Save',   'ko': 'Save'},
    'btn_load':      {'zh_tw': 'Load',   'en': 'Load',   'ja': 'Load',   'ko': 'Load'},
    'soundboard_import': {'zh_tw': '匯入音效', 'en': 'Import Sounds', 'ja': '音声を追加', 'ko': '사운드 추가'},
    'soundboard_clear': {'zh_tw': '清空全部', 'en': 'Clear All', 'ja': 'すべて削除', 'ko': '전체 삭제'},
    'soundboard_play': {'zh_tw': '播放', 'en': 'Play', 'ja': '再生', 'ko': '재생'},
    'soundboard_pause': {'zh_tw': '暫停', 'en': 'Pause', 'ja': '一時停止', 'ko': '일시정지'},
    'soundboard_remove': {'zh_tw': '移除', 'en': 'Remove', 'ja': '削除', 'ko': '삭제'},
    'tray_restore': {'zh_tw': '顯示主視窗', 'en': 'Restore Window', 'ja': 'ウィンドウを表示', 'ko': '창 복원'},
    'tray_quit': {'zh_tw': '結束程式', 'en': 'Quit', 'ja': '終了', 'ko': '종료'},
    'soundboard_intro': {
        'zh_tw': '匯入多個音效檔後即可在這裡快速播放。音效會混進目前輸出，適合搭配 OBS 或 VB Cable 使用。',
        'en': 'Import multiple sound files and trigger them here. Sounds are mixed into the current output for tools like OBS or VB Cable.',
        'ja': '複数の効果音ファイルを読み込み、ここからすぐ再生できます。音声は現在の出力へミックスされ、OBS や VB Cable と併用できます。',
        'ko': '여러 효과음 파일을 가져와 여기서 바로 재생할 수 있습니다. 사운드는 현재 출력에 믹스되어 OBS나 VB Cable과 함께 사용할 수 있습니다.',
    },
    'soundboard_intro2': {
        'zh_tw': '支援一次匯入多個檔案。若要讓音效真的送到輸出，請先啟動主輸出。',
        'en': 'You can import multiple files at once. Start the main output first if you want the sounds to reach your output device.',
        'ja': '複数ファイルを一度に読み込めます。効果音を実際に出力へ送るには、先にメイン出力を開始してください。',
        'ko': '여러 파일을 한 번에 가져올 수 있습니다. 효과음을 실제 출력으로 보내려면 먼저 메인 출력을 시작하세요.',
    },
    'soundboard_list_title': {'zh_tw': '音效清單', 'en': 'Sound List', 'ja': 'サウンド一覧', 'ko': '사운드 목록'},
    'soundboard_empty': {'zh_tw': '目前還沒有音效檔。', 'en': 'No sound files imported yet.', 'ja': 'まだ音声ファイルがありません。', 'ko': '아직 가져온 사운드 파일이 없습니다.'},
    'soundboard_volume': {'zh_tw': '音量', 'en': 'Volume', 'ja': '音量', 'ko': '볼륨'},
    'soundboard_missing_backend': {'zh_tw': '缺少 soundfile 套件，無法載入音效檔。', 'en': 'The soundfile package is missing, so audio files cannot be loaded.', 'ja': 'soundfile パッケージがないため、音声ファイルを読み込めません。', 'ko': 'soundfile 패키지가 없어 오디오 파일을 불러올 수 없습니다.'},
    'soundboard_import_title': {'zh_tw': '選擇音效檔', 'en': 'Select Sound Files', 'ja': '音声ファイルを選択', 'ko': '사운드 파일 선택'},
    'status_sound_added': {'zh_tw': '音效已加入', 'en': 'Sound added', 'ja': '音声を追加しました', 'ko': '사운드를 추가했습니다'},
    'status_sound_removed': {'zh_tw': '音效已移除', 'en': 'Sound removed', 'ja': '音声を削除しました', 'ko': '사운드를 삭제했습니다'},
    'status_sound_cleared': {'zh_tw': '已清空音效板', 'en': 'Soundboard cleared', 'ja': 'サウンドボードを空にしました', 'ko': '사운드보드를 비웠습니다'},
    'status_sound_played': {'zh_tw': '已觸發音效', 'en': 'Sound triggered', 'ja': '音声を再生しました', 'ko': '사운드를 재생했습니다'},
    'status_sound_paused': {'zh_tw': '音效已暫停', 'en': 'Sound paused', 'ja': '音声を一時停止しました', 'ko': '사운드를 일시정지했습니다'},
    'status_sent_to_tray': {'zh_tw': '已最小化到系統匣', 'en': 'Minimized to system tray', 'ja': 'システムトレイに最小化しました', 'ko': '시스템 트레이로 최소화했습니다'},
    'err_sound_load_title': {'zh_tw': '音效載入失敗', 'en': 'Failed to Load Sound', 'ja': '音声の読み込みに失敗しました', 'ko': '사운드 로드 실패'},
    'err_tray_unavailable_title': {'zh_tw': '系統匣不可用', 'en': 'Tray Unavailable', 'ja': 'トレイを利用できません', 'ko': '트레이를 사용할 수 없습니다'},
    'err_tray_unavailable_body': {'zh_tw': '目前環境無法建立系統匣圖示，視窗會維持一般最小化。', 'en': 'A tray icon could not be created in this environment, so the window will use normal minimization.', 'ja': 'この環境ではトレイアイコンを作成できないため、通常の最小化になります。', 'ko': '현재 환경에서는 트레이 아이콘을 만들 수 없어 일반 최소화로 동작합니다.'},
    # ── Device labels ─────────────────────────────────────────────────────────
    'dev_input':     {'zh_tw': 'Input:',   'en': 'Input:',   'ja': 'Input:',   'ko': 'Input:'},
    'dev_output':    {'zh_tw': 'Output:',  'en': 'Output:',  'ja': 'Output:',  'ko': 'Output:'},
    'dev_monitor':   {'zh_tw': 'Monitor:', 'en': 'Monitor:', 'ja': 'Monitor:', 'ko': 'Monitor:'},
    'dev_source':    {'zh_tw': 'Source:',  'en': 'Source:',  'ja': 'Source:',  'ko': 'Source:'},
    'dev_app_vol':   {'zh_tw': 'App Vol:', 'en': 'App Vol:', 'ja': 'App Vol:', 'ko': 'App Vol:'},
    # ── General ───────────────────────────────────────────────────────────────
    'off': {'zh_tw': 'Off', 'en': 'Off', 'ja': 'オフ', 'ko': '끄기'},
    'on':  {'zh_tw': 'On',  'en': 'On',  'ja': 'オン', 'ko': '켜기'},
    # ── About tab ─────────────────────────────────────────────────────────────
    'about_tagline': {
        'zh_tw': 'Real-time Mic Processor',
        'en':    'Real-time Mic Processor',
        'ja':    'リアルタイム マイク プロセッサ',
        'ko':    '실시간 마이크 프로세서',
    },
    'about_author_label': {
        'zh_tw': '作者',
        'en':    'Author',
        'ja':    '作者',
        'ko':    '작성자',
    },
    'about_email_label': {
        'zh_tw': 'Email',
        'en':    'Email',
        'ja':    'メール',
        'ko':    '이메일',
    },
    'about_twitter_label': {
        'zh_tw': '𝕏 / Twitter',
        'en':    '𝕏 / Twitter',
        'ja':    '𝕏 / Twitter',
        'ko':    '𝕏 / Twitter',
    },
    'about_license': {
        'zh_tw': (
            "本軟體免費供個人使用。\n\n"
            "✓  允許用於直播、Podcast、影片製作等創作性商業活動\n"
            "✓  允許個人修改供自用\n\n"
            "✗  嚴禁將本軟體（原版或修改版）以任何形式轉售、販賣或作為商業產品銷售\n"
            "✗  嚴禁以本軟體名義收費或販賣序號/授權\n\n"
            "如有合作或授權需求，請透過上方聯絡方式洽談。"
        ),
        'en': (
            "This software is free for personal use.\n\n"
            "✓  May be used for live streaming, podcasting, video production and similar creative commercial activities\n"
            "✓  Personal modifications for private use are permitted\n\n"
            "✗  Redistribution or resale of this software (original or modified) in any form is strictly prohibited\n"
            "✗  Selling licenses, keys, or charging fees under the name of this software is prohibited\n\n"
            "For collaboration or licensing inquiries, please use the contact information above."
        ),
        'ja': (
            "本ソフトウェアは個人利用に限り無料で使用できます。\n\n"
            "✓  配信・Podcast・動画制作などのクリエイティブな商業活動での使用は可\n"
            "✓  個人的な使用目的での改変は可\n\n"
            "✗  本ソフトウェア（原版・改変版問わず）の転売・販売・商業製品としての配布は厳禁\n"
            "✗  本ソフトウェアの名義でライセンスや認証キーを有償提供することは禁止\n\n"
            "ご協力・ライセンスに関するお問い合わせは上記の連絡先までどうぞ。"
        ),
        'ko': (
            "이 소프트웨어는 개인 사용에 한해 무료입니다.\n\n"
            "✓  라이브 스트리밍, 팟캐스트, 영상 제작 등 창작적 상업 활동에 사용 가능\n"
            "✓  개인적 용도의 수정 허용\n\n"
            "✗  이 소프트웨어(원본 또는 수정본)를 어떤 형태로든 재판매하거나 상업 제품으로 배포하는 것은 엄격히 금지\n"
            "✗  이 소프트웨어 명의로 라이선스, 키 판매 또는 유료 제공 금지\n\n"
            "협업 또는 라이선스 문의는 위의 연락처를 이용해 주세요."
        ),
    },
    # ── Help tab ──────────────────────────────────────────────────────────────
    'help_setup_title': {
        'zh_tw': '首次設定', 'en': 'First-time Setup', 'ja': '初期設定', 'ko': '초기 설정',
    },
    'help_setup_body': {
        'zh_tw': (
            "⚠️ 首次使用前，請先安裝 VB-Audio Virtual Cable（免費虛擬音效卡）\n"
            "安裝後，將本軟體的 Output 設為「CABLE Input」，\n"
            "再到 OBS 將麥克風來源設為「CABLE Output」。"
        ),
        'en': (
            "⚠️ Before first use, install VB-Audio Virtual Cable (free virtual audio device)\n"
            "After installing, set this app's Output to 'CABLE Input',\n"
            "then in OBS set your mic source to 'CABLE Output'."
        ),
        'ja': (
            "⚠️ 初回使用前に VB-Audio Virtual Cable（無料仮想オーディオデバイス）をインストールしてください。\n"
            "インストール後、本ソフトの Output を「CABLE Input」に設定し、\n"
            "OBS のマイクソースを「CABLE Output」に設定してください。"
        ),
        'ko': (
            "⚠️ 처음 사용하기 전에 VB-Audio Virtual Cable(무료 가상 오디오 장치)을 설치하세요.\n"
            "설치 후 이 앱의 Output을 'CABLE Input'으로 설정하고\n"
            "OBS에서 마이크 소스를 'CABLE Output'으로 설정하세요."
        ),
    },
    'help_param_title': {
        'zh_tw': '各項目說明',
        'en':    'Parameter Guide',
        'ja':    'パラメータ説明',
        'ko':    '파라미터 설명',
    },
    # ── Parameter descriptions (help tab) ────────────────────────────────────
    'help_gate_thr': {
        'zh_tw': '低於此電平的聲音會被靜音，防止環境雜音進入',
        'en':    'Silences audio below this level, prevents background noise',
        'ja':    'この閾値以下の音をミュートし、背景ノイズを防ぎます',
        'ko':    '이 레벨 이하의 소리를 무음 처리하여 배경 소음을 방지합니다',
    },
    'help_gate_att': {
        'zh_tw': '閘門打開的速度（越小=越快響應）',
        'en':    'How fast the gate opens (smaller = faster response)',
        'ja':    'ゲートが開く速さ（小さいほど早い）',
        'ko':    '게이트가 열리는 속도 (작을수록 빠름)',
    },
    'help_gate_hld': {
        'zh_tw': '聲音停止後保持開閘的時間',
        'en':    'How long the gate stays open after audio stops',
        'ja':    '音声が止まった後ゲートを開いたままにする時間',
        'ko':    '소리가 멈춘 후 게이트를 열어두는 시간',
    },
    'help_gate_rel': {
        'zh_tw': '閘門關閉的速度',
        'en':    'How fast the gate closes',
        'ja':    'ゲートが閉じる速さ',
        'ko':    '게이트가 닫히는 속도',
    },
    'help_hp_cutoff': {
        'zh_tw': '截掉低於此頻率的低頻（消除隆隆聲/空調雜音）',
        'en':    'Cuts frequencies below this point (removes rumble/AC noise)',
        'ja':    'この周波数以下の低音をカット（ハム音・空調ノイズ除去）',
        'ko':    '이 주파수 이하의 저음을 차단 (rumble/에어컨 소음 제거)',
    },
    'help_ls_freq_gain': {
        'zh_tw': '調整低頻段的整體音量，增加溫暖感或減少濁音',
        'en':    'Boosts or cuts the low frequency shelf, adds warmth or reduces muddiness',
        'ja':    '低域シェルフのブースト/カット。温かみの追加や濁り除去に',
        'ko':    '저주파수 셸프 부스트/컷, 따뜻함 추가 또는 탁함 제거',
    },
    'help_mid_freq_gain_q': {
        'zh_tw': '對特定中頻做增益/衰減，Q值越高影響範圍越窄',
        'en':    'Bell-shaped boost/cut at a specific frequency; higher Q = narrower band',
        'ja':    '特定の中域周波数をブースト/カット。Q値が高いほど帯域が狭い',
        'ko':    '특정 중간 주파수 부스트/컷, Q가 높을수록 좁은 대역',
    },
    'help_hs_freq_gain': {
        'zh_tw': '調整高頻段（亮度/清晰度）',
        'en':    'Boosts or cuts the high frequency shelf (brightness/clarity)',
        'ja':    '高域シェルフの調整（明瞭度・明るさ）',
        'ko':    '고주파수 셸프 조정 (밝기/명료도)',
    },
    'help_des_freq': {
        'zh_tw': '齒音偵測頻率（通常 5–8kHz 是 S/SH 音）',
        'en':    'Detection frequency for sibilance (typically 5–8kHz for S/SH sounds)',
        'ja':    'サ行・シ行などの歯擦音を検出する周波数（通常5〜8kHz）',
        'ko':    '치찰음 감지 주파수 (보통 S/SH 소리의 5~8kHz)',
    },
    'help_des_thr': {
        'zh_tw': '超過此電平才觸發齒音壓制',
        'en':    'Reduction only triggers above this level',
        'ja':    'この閾値を超えた場合のみ歯擦音を抑制',
        'ko':    '이 레벨을 초과할 때만 치찰음 억제 작동',
    },
    'help_des_red': {
        'zh_tw': '偵測到齒音時的衰減量',
        'en':    'How much the sibilance is reduced when detected',
        'ja':    '歯擦音が検出されたときの減衰量',
        'ko':    '치찰음이 감지될 때 감소량',
    },
    'help_cmp_thr': {
        'zh_tw': '超過此電平才開始壓縮',
        'en':    'Compression begins above this level',
        'ja':    'この閾値を超えると圧縮が始まる',
        'ko':    '이 레벨을 초과하면 압축 시작',
    },
    'help_cmp_ratio': {
        'zh_tw': '壓縮比例（2:1 = 超出部分減半）',
        'en':    'Compression amount (2:1 means excess is halved)',
        'ja':    '圧縮比（2:1 = 超過分が半減）',
        'ko':    '압축 비율 (2:1 = 초과분이 절반으로 감소)',
    },
    'help_cmp_att': {
        'zh_tw': '壓縮開始的反應時間',
        'en':    'How fast compression kicks in',
        'ja':    '圧縮が始まるまでの反応時間',
        'ko':    '압축이 시작되는 반응 시간',
    },
    'help_cmp_rel': {
        'zh_tw': '壓縮結束後恢復的時間',
        'en':    'How fast compression releases',
        'ja':    '圧縮解除後の回復時間',
        'ko':    '압축 해제 후 복구 시간',
    },
    'help_cmp_makeup': {
        'zh_tw': '壓縮後補償增益，讓輸出音量回到合適電平',
        'en':    'Post-compression gain to restore output level',
        'ja':    '圧縮後の補償ゲイン。出力レベルを適切な値に戻す',
        'ko':    '압축 후 보상 게인, 출력 레벨을 적절히 복구',
    },
    'help_rv_wet': {
        'zh_tw': '殘響混合比例（0=乾聲，1=全殘響）',
        'en':    'Reverb mix (0=dry, 1=full reverb)',
        'ja':    'リバーブのミックス量（0=ドライ、1=フルリバーブ）',
        'ko':    '리버브 혼합 비율 (0=건조, 1=전체 리버브)',
    },
    'help_rv_pre': {
        'zh_tw': '直達聲與殘響之間的延遲時間',
        'en':    'Delay between direct sound and reverb',
        'ja':    '直接音とリバーブの間の遅延時間',
        'ko':    '직접음과 리버브 사이의 지연 시간',
    },
    'help_rv_decay': {
        'zh_tw': '殘響衰減時間（越大=空間越大）',
        'en':    'Reverb decay time (higher = larger space)',
        'ja':    'リバーブの減衰時間（大きいほど広い空間）',
        'ko':    '리버브 감쇠 시간 (클수록 더 큰 공간)',
    },
    'help_lb_source': {
        'zh_tw': '選擇要混入的應用程式音訊來源',
        'en':    'Select which application\'s audio to mix in',
        'ja':    'ミックスするアプリケーションのオーディオを選択',
        'ko':    '믹스할 애플리케이션 오디오 소스 선택',
    },
    'help_lb_vol': {
        'zh_tw': '應用程式音訊的音量（不影響麥克風）',
        'en':    'Volume of the app audio (does not affect mic)',
        'ja':    'アプリオーディオの音量（マイクには影響しない）',
        'ko':    '앱 오디오 볼륨 (마이크에는 영향 없음)',
    },
    'help_vc_title': {
        'zh_tw': 'Voice Changer 模式說明',
        'en':    'Voice Changer Mode Descriptions',
        'ja':    'ボイスチェンジャーモード説明',
        'ko':    '보이스 체인저 모드 설명',
    },
    'help_vc_off': {
        'zh_tw': '關閉變聲，原始音色直通',
        'en':    'Disabled — clean pass-through, no pitch change',
        'ja':    '無効 — ピッチ変換なしでクリアにパススルー',
        'ko':    '비활성화 — 피치 변환 없이 클리어하게 통과',
    },
    'help_vc_robot': {
        'zh_tw': '環形調製產生機器人嗡嗡聲效果',
        'en':    'Ring modulator: creates robotic buzz effect',
        'ja':    'リングモジュレーター：ロボット的なブザー効果',
        'ko':    '링 변조기: 로봇 같은 버즈 효과 생성',
    },
    'help_vc_chipmunk': {
        'zh_tw': '+7 半音，卡通花栗鼠聲',
        'en':    '+7 semitones — cartoon / chipmunk voice',
        'ja':    '+7半音 — カートゥーン / チップマンク',
        'ko':    '+7 반음 — 만화 / 다람쥐 목소리',
    },
    'help_vc_deep': {
        'zh_tw': '−5 半音，怪物/低沉聲',
        'en':    '−5 semitones — monster / deep voice',
        'ja':    '−5半音 — モンスター / 低い声',
        'ko':    '−5 반음 — 괴물 / 낮은 목소리',
    },
    'help_vc_female': {
        'zh_tw': '共振峰升高 (×1.20) + 音高 +4 半音，男→女',
        'en':    'Formant warp ×1.20 + pitch +4 st — male → more feminine',
        'ja':    'フォルマント×1.20 + 音高+4半音 — 男性→女性寄り',
        'ko':    '포르만트 ×1.20 + 음높이 +4 반음 — 남→여성스러운',
    },
    'help_vc_male': {
        'zh_tw': '共振峰降低 (×0.83) + 音高 −3 半音，女→男',
        'en':    'Formant warp ×0.83 + pitch −3 st — female → more masculine',
        'ja':    'フォルマント×0.83 + 音高−3半音 — 女性→男性寄り',
        'ko':    '포르만트 ×0.83 + 음높이 −3 반음 — 여→남성스러운',
    },
    'help_vc_custom': {
        'zh_tw': '自訂半音移調，可搭配共振峰調整使用',
        'en':    'User-defined semitone shift; combine with formant for more control',
        'ja':    'ユーザー定義の半音シフト。フォルマントと組み合わせ可',
        'ko':    '사용자 정의 반음 이동; 포르만트와 함께 사용 가능',
    },
    # ── Language dialog ───────────────────────────────────────────────────────
    'lang_restart_msg': {
        'zh_tw': '請重新啟動以套用語言設定。\nPlease restart to apply language.\n再起動してください。\n재시작하세요。',
        'en':    'Please restart to apply language.\n請重新啟動以套用語言設定。\n再起動してください。\n재시작하세요。',
        'ja':    '再起動してください。\nPlease restart to apply language.\n請重新啟動以套用語言設定。\n재시작하세요。',
        'ko':    '재시작하세요。\nPlease restart to apply language.\n請重新啟動以套用語言設定。\n再起動してください。',
    },
    # ── Header ────────────────────────────────────────────────────────────────
    'hdr_tagline': {
        'zh_tw': 'Real-time Mic Processor  →  OBS',
        'en':    'Real-time Mic Processor  →  OBS',
        'ja':    'リアルタイム Mic プロセッサ  →  OBS',
        'ko':    '실시간 마이크 프로세서  →  OBS',
    },
    # ── Transport / device labels ─────────────────────────────────────────────
    'lbl_input':       {'zh_tw': '輸入:', 'en': 'Input:',       'ja': '入力:',       'ko': '입력:'},
    'lbl_output':      {'zh_tw': '輸出:', 'en': 'Output:',      'ja': '出力:',       'ko': '출력:'},
    'lbl_monitor':     {'zh_tw': '監聽:', 'en': 'Monitor:',     'ja': 'モニター:',    'ko': '모니터:'},
    'lbl_monitor_vol': {'zh_tw': 'Monitor 音量:', 'en': 'Monitor Vol:', 'ja': 'モニター音量:', 'ko': '모니터 볼륨:'},
    'lbl_source':      {'zh_tw': '來源:', 'en': 'Source:',      'ja': 'ソース:',      'ko': '소스:'},
    'lbl_app_vol':     {'zh_tw': 'App 音量:', 'en': 'App Vol:',  'ja': 'アプリ音量:', 'ko': '앱 볼륨:'},
    'lbl_level':       {'zh_tw': '音量:', 'en': 'Level:',       'ja': 'レベル:',      'ko': '레벨:'},
    'lbl_mode':        {'zh_tw': '模式:', 'en': 'Mode:',        'ja': 'モード:',      'ko': '모드:'},
    'lbl_off':         {'zh_tw': '關閉',  'en': 'Off',          'ja': 'オフ',         'ko': '끄기'},
    # ── App loopback section ──────────────────────────────────────────────────
    'lb_header':   {
        'zh_tw': '🔊  App 音訊混音',
        'en':    '🔊  App Audio Loopback',
        'ja':    '🔊  アプリ音声ミックス',
        'ko':    '🔊  앱 오디오 루프백',
    },
    'lb_subtitle': {
        'zh_tw': '（將任意 App 的輸出混入 DSP 鏈）',
        'en':    "(mix any app's output into DSP chain)",
        'ja':    '（任意アプリの音声を DSP に混入）',
        'ko':    '(모든 앱의 출력을 DSP 체인에 믹스)',
    },
    # ── Buttons ───────────────────────────────────────────────────────────────
    'btn_start':    {'zh_tw': '▶  開始', 'en': '▶  Start', 'ja': '▶  開始', 'ko': '▶  시작'},
    'btn_stop':     {'zh_tw': '■  停止', 'en': '■  Stop',  'ja': '■  停止', 'ko': '■  중지'},
    'btn_save':     {'zh_tw': '儲存',    'en': 'Save',     'ja': '保存',    'ko': '저장'},
    'btn_load':     {'zh_tw': '載入',    'en': 'Load',     'ja': '読込',    'ko': '불러오기'},
    'btn_bypass':   {'zh_tw': '⊘  旁通', 'en': '⊘  Bypass',  'ja': '⊘  バイパス', 'ko': '⊘  바이패스'},
    'btn_speaking': {'zh_tw': '🎤 說話',  'en': '🎤 Speaking','ja': '🎤 話す',     'ko': '🎤 말하기'},
    'btn_singing':  {'zh_tw': '🎵 唱歌',  'en': '🎵 Singing', 'ja': '🎵 歌う',     'ko': '🎵 노래'},
    # ── VB-Cable indicator ────────────────────────────────────────────────────
    'vb_ok':      {'zh_tw': '● VB Cable 已安裝', 'en': '● VB Cable OK',            'ja': '● VB Cable OK',       'ko': '● VB Cable OK'},
    'vb_missing': {'zh_tw': '● 未安裝 VB Cable', 'en': '● VB Cable not installed', 'ja': '● VB Cable 未インストール', 'ko': '● VB Cable 미설치'},
    # ── Lang dialog ───────────────────────────────────────────────────────────
    'lang_select_title': {
        'zh_tw': '選擇語言', 'en': 'Select Language',
        'ja': '言語を選択', 'ko': '언어 선택',
    },
    'lang_select_hint': {
        'zh_tw': '選擇後立即生效',
        'en':    'Change takes effect immediately',
        'ja':    '変更はすぐに反映されます',
        'ko':    '변경 즉시 적용됩니다',
    },
    'lang_dialog_title': {
        'zh_tw': '語言 / Language / 言語 / 언어',
        'en':    'Language / 語言 / 言語 / 언어',
        'ja':    '言語 / Language / 語言 / 언어',
        'ko':    '언어 / Language / 語言 / 言語',
    },
    'btn_ok': {
        'zh_tw': '確定', 'en': 'OK', 'ja': 'OK', 'ko': '확인',
    },
    'btn_cancel': {
        'zh_tw': '取消', 'en': 'Cancel', 'ja': 'キャンセル', 'ko': '취소',
    },
    'vb_tip_ready': {
        'zh_tw': '已偵測到 Virtual Cable，可直接用於 OBS 路由。',
        'en':    'Virtual Cable detected and ready for OBS routing.',
        'ja':    'Virtual Cable を検出しました。OBS ルーティングの準備完了です。',
        'ko':    'Virtual Cable이 감지되어 OBS 라우팅 준비가 완료되었습니다.',
    },
    'vb_tip_missing': {
        'zh_tw': '請先安裝 VB-Audio Virtual Cable（免費）以便將處理後音訊送到 OBS。',
        'en':    'Install VB-Audio Virtual Cable (free) to route processed audio to OBS.',
        'ja':    '処理後の音声を OBS に送るには VB-Audio Virtual Cable（無料）をインストールしてください。',
        'ko':    '처리된 오디오를 OBS로 보내려면 VB-Audio Virtual Cable(무료)을 설치하세요.',
    },
    'vb_route_title': {
        'zh_tw': 'OBS 路由', 'en': 'OBS Routing', 'ja': 'OBS ルーティング', 'ko': 'OBS 라우팅',
    },
    'vb_route_steps': {
        'zh_tw': (
            "{tip}\n\n"
            "步驟：\n"
            "1. 下載 VB-Audio Virtual Cable：\n"
            "   https://vb-audio.com/Cable/\n"
            "2. 安裝後重新開機\n"
            "3. 將 MicTool 的 Output 設為 CABLE Input\n"
            "4. 在 OBS：來源 → ＋ → 音訊輸入擷取\n"
            "   → 選擇 CABLE Output"
        ),
        'en': (
            "{tip}\n\n"
            "Steps:\n"
            "1. Download VB-Audio Virtual Cable:\n"
            "   https://vb-audio.com/Cable/\n"
            "2. Install and reboot\n"
            "3. Set MicTool Output to CABLE Input\n"
            "4. In OBS: Sources → + → Audio Input Capture\n"
            "   → select CABLE Output"
        ),
        'ja': (
            "{tip}\n\n"
            "手順:\n"
            "1. VB-Audio Virtual Cable をダウンロード:\n"
            "   https://vb-audio.com/Cable/\n"
            "2. インストール後に再起動\n"
            "3. MicTool の Output を CABLE Input に設定\n"
            "4. OBS で: ソース → ＋ → 音声入力キャプチャ\n"
            "   → CABLE Output を選択"
        ),
        'ko': (
            "{tip}\n\n"
            "단계:\n"
            "1. VB-Audio Virtual Cable 다운로드:\n"
            "   https://vb-audio.com/Cable/\n"
            "2. 설치 후 재부팅\n"
            "3. MicTool Output을 CABLE Input으로 설정\n"
            "4. OBS에서: 소스 → + → 오디오 입력 캡처\n"
            "   → CABLE Output 선택"
        ),
    },
    'voice_btn_off': {
        'zh_tw': '⊘  關閉', 'en': '⊘  Off', 'ja': '⊘  オフ', 'ko': '⊘  끄기',
    },
    'voice_btn_robot': {
        'zh_tw': '🤖 機器人', 'en': '🤖 Robot', 'ja': '🤖 ロボット', 'ko': '🤖 로봇',
    },
    'voice_btn_chipmunk': {
        'zh_tw': '🐿 花栗鼠', 'en': '🐿 Chipmunk', 'ja': '🐿 チップマンク', 'ko': '🐿 다람쥐',
    },
    'voice_btn_deep': {
        'zh_tw': '👹 低沉', 'en': '👹 Deep', 'ja': '👹 低音', 'ko': '👹 딥',
    },
    'voice_btn_female': {
        'zh_tw': '👧 女聲', 'en': '👧 Female', 'ja': '👧 女性', 'ko': '👧 여성',
    },
    'voice_btn_male': {
        'zh_tw': '🧔 男聲', 'en': '🧔 Male', 'ja': '🧔 男性', 'ko': '🧔 남성',
    },
    'voice_btn_custom': {
        'zh_tw': '🎛 自訂', 'en': '🎛 Custom', 'ja': '🎛 カスタム', 'ko': '🎛 사용자 정의',
    },
    'voice_hint_off': {
        'zh_tw': '變聲已關閉，原始音色直通',
        'en':    'Voice changer disabled — clean pass-through',
        'ja':    'ボイスチェンジャー無効 — そのまま通過',
        'ko':    '보이스 체인저 비활성화 — 원음 그대로 통과',
    },
    'voice_hint_robot': {
        'zh_tw': '環形調製，產生機器人嗡嗡聲效果',
        'en':    'Ring modulator: robotic buzz effect',
        'ja':    'リングモジュレーター: ロボット風の効果',
        'ko':    '링 변조기: 로봇 같은 버즈 효과',
    },
    'voice_hint_chipmunk': {
        'zh_tw': '+7 半音，卡通花栗鼠聲',
        'en':    '+7 semitones — cartoon / chipmunk',
        'ja':    '+7半音 — カートゥーン / チップマンク',
        'ko':    '+7 반음 — 만화 / 다람쥐',
    },
    'voice_hint_deep': {
        'zh_tw': '−5 半音，怪物或低沉聲',
        'en':    '−5 semitones — monster / deep voice',
        'ja':    '−5半音 — モンスター / 低い声',
        'ko':    '−5 반음 — 괴물 / 낮은 목소리',
    },
    'voice_hint_female': {
        'zh_tw': '+4 半音，較偏女聲',
        'en':    '+4 semitones — male → more feminine',
        'ja':    '+4半音 — 男性→女性寄り',
        'ko':    '+4 반음 — 남성에서 더 여성스럽게',
    },
    'voice_hint_male': {
        'zh_tw': '−3 半音，較偏男聲',
        'en':    '−3 semitones — female → more masculine',
        'ja':    '−3半音 — 女性→男性寄り',
        'ko':    '−3 반음 — 여성에서 더 남성스럽게',
    },
    'voice_hint_custom': {
        'zh_tw': '自訂：{value:+.1f} 半音',
        'en':    'Custom: {value:+.1f} semitones',
        'ja':    'カスタム: {value:+.1f} 半音',
        'ko':    '사용자 정의: {value:+.1f} 반음',
    },
    'vc_formant_hint': {
        'zh_tw': '  < 1.0 = 共振峰較低（偏男聲）  •  > 1.0 = 共振峰較高（偏女聲）',
        'en':    '  < 1.0 = lower formants (masculine)  •  > 1.0 = raise formants (feminine)',
        'ja':    '  < 1.0 = フォルマント低め（男性寄り）  •  > 1.0 = フォルマント高め（女性寄り）',
        'ko':    '  < 1.0 = 낮은 포르만트(남성적)  •  > 1.0 = 높은 포르만트(여성적)',
    },
    'status_saved': {
        'zh_tw': '設定已儲存。', 'en': 'Settings saved.', 'ja': '設定を保存しました。', 'ko': '설정을 저장했습니다.',
    },
    'status_loaded': {
        'zh_tw': '設定已載入。', 'en': 'Settings loaded.', 'ja': '設定を読み込みました。', 'ko': '설정을 불러왔습니다.',
    },
    'status_hotkey_saved': {
        'zh_tw': '快捷鍵已更新。', 'en': 'Hotkey updated.', 'ja': 'ホットキーを更新しました。', 'ko': '단축키를 업데이트했습니다.',
    },
    'err_start_title': {
        'zh_tw': '啟動錯誤', 'en': 'Start Error', 'ja': '起動エラー', 'ko': '시작 오류',
    },
    'err_save_title': {
        'zh_tw': '儲存錯誤', 'en': 'Save Error', 'ja': '保存エラー', 'ko': '저장 오류',
    },
    'err_load_title': {
        'zh_tw': '載入錯誤', 'en': 'Load Error', 'ja': '読込エラー', 'ko': '불러오기 오류',
    },
    'load_title': {
        'zh_tw': '載入', 'en': 'Load', 'ja': '読込', 'ko': '불러오기',
    },
    'load_none_body': {
        'zh_tw': '找不到已儲存的設定。',
        'en':    'No saved settings found.',
        'ja':    '保存された設定が見つかりません。',
        'ko':    '저장된 설정을 찾을 수 없습니다.',
    },
    'hotkeys_intro': {
        'zh_tw': '可在此綁定全域快捷鍵。程式在背景執行時也能觸發，支援鍵盤與滑鼠按鍵組合。',
        'en':    'Bind global hotkeys here. They work while the app is in the background and support keyboard plus mouse button combos.',
        'ja':    'ここでグローバルホットキーを設定できます。アプリがバックグラウンドでも動作し、キーボードとマウスボタンの組み合わせに対応します。',
        'ko':    '여기에서 전역 단축키를 설정할 수 있습니다. 앱이 백그라운드에 있어도 동작하며 키보드와 마우스 버튼 조합을 지원합니다.',
    },
    'hotkeys_intro2': {
        'zh_tw': '按「錄製」後，按下想要的組合鍵，放開後會自動完成。預設皆為空白。',
        'en':    'Click Record, press the combo you want, and release to finish automatically. All bindings are empty by default.',
        'ja':    '「録製」を押した後に使いたいキー組み合わせを押し、放せば自動的に登録されます。初期状態ではすべて未設定です。',
        'ko':    '기록을 누른 뒤 원하는 조합을 누르고 손을 떼면 자동으로 완료됩니다. 기본값은 모두 비어 있습니다.',
    },
    'hotkeys_unavailable': {
        'zh_tw': '目前無法啟用全域快捷鍵，請安裝 `pynput` 後重新啟動。',
        'en':    'Global hotkeys are unavailable right now. Install `pynput` and restart the app.',
        'ja':    '現在はグローバルホットキーを有効化できません。`pynput` をインストールして再起動してください。',
        'ko':    '현재 전역 단축키를 사용할 수 없습니다. `pynput`를 설치한 뒤 앱을 다시 시작하세요.',
    },
    'hotkeys_bindings_title': {
        'zh_tw': '快捷鍵綁定', 'en': 'Bindings', 'ja': 'バインド', 'ko': '바인딩',
    },
    'hotkeys_col_action': {
        'zh_tw': '功能', 'en': 'Action', 'ja': '機能', 'ko': '기능',
    },
    'hotkeys_col_binding': {
        'zh_tw': '綁定', 'en': 'Binding', 'ja': '割り当て', 'ko': '바인딩',
    },
    'hotkeys_record': {
        'zh_tw': '錄製', 'en': 'Record', 'ja': '録製', 'ko': '기록',
    },
    'hotkeys_clear': {
        'zh_tw': '清除', 'en': 'Clear', 'ja': '消去', 'ko': '지우기',
    },
    'hotkeys_empty': {
        'zh_tw': '未設定', 'en': 'Unassigned', 'ja': '未設定', 'ko': '미설정',
    },
    'hotkeys_record_title': {
        'zh_tw': '錄製快捷鍵', 'en': 'Record Hotkey', 'ja': 'ホットキー録製', 'ko': '단축키 기록',
    },
    'hotkeys_record_prompt': {
        'zh_tw': '請按下想要的快捷鍵組合，放開後會自動完成。',
        'en':    'Press the hotkey combo you want. It will finish automatically when you release it.',
        'ja':    '設定したいホットキーの組み合わせを押してください。離すと自動で完了します。',
        'ko':    '원하는 단축키 조합을 누르세요. 손을 떼면 자동으로 완료됩니다.',
    },
    'hotkeys_record_cancel': {
        'zh_tw': '取消', 'en': 'Cancel', 'ja': 'キャンセル', 'ko': '취소',
    },
    'hotkeys_section_audio': {
        'zh_tw': '音訊控制', 'en': 'Audio Control', 'ja': '音声制御', 'ko': '오디오 제어',
    },
    'hotkeys_section_mode': {
        'zh_tw': '處理模式', 'en': 'Processing Mode', 'ja': '処理モード', 'ko': '처리 모드',
    },
    'hotkeys_section_voice': {
        'zh_tw': '變聲模式', 'en': 'Voice Modes', 'ja': 'ボイスモード', 'ko': '보이스 모드',
    },
    'hotkey_toggle_output': {
        'zh_tw': '快速開關聲音輸出', 'en': 'Toggle Audio Output', 'ja': '音声出力の切替', 'ko': '오디오 출력 토글',
    },
    'hotkey_mode_speaking': {
        'zh_tw': '切換到說話模式', 'en': 'Switch to Speaking Mode', 'ja': '話すモードに切替', 'ko': '말하기 모드로 전환',
    },
    'hotkey_mode_singing': {
        'zh_tw': '切換到唱歌模式', 'en': 'Switch to Singing Mode', 'ja': '歌うモードに切替', 'ko': '노래 모드로 전환',
    },
    'hotkey_voice_off': {
        'zh_tw': '變聲關閉', 'en': 'Voice Off', 'ja': 'ボイスオフ', 'ko': '변성 끄기',
    },
    'hotkey_voice_robot': {
        'zh_tw': '機器人變聲', 'en': 'Robot Voice', 'ja': 'ロボットボイス', 'ko': '로봇 변성',
    },
    'hotkey_voice_chipmunk': {
        'zh_tw': '花栗鼠變聲', 'en': 'Chipmunk Voice', 'ja': 'チップマンクボイス', 'ko': '다람쥐 변성',
    },
    'hotkey_voice_deep': {
        'zh_tw': '低沉變聲', 'en': 'Deep Voice', 'ja': '低音ボイス', 'ko': '딥 보이스',
    },
    'hotkey_voice_female': {
        'zh_tw': '女聲變聲', 'en': 'Female Voice', 'ja': '女性ボイス', 'ko': '여성 보이스',
    },
    'hotkey_voice_male': {
        'zh_tw': '男聲變聲', 'en': 'Male Voice', 'ja': '男性ボイス', 'ko': '남성 보이스',
    },
    'hotkey_voice_custom': {
        'zh_tw': '自訂變聲', 'en': 'Custom Voice', 'ja': 'カスタムボイス', 'ko': '사용자 정의 보이스',
    },
}


def t(key: str) -> str:
    """Return the UI string for *key* in the current language, falling back to English."""
    row = _STRINGS.get(key, {})
    return row.get(_LANG) or row.get('en') or key


def tf(key: str, **kwargs) -> str:
    """Translate *key* and apply str.format kwargs if provided."""
    return t(key).format(**kwargs)

# Module-level list of (StringVar, key) pairs for live language switching
_I18N_VARS: list = []


def _mkvar(key: str) -> tk.StringVar:
    """Create a StringVar tracking *key*, register for live language updates."""
    v = tk.StringVar(value=t(key))
    _I18N_VARS.append((v, key))
    return v


HOTKEY_ACTIONS = [
    ('hotkeys_section_audio', [
        ('toggle_output', 'hotkey_toggle_output'),
    ]),
    ('hotkeys_section_mode', [
        ('mode_speaking', 'hotkey_mode_speaking'),
        ('mode_singing', 'hotkey_mode_singing'),
    ]),
    ('hotkeys_section_voice', [
        ('voice_off', 'hotkey_voice_off'),
        ('voice_robot', 'hotkey_voice_robot'),
        ('voice_chipmunk', 'hotkey_voice_chipmunk'),
        ('voice_deep', 'hotkey_voice_deep'),
        ('voice_female', 'hotkey_voice_female'),
        ('voice_male', 'hotkey_voice_male'),
        ('voice_custom', 'hotkey_voice_custom'),
    ]),
]


def _combo_sort_key(token: str):
    mod_order = {
        'ctrl': 0, 'shift': 1, 'alt': 2, 'cmd': 3,
    }
    if token in mod_order:
        return (0, mod_order[token], token)
    if token.startswith('mouse_'):
        return (2, 0, token)
    return (1, 0, token)


def _canonical_hotkey_tokens(tokens) -> tuple[str, ...]:
    cleaned = [str(tok).strip().lower() for tok in tokens if str(tok).strip()]
    return tuple(sorted(dict.fromkeys(cleaned), key=_combo_sort_key))


def _parse_hotkey_combo(combo: str) -> tuple[str, ...]:
    if not combo:
        return ()
    return _canonical_hotkey_tokens(combo.split('+'))


def _pretty_hotkey_token(token: str) -> str:
    mapping = {
        'ctrl': 'Ctrl',
        'shift': 'Shift',
        'alt': 'Alt',
        'cmd': 'Win',
        'space': 'Space',
        'enter': 'Enter',
        'tab': 'Tab',
        'esc': 'Esc',
        'backspace': 'Backspace',
        'delete': 'Delete',
        'up': 'Up',
        'down': 'Down',
        'left': 'Left',
        'right': 'Right',
        'page_up': 'Page Up',
        'page_down': 'Page Down',
        'home': 'Home',
        'end': 'End',
        'insert': 'Insert',
        'mouse_left': 'Mouse Left',
        'mouse_right': 'Mouse Right',
        'mouse_middle': 'Mouse Middle',
        'mouse_x1': 'Mouse X1',
        'mouse_x2': 'Mouse X2',
    }
    if token in mapping:
        return mapping[token]
    if len(token) == 1:
        return token.upper()
    if token.startswith('f') and token[1:].isdigit():
        return token.upper()
    return token.replace('_', ' ').title()


def format_hotkey_combo(combo: str) -> str:
    tokens = _parse_hotkey_combo(combo)
    return '+'.join(_pretty_hotkey_token(tok) for tok in tokens)


class GlobalHotkeyManager:
    def __init__(self, emit):
        self._emit = emit
        self.available = pynput_keyboard is not None and pynput_mouse is not None
        self._bindings: dict[str, frozenset[str]] = {}
        self._pressed: set[str] = set()
        self._active_actions: set[str] = set()
        self._capture_tokens: set[str] = set()
        self._capture_active = False
        self._key_listener = None
        self._mouse_listener = None
        self._lock = threading.Lock()

    def start(self):
        if not self.available or self._key_listener is not None:
            return
        self._key_listener = pynput_keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._mouse_listener = pynput_mouse.Listener(
            on_click=self._on_mouse_click,
        )
        self._key_listener.start()
        self._mouse_listener.start()

    def stop(self):
        for listener in (self._key_listener, self._mouse_listener):
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
        self._key_listener = None
        self._mouse_listener = None

    def set_binding(self, action: str, combo: str):
        tokens = frozenset(_parse_hotkey_combo(combo))
        with self._lock:
            if tokens:
                self._bindings[action] = tokens
            else:
                self._bindings.pop(action, None)
                self._active_actions.discard(action)

    def get_binding(self, action: str) -> str:
        tokens = self._bindings.get(action, frozenset())
        return '+'.join(tokens)

    def begin_capture(self):
        with self._lock:
            self._capture_tokens.clear()
            self._capture_active = True
            self._active_actions.clear()

    def cancel_capture(self):
        with self._lock:
            self._capture_tokens.clear()
            self._capture_active = False

    def _finish_capture_if_ready(self):
        with self._lock:
            if not self._capture_active or self._pressed or not self._capture_tokens:
                return
            combo = '+'.join(_canonical_hotkey_tokens(self._capture_tokens))
            self._capture_tokens.clear()
            self._capture_active = False
        self._emit(('capture_done', combo))

    def _key_to_token(self, key):
        if pynput_keyboard is None:
            return None
        special = {
            pynput_keyboard.Key.ctrl: 'ctrl',
            pynput_keyboard.Key.ctrl_l: 'ctrl',
            pynput_keyboard.Key.ctrl_r: 'ctrl',
            pynput_keyboard.Key.shift: 'shift',
            pynput_keyboard.Key.shift_l: 'shift',
            pynput_keyboard.Key.shift_r: 'shift',
            pynput_keyboard.Key.alt: 'alt',
            pynput_keyboard.Key.alt_l: 'alt',
            pynput_keyboard.Key.alt_r: 'alt',
            pynput_keyboard.Key.alt_gr: 'alt',
            pynput_keyboard.Key.cmd: 'cmd',
            pynput_keyboard.Key.cmd_l: 'cmd',
            pynput_keyboard.Key.cmd_r: 'cmd',
            pynput_keyboard.Key.space: 'space',
            pynput_keyboard.Key.enter: 'enter',
            pynput_keyboard.Key.tab: 'tab',
            pynput_keyboard.Key.esc: 'esc',
            pynput_keyboard.Key.backspace: 'backspace',
            pynput_keyboard.Key.delete: 'delete',
            pynput_keyboard.Key.up: 'up',
            pynput_keyboard.Key.down: 'down',
            pynput_keyboard.Key.left: 'left',
            pynput_keyboard.Key.right: 'right',
            pynput_keyboard.Key.page_up: 'page_up',
            pynput_keyboard.Key.page_down: 'page_down',
            pynput_keyboard.Key.home: 'home',
            pynput_keyboard.Key.end: 'end',
            pynput_keyboard.Key.insert: 'insert',
        }
        if key in special:
            return special[key]
        if isinstance(key, pynput_keyboard.KeyCode):
            if key.char and key.char.isprintable() and not key.char.isspace():
                return key.char.lower()
            if key.vk is not None:
                if 65 <= key.vk <= 90:
                    return chr(key.vk + 32)
                if 48 <= key.vk <= 57:
                    return chr(key.vk)
                if 96 <= key.vk <= 105:
                    return str(key.vk - 96)
                if 112 <= key.vk <= 123:
                    return f'f{key.vk - 111}'
        text = str(key).lower()
        if text.startswith('key.f'):
            return text.replace('key.', '')
        return None

    def _mouse_to_token(self, button):
        if pynput_mouse is None:
            return None
        mapping = {
            pynput_mouse.Button.left: 'mouse_left',
            pynput_mouse.Button.right: 'mouse_right',
            pynput_mouse.Button.middle: 'mouse_middle',
            getattr(pynput_mouse.Button, 'x1', None): 'mouse_x1',
            getattr(pynput_mouse.Button, 'x2', None): 'mouse_x2',
        }
        return mapping.get(button)

    def _update_press(self, token: str, pressed: bool):
        if not token:
            return
        with self._lock:
            if pressed:
                self._pressed.add(token)
                if self._capture_active:
                    self._capture_tokens.add(token)
            else:
                self._pressed.discard(token)
                self._active_actions = {
                    action for action in self._active_actions
                    if self._bindings.get(action, frozenset()).issubset(self._pressed)
                }
        if pressed:
            self._trigger_actions()
        else:
            self._finish_capture_if_ready()

    def _trigger_actions(self):
        to_fire = []
        with self._lock:
            if self._capture_active:
                return
            for action, combo in self._bindings.items():
                if combo and combo.issubset(self._pressed) and action not in self._active_actions:
                    self._active_actions.add(action)
                    to_fire.append(action)
        for action in to_fire:
            self._emit(('action', action))

    def _on_key_press(self, key):
        self._update_press(self._key_to_token(key), True)

    def _on_key_release(self, key):
        self._update_press(self._key_to_token(key), False)

    def _on_mouse_click(self, x, y, button, pressed):
        self._update_press(self._mouse_to_token(button), pressed)


class SoundboardMixer:
    def __init__(self):
        self._lock = threading.Lock()
        self._clips: dict[str, dict[str, object]] = {}

    def clear(self):
        with self._lock:
            self._clips.clear()

    def add_clip(self, clip_id: str, samples: np.ndarray, gain: float = 1.0):
        arr = np.asarray(samples, dtype=np.float32).reshape(-1)
        with self._lock:
            self._clips[clip_id] = {
                'samples': arr.copy(),
                'pos': 0,
                'playing': False,
                'gain': float(max(0.0, gain)),
            }

    def remove_clip(self, clip_id: str):
        with self._lock:
            self._clips.pop(clip_id, None)

    def set_gain(self, clip_id: str, gain: float):
        with self._lock:
            clip = self._clips.get(clip_id)
            if clip is not None:
                clip['gain'] = float(max(0.0, gain))

    def is_playing(self, clip_id: str) -> bool:
        with self._lock:
            clip = self._clips.get(clip_id)
            return bool(clip and clip.get('playing'))

    def toggle(self, clip_id: str) -> bool:
        with self._lock:
            clip = self._clips.get(clip_id)
            if clip is None:
                return False
            if clip['playing']:
                clip['playing'] = False
                return False
            if clip['pos'] >= len(clip['samples']):
                clip['pos'] = 0
            clip['playing'] = True
            return True

    def mix(self, frames: int) -> np.ndarray:
        if frames <= 0:
            return np.zeros(0, dtype=np.float32)
        out = np.zeros(frames, dtype=np.float32)
        with self._lock:
            if not self._clips:
                return out
            for clip in self._clips.values():
                if not clip.get('playing'):
                    continue
                data = clip['samples']
                pos = int(clip['pos'])
                if pos >= len(data):
                    clip['pos'] = 0
                    clip['playing'] = False
                    continue
                take = min(frames, len(data) - pos)
                out[:take] += data[pos:pos + take] * float(clip.get('gain', 1.0))
                pos += take
                if pos >= len(data):
                    clip['pos'] = 0
                    clip['playing'] = False
                else:
                    clip['pos'] = pos
        return np.clip(out, -1.0, 1.0)

    @staticmethod
    def load_file(path: str) -> np.ndarray:
        if sf is None:
            raise RuntimeError(t('soundboard_missing_backend'))
        data, src_sr = sf.read(path, dtype='float32', always_2d=True)
        if data.size == 0:
            return np.zeros(0, dtype=np.float32)
        mono = data.mean(axis=1).astype(np.float32)
        if int(src_sr) != SR and len(mono) > 0:
            target_len = max(1, int(round(len(mono) * SR / float(src_sr))))
            mono = sci_signal.resample(mono, target_len).astype(np.float32)
        return np.clip(mono, -1.0, 1.0)

# ──────────────────────────────────────────────────────────────────────────────
#  Global audio constants
# ──────────────────────────────────────────────────────────────────────────────
SR    = 44100   # sample rate (Hz)
BLOCK = 512     # callback block size — increase to 1024 if you hear dropouts

# ══════════════════════════════════════════════════════════════════════════════
#  DSP BUILDING BLOCKS
# ══════════════════════════════════════════════════════════════════════════════

class SOSFilter:
    """Single stateful SOS biquad — fast block processing via scipy sosfilt."""

    def __init__(self):
        self.sos    = np.array([[1., 0, 0, 1, 0, 0]], dtype=np.float64)
        self.zi     = np.zeros((1, 2), dtype=np.float64)
        self.bypass = True

    def _commit(self, sos: np.ndarray):
        self.sos    = np.atleast_2d(sos).astype(np.float64)
        self.zi     = sci_signal.sosfilt_zi(self.sos).astype(np.float64)
        self.bypass = False

    def highpass(self, fc: float, q: float = 0.707):
        if 2 < fc < SR / 2 - 10:
            self._commit(sci_signal.butter(2, fc / (SR / 2), btype='high', output='sos'))
        else:
            self.bypass = True

    def lowshelf(self, fc: float, gain_db: float):
        A, w0 = 10 ** (gain_db / 40), 2 * np.pi * fc / SR
        sA, c = np.sqrt(A), np.cos(w0)
        alpha = np.sin(w0) / np.sqrt(2)           # S = 1
        b0 = A * ((A+1) - (A-1)*c + 2*sA*alpha)
        b1 = 2*A * ((A-1) - (A+1)*c)
        b2 = A * ((A+1) - (A-1)*c - 2*sA*alpha)
        a0 = (A+1) + (A-1)*c + 2*sA*alpha
        a1 = -2 * ((A-1) + (A+1)*c)
        a2 = (A+1) + (A-1)*c - 2*sA*alpha
        self._commit([[b0/a0, b1/a0, b2/a0, 1, a1/a0, a2/a0]])

    def highshelf(self, fc: float, gain_db: float):
        A, w0 = 10 ** (gain_db / 40), 2 * np.pi * fc / SR
        sA, c = np.sqrt(A), np.cos(w0)
        alpha = np.sin(w0) / np.sqrt(2)
        b0 = A * ((A+1) + (A-1)*c + 2*sA*alpha)
        b1 = -2*A * ((A-1) + (A+1)*c)
        b2 = A * ((A+1) + (A-1)*c - 2*sA*alpha)
        a0 = (A+1) - (A-1)*c + 2*sA*alpha
        a1 = 2 * ((A-1) - (A+1)*c)
        a2 = (A+1) - (A-1)*c - 2*sA*alpha
        self._commit([[b0/a0, b1/a0, b2/a0, 1, a1/a0, a2/a0]])

    def peaking(self, fc: float, gain_db: float, Q: float = 2.0):
        if abs(gain_db) < 0.01:
            self.bypass = True
            return
        A, w0 = 10 ** (gain_db / 40), 2 * np.pi * fc / SR
        alpha = np.sin(w0) / (2 * Q)
        b0, b2 = 1 + alpha*A, 1 - alpha*A
        a0, a2 = 1 + alpha/A, 1 - alpha/A
        b1 = a1 = -2 * np.cos(w0)
        self._commit([[b0/a0, b1/a0, b2/a0, 1, a1/a0, a2/a0]])

    def process(self, x: np.ndarray) -> np.ndarray:
        if self.bypass:
            return x
        y, self.zi = sci_signal.sosfilt(self.sos, x.astype(np.float64), zi=self.zi)
        return y.astype(np.float32)


class Compressor:
    """Feed-forward compressor with soft knee and makeup gain."""

    def __init__(self):
        self.threshold = -20.0   # dBFS
        self.ratio     = 4.0
        self.attack    = 10.0    # ms
        self.release   = 100.0   # ms
        self.knee      = 6.0     # dB soft-knee width
        self.makeup    = 0.0     # dB
        self._env      = 0.0

    def process(self, x: np.ndarray) -> np.ndarray:
        att    = np.exp(-1.0 / (SR * max(self.attack,  0.1) / 1000.0))
        rel    = np.exp(-1.0 / (SR * max(self.release, 1.0) / 1000.0))
        makeup = 10 ** (self.makeup / 20.0)
        T, R, K = self.threshold, self.ratio, self.knee
        klo, khi = T - K / 2, T + K / 2
        y   = np.empty_like(x, dtype=np.float32)
        env = self._env
        for i in range(len(x)):
            xn  = float(x[i])
            lvl = 20.0 * np.log10(max(abs(xn), 1e-9))
            if lvl <= klo:
                gc = lvl
            elif lvl <= khi:
                gc = lvl + (1.0/R - 1.0) * (lvl - klo)**2 / (2.0 * K)
            else:
                gc = T + (lvl - T) / R
            gain = 10.0 ** ((gc - lvl) / 20.0)
            if gain < env:
                env = att * env + (1.0 - att) * gain
            else:
                env = rel * env + (1.0 - rel) * gain
            y[i] = np.float32(xn * env * makeup)
        self._env = env
        return y


class DeEsser:
    """Split-band de-esser — dynamically attenuates the sibilance band.

    The input is split into:
      • sibilance band  (HP above `freq`) — its level drives gain reduction
      • low band        (original − sibilance) — always passed through

    When the sibilance envelope exceeds `threshold`, it is attenuated by up
    to `reduction` dB, then recombined with the low band.
    """

    def __init__(self):
        self.freq      = 7000.0   # Hz — HP cutoff of detection/split band
        self.threshold = -25.0    # dBFS
        self.reduction = 8.0      # max dB of attenuation
        self.attack    = 1.5      # ms
        self.release   = 60.0     # ms
        self._env      = 0.0
        self._hp       = SOSFilter()
        self._rebuild()

    def _rebuild(self):
        self._hp.highpass(self.freq, q=0.707)

    def process(self, x: np.ndarray) -> np.ndarray:
        att = np.exp(-1.0 / (SR * max(self.attack,  0.1) / 1000.0))
        rel = np.exp(-1.0 / (SR * max(self.release, 1.0) / 1000.0))
        thr_lin = 10.0 ** (self.threshold / 20.0)
        min_gain = 10.0 ** (-self.reduction / 20.0)

        sib = self._hp.process(x.copy())   # sibilance band
        low = x - sib                       # complementary low band

        y   = np.empty_like(x, dtype=np.float32)
        env = self._env
        for i in range(len(x)):
            lvl = abs(float(sib[i]))
            if lvl > env:
                env = att * env + (1.0 - att) * lvl
            else:
                env = rel * env + (1.0 - rel) * lvl
            if env > thr_lin:
                # gain ramps from 1.0 → min_gain as env rises above threshold
                gain = max(min_gain, thr_lin / env)
            else:
                gain = 1.0
            y[i] = np.float32(float(low[i]) + float(sib[i]) * gain)
        self._env = env
        return y


class FormantShifter:
    """Formant-preserving voice gender transformer.

    Unlike a plain pitch shifter, this separately controls the vocal-tract
    resonances (formants) and the fundamental frequency:

      1. Cepstral liftering  — extracts the smooth spectral envelope (formants)
         from the fine structure (pitch harmonics).
      2. Frequency-axis warp — stretches/compresses the envelope while leaving
         the fine structure untouched → natural-sounding gender change.
      3. Phase-vocoder pitch — independently shifts F0 on top of the formant warp.

    Physiological basis
    -------------------
    Average male vocal-tract length ≈ 17.5 cm, female ≈ 14.5 cm.
    Ratio ≈ 0.83 → female formants are ~1/0.83 ≈ 1.20× higher than male.

    Parameters
    ----------
    formant  : float  warp ratio (> 1 raises formants → more feminine,
                                   < 1 lowers formants → more masculine)
    pitch_st : float  pitch shift in semitones (applied on top of formant warp)
    """

    def __init__(self, formant: float = 1.0, pitch_st: float = 0.0):
        self.formant  = formant
        self.pitch_st = pitch_st

        N = 2048; H = BLOCK          # N=2048, H=512 → 75% overlap
        self._N   = N
        self._H   = H
        self._win = np.sqrt(np.hanning(N)).astype(np.float64)
        self._exp = (2.0 * np.pi * np.arange(N // 2 + 1, dtype=np.float64) * H) / N
        # Cepstral lifter cutoff (quefrency bins) — keeps ~3–4 formant peaks
        self._lif     = 40
        # Phase-vocoder state
        self._in_buf  = np.zeros(N)
        self._last_ph = np.zeros(N // 2 + 1)
        self._syn_ph  = np.zeros(N // 2 + 1)
        self._out_buf = np.zeros(N + H * 8, dtype=np.float64)

    def process(self, x: np.ndarray) -> np.ndarray:
        N, H, win, exp = self._N, self._H, self._win, self._exp
        ratio = 2.0 ** (self.pitch_st / 12.0)

        # Shift new block into analysis buffer
        self._in_buf[:-H] = self._in_buf[H:]
        self._in_buf[-H:] = x.astype(np.float64)

        # ── Analysis FFT ──────────────────────────────────────────────────────
        spec = np.fft.rfft(self._in_buf * win)
        mag  = np.abs(spec)
        ph   = np.angle(spec)

        # ── Cepstral liftering: extract spectral envelope ─────────────────────
        log_mag  = np.log(mag + 1e-8)
        cep      = np.fft.irfft(log_mag, n=N)        # real cepstrum, length N
        # Keep only low-quefrency bins (smooth envelope); zero the rest
        lif = self._lif
        liftered           = np.zeros(N)
        liftered[:lif]     = cep[:lif]
        liftered[N-lif+1:] = cep[N-lif+1:]            # symmetric for real signal
        envelope = np.exp(np.fft.rfft(liftered).real)  # smooth linear envelope
        fine_mag = mag / (envelope + 1e-8)             # excitation / fine structure

        # ── Spectral envelope warp (formant shift) ────────────────────────────
        alpha = self.formant
        N2    = len(envelope)                            # N//2 + 1
        src   = np.clip(np.arange(N2, dtype=np.float64) / alpha, 0, N2 - 1)
        i0    = src.astype(int)
        i1    = np.minimum(i0 + 1, N2 - 1)
        frac  = src - i0
        env_w = envelope[i0] * (1.0 - frac) + envelope[i1] * frac   # warped envelope

        # Recombine: warped envelope × original fine structure
        mag_new = env_w * fine_mag

        # ── Phase vocoder for pitch shift ─────────────────────────────────────
        dp = ph - self._last_ph - exp
        self._last_ph = ph.copy()
        dp -= np.round(dp / (2.0 * np.pi)) * (2.0 * np.pi)
        self._syn_ph += (exp + dp) * ratio

        # ── Synthesis + OLA ───────────────────────────────────────────────────
        out_fr = np.fft.irfft(mag_new * np.exp(1j * self._syn_ph), N).real * win
        self._out_buf[:N] += out_fr * (2.0 * H / N)

        hop_s = max(1, round(H * ratio))
        chunk = self._out_buf[:hop_s].copy()
        self._out_buf[:len(self._out_buf) - hop_s] = self._out_buf[hop_s:]
        self._out_buf[len(self._out_buf) - hop_s:] = 0.0

        if hop_s == H:
            return chunk.astype(np.float32)
        idx  = np.linspace(0, hop_s - 1, H)
        i0s  = idx.astype(int)
        i1s  = np.minimum(i0s + 1, hop_s - 1)
        frac2 = idx - i0s
        return (chunk[i0s] * (1.0 - frac2) + chunk[i1s] * frac2).astype(np.float32)


class PitchShifter:
    """Real-time pitch shifter — phase-vocoder + linear resampling.

    Modes
    -----
    MODE_OFF      bypass
    MODE_ROBOT    ring-modulate with a sine carrier (robotic buzz)
    MODE_CHIPMUNK +7 semitones  (cartoon / chipmunk)
    MODE_DEEP     -5 semitones  (monster / deep)
    MODE_FEMALE   +4 semitones  (male → more feminine)
    MODE_MALE     -3 semitones  (female → more masculine)
    MODE_CUSTOM   user-defined semitones slider

    Algorithm
    ---------
    Analysis: STFT frame (N=2048, hop=BLOCK=512, sqrt-Hann window)
    Phase vocoder: track instantaneous frequencies, advance synthesis phase
                   by ratio to shift pitch while preserving formants roughly.
    Synthesis: IFFT → overlap-add → extract hop_s samples → resample to BLOCK.
    """

    MODE_OFF = 0; MODE_ROBOT = 1; MODE_CHIPMUNK = 2
    MODE_DEEP = 3; MODE_FEMALE = 4; MODE_MALE = 5; MODE_CUSTOM = 6

    _SEMITONES = {
        MODE_OFF: 0.0, MODE_ROBOT: 0.0,
        MODE_CHIPMUNK:  7.0, MODE_DEEP:   -5.0,
        MODE_FEMALE:    4.0, MODE_MALE:   -3.0,
        MODE_CUSTOM:    0.0,
    }

    def __init__(self):
        self.mode      = self.MODE_OFF
        self.custom_st = 0.0      # semitones for MODE_CUSTOM
        self.robot_hz  = 80.0     # carrier frequency for robot mode
        # Formant shifter used exclusively for FEMALE / MALE modes
        self._fs = FormantShifter(formant=1.0, pitch_st=0.0)

        N = 2048; H = BLOCK       # N=2048, H=512 → 75 % overlap
        self._N   = N
        self._H   = H
        self._win = np.sqrt(np.hanning(N)).astype(np.float64)
        # Expected phase advance per analysis hop for each bin
        self._exp = (2.0 * np.pi * np.arange(N // 2 + 1, dtype=np.float64) * H) / N
        # Analysis state
        self._in_buf  = np.zeros(N)
        self._last_ph = np.zeros(N // 2 + 1)
        self._syn_ph  = np.zeros(N // 2 + 1)
        # Output accumulation buffer (large enough for any reasonable ratio)
        self._out_buf = np.zeros(N + H * 8, dtype=np.float64)
        # Robot ring-mod phase
        self._rob_ph  = 0.0

    def _semitones(self) -> float:
        return self.custom_st if self.mode == self.MODE_CUSTOM \
               else self._SEMITONES.get(self.mode, 0.0)

    def process(self, x: np.ndarray) -> np.ndarray:
        if self.mode == self.MODE_OFF:
            return x
        if self.mode == self.MODE_ROBOT:
            return self._ring_mod(x)
        # Female / Male: cepstral formant warp + pitch shift (sounds natural)
        if self.mode in (self.MODE_FEMALE, self.MODE_MALE):
            return self._fs.process(x)
        st = self._semitones()
        if abs(st) < 0.01:
            return x
        return self._pv_shift(x, 2.0 ** (st / 12.0))

    # ── Robot: ring-modulate signal with a pure sine ──────────────────────────
    def _ring_mod(self, x: np.ndarray) -> np.ndarray:
        inc = 2.0 * np.pi * self.robot_hz / SR
        t   = np.arange(len(x)) * inc + self._rob_ph
        self._rob_ph = (self._rob_ph + len(x) * inc) % (2.0 * np.pi)
        return (x * np.sin(t).astype(np.float32))

    # ── Phase-vocoder pitch shift ─────────────────────────────────────────────
    def _pv_shift(self, x: np.ndarray, ratio: float) -> np.ndarray:
        N, H, win, exp = self._N, self._H, self._win, self._exp

        # Shift new block into analysis buffer
        self._in_buf[:-H] = self._in_buf[H:]
        self._in_buf[-H:] = x.astype(np.float64)

        # Analysis FFT
        spec = np.fft.rfft(self._in_buf * win)
        mag  = np.abs(spec)
        ph   = np.angle(spec)

        # True instantaneous frequency (phase derivative)
        dp = ph - self._last_ph - exp
        self._last_ph = ph.copy()
        dp -= np.round(dp / (2.0 * np.pi)) * (2.0 * np.pi)   # wrap to [-π,π]
        true_f = exp + dp

        # Advance synthesis phase proportionally to pitch ratio
        self._syn_ph += true_f * ratio

        # Synthesis IFFT + overlap-add
        out_fr = np.fft.irfft(mag * np.exp(1j * self._syn_ph), N).real * win
        norm   = 2.0 * H / N     # Hann-window OLA normalisation (hop = N/4)
        self._out_buf[:N] += out_fr * norm

        # Extract hop_s = H*ratio samples, resample back to H samples
        hop_s = max(1, round(H * ratio))
        chunk = self._out_buf[:hop_s].copy()
        self._out_buf[:len(self._out_buf) - hop_s] = self._out_buf[hop_s:]
        self._out_buf[len(self._out_buf) - hop_s:] = 0.0

        if hop_s == H:
            return chunk.astype(np.float32)

        # Linear interpolation resample: hop_s → H
        idx  = np.linspace(0, hop_s - 1, H)
        i0   = idx.astype(int)
        i1   = np.minimum(i0 + 1, hop_s - 1)
        frac = idx - i0
        return (chunk[i0] * (1.0 - frac) + chunk[i1] * frac).astype(np.float32)


class Reverb:
    """Dattorro (1997) plate reverb — warm, dense, natural tail.

    Reference: J. Dattorro, "Effect Design Part 1: Reverberator and Other
    Filters", JAES Vol.45 No.9, 1997.

    Signal flow:
      input → BW-LP → pre-delay → 4-stage input diffusion (APF cascade)
        → figure-8 cross-coupled tank:
            Tank A: mod-APF → delay → HP-damp LP → fixed APF → delay
            Tank B: mod-APF → delay → HP-damp LP → fixed APF → delay
            (A feeds B, B feeds A, scaled by `decay`)
      output = (tank-A-out + tank-B-out) × 0.5

    The LFO-modulated APFs in each tank create the characteristic warm
    "shimmer-hum" that plate reverbs are known for, with no metallic ringing.
    """

    _SR0 = 29761.0   # Dattorro's original normalised sample rate

    def __init__(self):
        self.wet       = 0.22
        self.pre_delay = 20    # ms
        self.decay     = 0.50  # 0–0.95 — feedback (longer tail = higher value)
        self.bandwidth = 0.80  # 0–1   — input HF content (1=bright, 0.7=warm)
        self.damping   = 0.35  # 0–1   — HF roll-off in tank (0=bright, 1=dark)
        self.mod_rate  = 1.0   # Hz    — LFO speed
        self.mod_depth = 16.0  # smp   — LFO peak excursion
        self._bw_s     = 0.0
        self._lp_A     = self._lp_B = 0.0
        self._lfo_ph   = 0.0
        self._node_A   = self._node_B = 0.0
        self._build()

    def _build(self):
        sc  = SR / self._SR0       # ~1.482 at 44100 Hz
        md  = int(self.mod_depth) + 4

        # Pre-delay line
        pd_n       = max(int(self.pre_delay * SR / 1000), 1)
        self._pd   = np.zeros(pd_n, np.float32)
        self._pd_p = 0

        # Input diffusion: 4 fixed allpass filters
        # buf size = delay exactly → buf[pos] is `delay` samples old
        id_d = [int(d * sc) for d in [142, 107, 379, 277]]
        self._id_b = [np.zeros(max(d, 2), np.float32) for d in id_d]
        self._id_p = [0] * 4
        self._id_g = [0.75, 0.75, 0.625, 0.625]

        # Tank A ─────────────────────────────────────────────────────────────
        # Modulated APF: separate write/read; buf bigger than nominal delay
        ma_d         = int(672 * sc)
        self._ma     = np.zeros(ma_d + md, np.float32)
        self._ma_p   = 0
        self._ma_d   = ma_d
        # D1: pure delay (read-before-write circular)
        self._D1     = np.zeros(max(int(4453 * sc), 1), np.float32)
        self._D1_p   = 0
        # Fixed APF7 (buf size = delay → buf[pos] is delay samples old)
        self._a7     = np.zeros(max(int(1800 * sc), 2), np.float32)
        self._a7_p   = 0
        # D2: pure delay
        self._D2     = np.zeros(max(int(3720 * sc), 1), np.float32)
        self._D2_p   = 0

        # Tank B ─────────────────────────────────────────────────────────────
        mb_d         = int(908 * sc)
        self._mb     = np.zeros(mb_d + md, np.float32)
        self._mb_p   = 0
        self._mb_d   = mb_d
        self._D3     = np.zeros(max(int(4217 * sc), 1), np.float32)
        self._D3_p   = 0
        self._a8     = np.zeros(max(int(2656 * sc), 2), np.float32)
        self._a8_p   = 0
        self._D4     = np.zeros(max(int(3163 * sc), 1), np.float32)
        self._D4_p   = 0

    def rebuild(self):
        self._build()   # fresh buffers; continuous params preserved in attrs

    def process(self, x: np.ndarray) -> np.ndarray:
        wet    = self.wet
        dry    = 1.0 - wet
        bw     = self.bandwidth
        damp   = self.damping
        decay  = self.decay
        depth  = self.mod_depth
        lfo_inc = 2.0 * np.pi * self.mod_rate / SR

        bw_s   = self._bw_s
        lp_A   = self._lp_A
        lp_B   = self._lp_B
        lfo_ph = self._lfo_ph
        node_A = self._node_A
        node_B = self._node_B

        id_b, id_p, id_g = self._id_b, self._id_p, self._id_g
        ma,  ma_p,  ma_d  = self._ma,  self._ma_p,  self._ma_d
        mb,  mb_p,  mb_d  = self._mb,  self._mb_p,  self._mb_d
        D1,  D1_p         = self._D1,  self._D1_p
        D2,  D2_p         = self._D2,  self._D2_p
        D3,  D3_p         = self._D3,  self._D3_p
        D4,  D4_p         = self._D4,  self._D4_p
        a7,  a7_p         = self._a7,  self._a7_p
        a8,  a8_p         = self._a8,  self._a8_p
        pd,  pd_p         = self._pd,  self._pd_p
        pd_n = len(pd);  ma_n = len(ma);  mb_n = len(mb)
        D1_n = len(D1);  D2_n = len(D2);  D3_n = len(D3);  D4_n = len(D4)
        a7_n = len(a7);  a8_n = len(a8)

        y = np.empty_like(x, np.float32)

        for i in range(len(x)):
            xn = float(x[i])

            # ── Pre-delay ──────────────────────────────────────────────────
            pd_out  = float(pd[pd_p])
            pd[pd_p] = np.float32(xn)
            pd_p    = (pd_p + 1) % pd_n

            # ── Bandwidth LP (input HF softening) ─────────────────────────
            bw_s = bw * pd_out + (1.0 - bw) * bw_s
            sig  = bw_s

            # ── Input diffusion (4 cascaded allpass) ───────────────────────
            for k in range(4):
                buf = id_b[k];  p = id_p[k];  g = id_g[k]
                old = float(buf[p])
                v   = sig + g * old
                buf[p]  = np.float32(v)
                id_p[k] = (p + 1) % len(buf)
                sig = old - g * v

            # ── LFO ────────────────────────────────────────────────────────
            lfo     = depth * np.sin(lfo_ph)
            lfo_ph += lfo_inc
            if lfo_ph > 6.2831853: lfo_ph -= 6.2831853

            # ══ TANK A: sig + decay·node_B ════════════════════════════════
            a_in = sig + decay * node_B

            # Modulated APF A (LFO positive phase)
            rp   = (ma_p - ma_d - lfo) % ma_n
            rp0  = int(rp);  rp1 = (rp0 + 1) % ma_n;  frac = rp - rp0
            ma_old = float(ma[rp0]) * (1.0 - frac) + float(ma[rp1]) * frac
            ma_v   = a_in + 0.7 * ma_old
            ma[ma_p] = np.float32(ma_v)
            ma_p     = (ma_p + 1) % ma_n
            out_ma   = ma_old - 0.7 * ma_v

            # D1 (pure delay: read oldest, write new, advance)
            D1_out  = float(D1[D1_p])
            D1[D1_p] = np.float32(out_ma)
            D1_p    = (D1_p + 1) % D1_n

            # HF damping LP A
            lp_A = (1.0 - damp) * D1_out + damp * lp_A

            # Fixed APF7 (g = 0.5)
            old_a7   = float(a7[a7_p])
            v_a7     = lp_A + 0.5 * old_a7
            a7[a7_p] = np.float32(v_a7)
            a7_p     = (a7_p + 1) % a7_n
            out_a7   = old_a7 - 0.5 * v_a7

            # D2
            D2_out  = float(D2[D2_p])
            D2[D2_p] = np.float32(out_a7)
            D2_p    = (D2_p + 1) % D2_n
            node_A  = D2_out

            # ══ TANK B: sig + decay·node_A ════════════════════════════════
            b_in = sig + decay * node_A

            # Modulated APF B (LFO negative phase — opposite to A)
            rp   = (mb_p - mb_d + lfo) % mb_n
            rp0  = int(rp);  rp1 = (rp0 + 1) % mb_n;  frac = rp - rp0
            mb_old = float(mb[rp0]) * (1.0 - frac) + float(mb[rp1]) * frac
            mb_v   = b_in + 0.7 * mb_old
            mb[mb_p] = np.float32(mb_v)
            mb_p     = (mb_p + 1) % mb_n
            out_mb   = mb_old - 0.7 * mb_v

            # D3
            D3_out  = float(D3[D3_p])
            D3[D3_p] = np.float32(out_mb)
            D3_p    = (D3_p + 1) % D3_n

            # HF damping LP B
            lp_B = (1.0 - damp) * D3_out + damp * lp_B

            # Fixed APF8 (g = 0.5)
            old_a8   = float(a8[a8_p])
            v_a8     = lp_B + 0.5 * old_a8
            a8[a8_p] = np.float32(v_a8)
            a8_p     = (a8_p + 1) % a8_n
            out_a8   = old_a8 - 0.5 * v_a8

            # D4
            D4_out  = float(D4[D4_p])
            D4[D4_p] = np.float32(out_a8)
            D4_p    = (D4_p + 1) % D4_n
            node_B  = D4_out

            # ── Output: blend both tank outputs ────────────────────────────
            y[i] = np.float32(dry * xn + wet * (node_A + node_B) * 0.5)

        # Write state back
        self._bw_s   = bw_s;   self._lp_A = lp_A;    self._lp_B  = lp_B
        self._lfo_ph = lfo_ph; self._node_A = node_A; self._node_B = node_B
        self._ma_p = ma_p; self._mb_p = mb_p
        self._D1_p = D1_p; self._D2_p = D2_p; self._D3_p = D3_p; self._D4_p = D4_p
        self._a7_p = a7_p; self._a8_p = a8_p; self._pd_p = pd_p
        self._id_p = id_p
        return y


# ══════════════════════════════════════════════════════════════════════════════
#  PROCESSING CHAINS
# ══════════════════════════════════════════════════════════════════════════════

class NoiseGate:
    """Noise gate with attack / hold / release envelope.

    Signal below threshold → gain ramps to 0.
    Signal above threshold → gain ramps to 1, hold timer resets.
    """

    def __init__(self):
        self.threshold = -40.0   # dBFS  open threshold
        self.attack    =   2.0   # ms    gain-open speed
        self.hold      =  80.0   # ms    hold-open after signal drops
        self.release   = 150.0   # ms    gain-close speed
        self._env      =  0.0
        self._gain     =  0.0
        self._hold_rem =  0      # remaining hold samples

    def process(self, x: np.ndarray) -> np.ndarray:
        thr = 10.0 ** (self.threshold / 20.0)
        att = np.exp(-1.0 / max(SR * self.attack  / 1000.0, 1.0))
        rel = np.exp(-1.0 / max(SR * self.release / 1000.0, 1.0))
        N   = len(x)

        # Envelope: coef^N so block-rate matches time constant correctly
        rms       = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
        env_coef  = (att if rms > self._env else rel) ** N
        self._env = env_coef * self._env + (1.0 - env_coef) * rms

        hold_n = int(SR * self.hold / 1000.0)
        if self._env >= thr:
            self._hold_rem = hold_n
            target = 1.0
        elif self._hold_rem > 0:
            self._hold_rem = max(0, self._hold_rem - N)
            target = 1.0
        else:
            target = 0.0

        # Per-sample gain ramp: gain[i] = target + (gain0 - target) * coef^(i+1)
        # → smooth within block, no clicking, correct time constant
        coef       = att if target > self._gain else rel
        gain_arr   = target + (self._gain - target) * np.power(
                         coef, np.arange(1, N + 1, dtype=np.float64))
        self._gain = float(gain_arr[-1])
        return (x * gain_arr).astype(np.float32)


class SpeakingChain:
    """NoiseGate → HP → Low-shelf → Mid peak → High-shelf → DeEsser → Compressor → Gain"""

    def __init__(self):
        self.gate = NoiseGate()
        self.hp  = SOSFilter()
        self.ls  = SOSFilter()
        self.mid = SOSFilter()
        self.hs  = SOSFilter()
        self.des = DeEsser()
        self.cmp = Compressor()
        # Parameter defaults
        self.hp_fc    = 100.0
        self.ls_fc    = 200.0;  self.ls_gain  = -2.0
        self.mid_fc   = 3000.0; self.mid_gain =  3.0; self.mid_q = 2.0
        self.hs_fc    = 8000.0; self.hs_gain  =  2.0
        self.cmp.threshold = -20.0
        self.cmp.ratio     =  4.0
        self.cmp.attack    =  5.0
        self.cmp.release   = 80.0
        self.cmp.makeup    =  6.0
        self.gain_db = 0.0
        self._rebuild()

    def _rebuild(self):
        self.hp.highpass(self.hp_fc)
        self.ls.lowshelf(self.ls_fc, self.ls_gain)
        self.mid.peaking(self.mid_fc, self.mid_gain, self.mid_q)
        self.hs.highshelf(self.hs_fc, self.hs_gain)

    def process(self, x: np.ndarray) -> np.ndarray:
        x = self.gate.process(x)
        x = self.hp.process(x)
        x = self.ls.process(x)
        x = self.mid.process(x)
        x = self.hs.process(x)
        x = self.des.process(x)
        x = self.cmp.process(x)
        return (x * 10.0 ** (self.gain_db / 20.0)).astype(np.float32)


class SingingChain:
    """HP → Warmth → Presence → Air shelf → DeEsser → Compressor → Reverb → Gain"""

    def __init__(self):
        self.hp  = SOSFilter()
        self.wm  = SOSFilter()
        self.pr  = SOSFilter()
        self.air = SOSFilter()
        self.des = DeEsser()
        self.cmp = Compressor()
        self.rvb = Reverb()
        # Parameter defaults
        self.hp_fc    = 80.0
        self.wm_fc    = 250.0;  self.wm_gain  =  2.0; self.wm_q  = 1.0
        self.pr_fc    = 5000.0; self.pr_gain  =  2.5; self.pr_q  = 1.5
        self.air_fc   = 12000.0; self.air_gain =  3.0
        self.des.freq      = 7500.0
        self.des.threshold = -28.0
        self.des.reduction =  6.0
        self.cmp.threshold = -24.0
        self.cmp.ratio     =  2.0
        self.cmp.attack    = 20.0
        self.cmp.release   = 200.0
        self.cmp.makeup    =  4.0
        self.gain_db = 0.0
        self._rebuild()

    def _rebuild(self):
        self.hp.highpass(self.hp_fc)
        self.wm.peaking(self.wm_fc, self.wm_gain, self.wm_q)
        self.pr.peaking(self.pr_fc, self.pr_gain, self.pr_q)
        self.air.highshelf(self.air_fc, self.air_gain)

    def process(self, x: np.ndarray) -> np.ndarray:
        x = self.hp.process(x)
        x = self.wm.process(x)
        x = self.pr.process(x)
        x = self.air.process(x)
        x = self.des.process(x)
        x = self.cmp.process(x)
        x = self.rvb.process(x)
        return (x * 10.0 ** (self.gain_db / 20.0)).astype(np.float32)


# ══════════════════════════════════════════════════════════════════════════════
#  LOOPBACK CAPTURE  (WASAPI — captures output of any speaker/app)
# ══════════════════════════════════════════════════════════════════════════════

def _load_capture_dll():
    """Load MicToolCapture.dll (C++ WASAPI per-process capture).
    Returns the ctypes DLL object or None if not available."""
    dll_path = Path(__file__).parent / "MicToolCapture.dll"
    if not dll_path.exists():
        return None
    try:
        dll = ctypes.CDLL(str(dll_path))
        # MicTool_ListSessions(SessionEntry* out, int maxCount) -> int
        dll.MicTool_ListSessions.restype  = ctypes.c_int
        dll.MicTool_ListSessions.argtypes = [ctypes.c_void_p, ctypes.c_int]
        # MicTool_StartCapture(DWORD pid, int includeChildren) -> int
        dll.MicTool_StartCapture.restype  = ctypes.c_int
        dll.MicTool_StartCapture.argtypes = [ctypes.c_uint32, ctypes.c_int]
        # MicTool_ReadAudio(float* buf, int n) -> int
        dll.MicTool_ReadAudio.restype  = ctypes.c_int
        dll.MicTool_ReadAudio.argtypes = [ctypes.c_void_p, ctypes.c_int]
        # MicTool_GetSampleRate() -> UINT
        dll.MicTool_GetSampleRate.restype  = ctypes.c_uint
        dll.MicTool_GetSampleRate.argtypes = []
        # MicTool_StopCapture() -> void
        dll.MicTool_StopCapture.restype  = None
        dll.MicTool_StopCapture.argtypes = []
        # MicTool_ListWindowProcesses(WindowProcEntry* out, int maxCount) -> int
        # Enumerates all visible top-level windows (OBS approach) so users can
        # select Chrome/Firefox/Zen even before they start playing audio.
        dll.MicTool_ListWindowProcesses.restype  = ctypes.c_int
        dll.MicTool_ListWindowProcesses.argtypes = [ctypes.c_void_p, ctypes.c_int]
        return dll
    except Exception:
        return None


class _SessionEntry(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('pid',        ctypes.c_uint32),
        ('exe_name',   ctypes.c_wchar * 260),
        ('peak_level', ctypes.c_float),
    ]

class _WindowProcEntry(ctypes.Structure):
    _fields_ = [
        ('pid',      ctypes.c_uint32),
        ('exe_name', ctypes.c_wchar * 260),
    ]


class LoopbackCapture:
    """Per-process audio capture via MicToolCapture.dll (WASAPI process loopback).
    Falls back to soundcard device loopback if DLL is unavailable.

    list_sources() → [('process', pid, label), ('device', id, label), ...]
    start(kind, key)  — kind='process' or 'device'
    read(n)           → mono float32 array
    """

    def __init__(self):
        self.enabled = False
        self.gain    = 1.0
        self._dll    = _load_capture_dll()
        self._mode   = None          # 'process' | 'device' | None
        # device-loopback state (soundcard fallback)
        self._buf      = np.zeros(0, np.float32)
        self._lock     = threading.Lock()
        self._thread   = None
        self._stop_evt = threading.Event()
        # process-loopback: resample buffer
        self._proc_buf  = np.zeros(0, np.float32)
        self._proc_lock = threading.Lock()
        self._proc_thread = None
        self._proc_stop   = threading.Event()

    # ── public API ────────────────────────────────────────────────────────────

    def start(self, kind: str, key):
        """kind='process' (key=pid int) or 'device' (key=speaker_id str)."""
        self.stop()
        self._mode = kind
        if kind == 'process' and self._dll:
            ret = self._dll.MicTool_StartCapture(int(key), 1)
            if ret == 0:
                self._proc_stop.clear()
                self._proc_thread = threading.Thread(
                    target=self._drain_dll, daemon=True)
                self._proc_thread.start()
        elif kind == 'device':
            self._stop_evt.clear()
            self._thread = threading.Thread(
                target=self._run_device, args=(key,), daemon=True)
            self._thread.start()

    def stop(self):
        # Stop process capture
        self._proc_stop.set()
        if self._proc_thread and self._proc_thread.is_alive():
            self._proc_thread.join(timeout=1.0)
        self._proc_thread = None
        if self._dll:
            try: self._dll.MicTool_StopCapture()
            except Exception: pass
        with self._proc_lock:
            self._proc_buf = np.zeros(0, np.float32)
        # Stop device capture
        self._stop_evt.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        with self._lock:
            self._buf = np.zeros(0, np.float32)
        self._mode = None

    def read(self, n: int) -> np.ndarray:
        if self._mode == 'process':
            with self._proc_lock:
                avail = len(self._proc_buf)
                if avail >= n:
                    out = self._proc_buf[:n].copy()
                    self._proc_buf = self._proc_buf[n:]
                    return out * self.gain
        else:
            with self._lock:
                if len(self._buf) >= n:
                    out = self._buf[:n].copy()
                    self._buf = self._buf[n:]
                    return out * self.gain
        return np.zeros(n, np.float32)

    # ── process-loopback drain thread ─────────────────────────────────────────

    def _drain_dll(self):
        import math
        from scipy.signal import resample_poly
        tmp = (ctypes.c_float * BLOCK)()
        cap_sr = self._dll.MicTool_GetSampleRate() or SR
        while not self._proc_stop.is_set():
            got = self._dll.MicTool_ReadAudio(tmp, BLOCK)
            if got > 0:
                chunk = np.frombuffer(tmp, dtype=np.float32, count=got).copy()
                if cap_sr != SR:
                    g = math.gcd(int(SR), int(cap_sr))
                    chunk = resample_poly(
                        chunk, SR // g, cap_sr // g).astype(np.float32)
                with self._proc_lock:
                    self._proc_buf = np.concatenate([self._proc_buf, chunk])
                    if len(self._proc_buf) > SR * 2:
                        self._proc_buf = self._proc_buf[-SR * 2:]
            else:
                threading.Event().wait(0.005)

    # ── device-loopback thread (soundcard fallback) ────────────────────────────

    def _run_device(self, speaker_id: str):
        try:
            import soundcard as sc, math
            from scipy.signal import resample_poly
            with sc.get_microphone(speaker_id, include_loopback=True) as mic:
                cap_sr = getattr(mic, 'samplerate', SR)
                while not self._stop_evt.is_set():
                    data = mic.record(samplerate=cap_sr, numframes=BLOCK)
                    mono = (data.mean(axis=1) if data.ndim > 1
                            else data).astype(np.float32)
                    if cap_sr != SR:
                        g = math.gcd(int(SR), int(cap_sr))
                        mono = resample_poly(
                            mono, SR // g, cap_sr // g).astype(np.float32)
                    with self._lock:
                        self._buf = np.concatenate([self._buf, mono])
                        if len(self._buf) > SR * 2:
                            self._buf = self._buf[-SR * 2:]
        except Exception:
            pass

    # ── static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def list_sources() -> list[tuple[str, object, str]]:
        """Return [(kind, key, label), ...] sorted: per-app first, then devices.

        Uses two complementary strategies (same as OBS):
        1. MicTool_ListSessions  – processes with active audio sessions; shows
           real-time peak level and the root process PID (parent-chain resolved
           so Chrome/Firefox utility children map back to the browser).
        2. MicTool_ListWindowProcesses – all visible top-level windows; ensures
           Chrome / Zen appear even before they start playing audio, using the
           MAIN process PID so INCLUDE_TARGET_PROCESS_TREE covers all children.
        """
        sources = []
        dll = _load_capture_dll()
        if not dll:
            return sources

        # ── Step 1: audio sessions (with peak levels) ─────────────────────────
        sess_entries = (_SessionEntry * 64)()
        sess_count   = dll.MicTool_ListSessions(sess_entries, 64)
        # pid -> (name, peak)
        active: dict[int, tuple[str, float]] = {}
        for i in range(sess_count):
            pid  = sess_entries[i].pid
            name = sess_entries[i].exe_name or f"PID {pid}"
            peak = sess_entries[i].peak_level
            # Keep highest peak if same pid seen twice (shouldn't happen after
            # dedup in C++, but be safe)
            if pid not in active or peak > active[pid][1]:
                active[pid] = (name, peak)

        # ── Step 2: window processes (OBS-style — all visible apps) ───────────
        win_entries = (_WindowProcEntry * 256)()
        win_count   = dll.MicTool_ListWindowProcesses(win_entries, 256)
        # Build ordered list: active-session apps first (with peak indicator),
        # then window-only apps (no session yet), alphabetically.
        seen_pids: set[int] = set()

        # Active-session entries first
        for pid, (name, peak) in sorted(active.items(),
                                         key=lambda kv: kv[1][0].lower()):
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            bar = "[LOUD]" if peak > 0.02 else "[PLAY]"
            sources.append(('process', pid, f"{bar} {name}  (PID {pid})"))

        # Window-only entries (browser not yet playing audio, etc.)
        for i in range(win_count):
            pid  = win_entries[i].pid
            name = win_entries[i].exe_name or f"PID {pid}"
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            sources.append(('process', pid, f"[APP] {name}  (PID {pid})"))

        return sources


# ══════════════════════════════════════════════════════════════════════════════
#  AUDIO ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class AudioEngine:
    BYPASS = 0
    SPEAK  = 1
    SING   = 2

    def __init__(self):
        self.mode  = self.BYPASS
        self.speak = SpeakingChain()
        self.sing  = SingingChain()
        self.pitch  = PitchShifter()
        self.loopback = LoopbackCapture()
        self.soundboard = SoundboardMixer()
        self.stream     = None
        self.mon_stream = None
        self.monitor_vol = 0.8      # independent monitor volume (linear)
        self._mon_q: queue.Queue = queue.Queue(maxsize=6)
        self.peak   = 0.0   # updated each callback for VU meter

    def _cb(self, indata, outdata, frames, t, status):
        x = indata[:, 0].copy().astype(np.float32)
        # ── DSP chain (mic only) ──────────────────────────────────────────────
        if   self.mode == self.SPEAK: x = self.speak.process(x)
        elif self.mode == self.SING:  x = self.sing.process(x)
        x = self.pitch.process(x)
        x = np.clip(x, -1.0, 1.0)
        # ── Mix loopback AFTER DSP so app audio is never pitch-shifted/EQ'd ──
        if self.loopback.enabled:
            x = np.clip(x + self.loopback.read(len(x)), -1.0, 1.0)
        x = np.clip(x + self.soundboard.mix(len(x)), -1.0, 1.0)
        outdata[:, 0] = x
        if outdata.shape[1] == 2:
            outdata[:, 1] = x
        self.peak = float(np.max(np.abs(x)))
        # Feed monitor — non-blocking, drop if full (avoids latency build-up)
        try:
            self._mon_q.put_nowait(x.copy())
        except queue.Full:
            pass

    def _mon_cb(self, outdata, frames, t, status):
        try:
            x = self._mon_q.get_nowait()
        except queue.Empty:
            x = np.zeros(frames, dtype=np.float32)
        x = np.clip(x * self.monitor_vol, -1.0, 1.0)
        outdata[:, 0] = x
        if outdata.shape[1] == 2:
            outdata[:, 1] = x

    def start(self, in_dev: int, out_dev: int, mon_dev: int | None = None):
        self.stop()
        info  = sd.query_devices(out_dev)
        n_out = min(2, info['max_output_channels'])
        self.stream = sd.Stream(
            samplerate=SR, blocksize=BLOCK,
            device=(in_dev, out_dev),
            channels=(1, n_out),
            dtype='float32', latency='low',
            callback=self._cb,
        )
        self.stream.start()
        if mon_dev is not None:
            mon_info = sd.query_devices(mon_dev)
            n_mon = min(2, mon_info['max_output_channels'])
            self.mon_stream = sd.OutputStream(
                samplerate=SR, blocksize=BLOCK,
                device=mon_dev, channels=n_mon,
                dtype='float32', latency='low',
                callback=self._mon_cb,
            )
            self.mon_stream.start()

    def stop(self):
        self.loopback.stop()
        if self.mon_stream:
            try:
                self.mon_stream.stop()
                self.mon_stream.close()
            except Exception:
                pass
            self.mon_stream = None
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        # drain monitor queue
        while True:
            try:
                self._mon_q.get_nowait()
            except queue.Empty:
                break
        self.peak = 0.0

    @property
    def running(self) -> bool:
        return self.stream is not None and self.stream.active


# ══════════════════════════════════════════════════════════════════════════════
#  GUI — dark Catppuccin-Mocha palette
# ══════════════════════════════════════════════════════════════════════════════

BG   = "#1e1e2e"
BG2  = "#181825"
BG3  = "#313244"
FG   = "#cdd6f4"
SUB  = "#a6adc8"
BLUE = "#89b4fa"
GRN  = "#a6e3a1"
RED  = "#f38ba8"
YEL  = "#f9e2af"
MUTE = "#45475a"


class LabeledSlider(tk.Frame):
    """Compact [label ──slider── value] row."""

    def __init__(self, parent, label, from_: float, to: float,
                 default: float, fmt: str = "{:.1f}", unit: str = "",
                 cmd=None, length: int = 200, **kw):
        super().__init__(parent, bg=BG2, **kw)
        self.fmt  = fmt
        self.unit = unit
        self._cmd = cmd
        self.var  = tk.DoubleVar(value=default)

        if isinstance(label, tk.StringVar):
            tk.Label(self, textvariable=label, font=("Segoe UI", 9),
                     bg=BG2, fg=SUB, width=17, anchor='w').pack(side='left')
        else:
            tk.Label(self, text=label, font=("Segoe UI", 9),
                     bg=BG2, fg=SUB, width=17, anchor='w').pack(side='left')

        ttk.Scale(self, from_=from_, to=to, variable=self.var,
                  orient='horizontal', length=length).pack(side='left', padx=(2, 4))

        self._val_lbl = tk.Label(self, text=self._fmtv(default),
                                  font=("Consolas", 9), bg=BG2, fg=BLUE,
                                  width=10, anchor='e')
        self._val_lbl.pack(side='left')
        self.var.trace_add('write', self._on_change)

    def _fmtv(self, v: float) -> str:
        return self.fmt.format(v) + self.unit

    def _on_change(self, *_):
        v = self.var.get()
        self._val_lbl.config(text=self._fmtv(v))
        if self._cmd:
            self._cmd(v)

    def get(self) -> float:
        return self.var.get()

    def set(self, v: float):
        self.var.set(v)


class ScrollFrame(tk.Frame):
    """Vertically scrollable frame."""

    def __init__(self, parent, **kw):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill='both', expand=True)
        canvas = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        super().__init__(canvas, bg=BG, **kw)
        self._win = canvas.create_window((0, 0), window=self, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        self.bind('<Configure>', lambda e: canvas.configure(
            scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(
            self._win, width=e.width))
        canvas.bind_all('<MouseWheel>',
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))


# ──────────────────────────────────────────────────────────────────────────────

class MicToolApp(tk.Tk):

    def __init__(self):
        super().__init__()
        # Load language preference before building UI so t() returns correctly
        self._load_language_from_settings()
        self.title("MicTool  —  Real-time Mic Processor")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.geometry("560x820")
        self.engine = AudioEngine()
        # i18n live-update registries
        self._i18n_lframes: list = []   # list[tuple[tk.LabelFrame, str]]
        self._i18n_buttons: list = []   # list[tuple[tk.Button, str]]
        self._i18n_textboxes: list = [] # list[tuple[tk.Text, str]]
        self._nb_tab_info:  list = []   # list[tuple[tk.Frame, str, str]]
        self._nb: ttk.Notebook | None = None
        self._hotkey_bindings: dict[str, str] = {}
        self._hotkey_vars: dict[str, tk.StringVar] = {}
        self._hotkey_capture_dialog: tk.Toplevel | None = None
        self._hotkey_capture_action: str | None = None
        self._hotkey_event_q: queue.Queue = queue.Queue()
        self._hotkeys = GlobalHotkeyManager(self._hotkey_event_q.put_nowait)
        self._soundboard_items: list[dict[str, object]] = []
        self._soundboard_rows: list[tuple[tk.Widget, str]] = []
        self._soundboard_empty_lbl: tk.Label | None = None
        self._soundboard_list_frame: tk.Frame | None = None
        self._tray_icon_added = False
        self._tray_supported: bool | None = None
        self._tray_hwnd = None
        self._tray_icon_handle = None
        self._tray_wndproc = None
        self._tray_old_wndproc = None
        self._is_quitting = False
        self._hotkeys.start()
        self._apply_styles()
        self._build_ui()
        self._auto_load()     # restore last session
        self.update_idletasks()
        self._init_native_tray()
        self._vu_loop()
        self._hotkey_loop()
        self._soundboard_loop()
        self.bind('<Unmap>', self._on_window_unmap)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    @staticmethod
    def _load_language_from_settings():
        """Read the 'language' key from settings.json and set the global _LANG."""
        global _LANG
        if not SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
            lang = data.get('language', '')
            if lang in ('zh_tw', 'en', 'ja', 'ko'):
                _LANG = lang
        except Exception:
            pass

    # ── i18n helpers ──────────────────────────────────────────────────────────

    def _section(self, parent, key: str) -> tk.LabelFrame:
        """Create a LabelFrame section header, registered for live i18n updates."""
        lf = tk.LabelFrame(parent, text=f'  {t(key)}  ',
                           font=('Segoe UI', 9, 'bold'),
                           bg=BG2, fg=BLUE, bd=1, relief='groove', padx=6, pady=4)
        self._i18n_lframes.append((lf, key))
        return lf

    def _apply_lang_live(self):
        """Update all registered UI elements to the current language instantly."""
        # Update all StringVars
        for v, k in _I18N_VARS:
            v.set(t(k))
        # Update LabelFrames
        for lf, k in self._i18n_lframes:
            try:
                lf.config(text=f'  {t(k)}  ')
            except Exception:
                pass
        # Update buttons
        for btn, k in self._i18n_buttons:
            try:
                btn.config(text=t(k))
            except Exception:
                pass
        # Update read-only text boxes
        for box, k in self._i18n_textboxes:
            try:
                box.config(state='normal')
                box.delete('1.0', 'end')
                box.insert('1.0', t(k))
                box.config(state='disabled')
            except Exception:
                pass
        # Update notebook tabs
        if self._nb:
            for frame, icon, key in self._nb_tab_info:
                try:
                    self._nb.tab(frame, text=f'  {icon}  {t(key)}  ')
                except Exception:
                    pass
        if hasattr(self, '_voice_btns'):
            self._refresh_voice_btns()
        if hasattr(self, '_soundboard_items'):
            self._refresh_soundboard_ui()

    # ── Styles ────────────────────────────────────────────────────────────────

    def _apply_styles(self):
        s = ttk.Style(self)
        s.theme_use('clam')
        s.configure('.',             background=BG,  foreground=FG,
                    fieldbackground=BG3, troughcolor=BG3,
                    bordercolor=MUTE)
        s.configure('TScale',        background=BG2, troughcolor=BG3,
                    sliderlength=14)
        s.configure('TCombobox',     fieldbackground=BG3, foreground=FG,
                    selectbackground=BG3, selectforeground=FG)
        s.map('TCombobox',           fieldbackground=[('readonly', BG3)],
                                     foreground=[('readonly', FG)])
        s.configure('TNotebook',     background=BG,  bordercolor=MUTE, tabmargins=0)
        s.configure('TNotebook.Tab', background=BG3, foreground=SUB,
                    padding=[14, 6], font=('Segoe UI', 10, 'bold'))
        s.map('TNotebook.Tab',       background=[('selected', BG2)],
                                     foreground=[('selected', FG)])

    # ── Top-level layout ──────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_transport()
        self._build_vu()
        self._build_mode_bar()
        tk.Frame(self, bg=MUTE, height=1).pack(fill='x', pady=(4, 0))

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=0, pady=0)
        self._nb = nb

        speak_outer = tk.Frame(nb, bg=BG)
        sing_outer  = tk.Frame(nb, bg=BG)
        voice_outer = tk.Frame(nb, bg=BG)
        soundboard_outer = tk.Frame(nb, bg=BG)
        hotkey_outer = tk.Frame(nb, bg=BG)
        help_outer  = tk.Frame(nb, bg=BG)
        about_outer = tk.Frame(nb, bg=BG)
        nb.add(speak_outer, text=f"  🎤  {t('tab_speaking')}  ")
        nb.add(sing_outer,  text=f"  🎵  {t('tab_singing')}  ")
        nb.add(voice_outer, text=f"  🎙  {t('tab_voice')}  ")
        nb.add(soundboard_outer, text=f"  🔊  {t('tab_soundboard')}  ")
        nb.add(hotkey_outer, text=f"  ⌨  {t('tab_hotkeys')}  ")
        nb.add(help_outer,  text=f"  ❓  {t('tab_help')}  ")
        nb.add(about_outer, text=f"  ℹ  {t('tab_about')}  ")
        self._nb_tab_info = [
            (speak_outer, '🎤', 'tab_speaking'),
            (sing_outer,  '🎵', 'tab_singing'),
            (voice_outer, '🎙', 'tab_voice'),
            (soundboard_outer, '🔊', 'tab_soundboard'),
            (hotkey_outer, '⌨', 'tab_hotkeys'),
            (help_outer,  '❓', 'tab_help'),
            (about_outer, 'ℹ',  'tab_about'),
        ]

        speak_scroll = ScrollFrame(speak_outer)
        self._build_speak_panel(speak_scroll)

        sing_scroll = ScrollFrame(sing_outer)
        self._build_sing_panel(sing_scroll)

        voice_scroll = ScrollFrame(voice_outer)
        self._build_voice_panel(voice_scroll)

        soundboard_scroll = ScrollFrame(soundboard_outer)
        self._build_soundboard_panel(soundboard_scroll)

        hotkey_scroll = ScrollFrame(hotkey_outer)
        self._build_hotkeys_panel(hotkey_scroll)

        help_scroll = ScrollFrame(help_outer)
        self._build_help_panel(help_scroll)

        about_scroll = ScrollFrame(about_outer)
        self._build_about_panel(about_scroll)

    def _build_header(self):
        f = tk.Frame(self, bg=BG)
        f.pack(fill='x', padx=14, pady=(10, 4))
        tk.Label(f, text="MicTool", font=("Segoe UI", 15, "bold"),
                 bg=BG, fg=BLUE).pack(side='left')
        tk.Label(f, textvariable=_mkvar('hdr_tagline'),
                 font=("Segoe UI", 9), bg=BG, fg=SUB).pack(side='left')
        # Language selector button (right side)
        tk.Button(f, text="🌐", font=("Segoe UI", 11),
                  bg=BG, fg=SUB, activebackground=BG3,
                  bd=0, padx=4, pady=0, cursor='hand2',
                  command=self._open_lang_dialog).pack(side='right')

    def _open_lang_dialog(self):
        """Open a small dialog to pick the UI language (takes effect immediately)."""
        global _LANG
        dlg = tk.Toplevel(self)
        dlg.title(t('lang_dialog_title'))
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()

        tk.Label(dlg, text=t('lang_select_hint'),
                 font=("Segoe UI", 9), bg=BG, fg=SUB).pack(padx=20, pady=(14, 6))

        lang_var = tk.StringVar(value=_LANG)
        options = [
            ('zh_tw', '繁體中文'),
            ('en',    'English'),
            ('ja',    '日本語'),
            ('ko',    '한국어'),
        ]
        for code, label in options:
            tk.Radiobutton(dlg, text=label, variable=lang_var, value=code,
                           font=("Segoe UI", 10), bg=BG, fg=FG,
                           selectcolor=BG3, activebackground=BG,
                           activeforeground=FG).pack(anchor='w', padx=24, pady=2)

        def _apply():
            global _LANG
            chosen = lang_var.get()
            _LANG = chosen
            # Persist to settings
            data = {}
            if SETTINGS_FILE.exists():
                try:
                    data = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
                except Exception:
                    pass
            data['language'] = chosen
            try:
                SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
            except Exception:
                pass
            dlg.destroy()
            self._apply_lang_live()

        btn_f = tk.Frame(dlg, bg=BG)
        btn_f.pack(pady=(8, 14))
        tk.Button(btn_f, text=t('btn_ok'), font=("Segoe UI", 9, "bold"),
                  bg=BLUE, fg=BG, activebackground=BLUE,
                  bd=0, padx=20, pady=5, command=_apply).pack(side='left', padx=6)
        tk.Button(btn_f, text=t('btn_cancel'), font=("Segoe UI", 9),
                  bg=BG3, fg=FG, activebackground=BG3,
                  bd=0, padx=12, pady=5, command=dlg.destroy).pack(side='left', padx=6)

    def _build_transport(self):
        f = tk.Frame(self, bg=BG)
        f.pack(fill='x', padx=14, pady=4)

        devs      = sd.query_devices()
        in_names  = [f"{i}: {d['name']}" for i, d in enumerate(devs)
                     if d['max_input_channels'] > 0]
        out_names = [f"{i}: {d['name']}" for i, d in enumerate(devs)
                     if d['max_output_channels'] > 0]
        self._in_names  = in_names
        self._out_names = out_names

        def default_str(names, is_input):
            # Prefer VB-Audio Virtual Cable for output when available
            if not is_input:
                for n in names:
                    nl = n.lower()
                    if 'cable input' in nl or 'vb-audio' in nl:
                        return n
            try:
                idx = sd.default.device[0 if is_input else 1]
                pfx = f"{idx}:"
                for n in names:
                    if n.startswith(pfx):
                        return n
            except Exception:
                pass
            return names[0] if names else ""

        row1 = tk.Frame(f, bg=BG); row1.pack(fill='x', pady=2)
        tk.Label(row1, textvariable=_mkvar('lbl_input'), font=("Segoe UI", 9),
                 bg=BG, fg=SUB, width=7, anchor='w').pack(side='left')
        self.in_var = tk.StringVar(value=default_str(in_names, True))
        ttk.Combobox(row1, textvariable=self.in_var, values=in_names,
                     state='readonly', width=44).pack(side='left')
        self.in_var.trace_add('write', self._on_dev_change)

        row2 = tk.Frame(f, bg=BG); row2.pack(fill='x', pady=2)
        tk.Label(row2, textvariable=_mkvar('lbl_output'), font=("Segoe UI", 9),
                 bg=BG, fg=SUB, width=7, anchor='w').pack(side='left')
        self.out_var = tk.StringVar(value=default_str(out_names, False))
        out_cb = ttk.Combobox(row2, textvariable=self.out_var, values=out_names,
                              state='readonly', width=44)
        out_cb.pack(side='left')
        self.out_var.trace_add('write', self._on_dev_change)

        # Monitor row — independent listen-back output (does NOT affect OBS signal)
        mon_names = ["Off"] + out_names
        row_mon = tk.Frame(f, bg=BG); row_mon.pack(fill='x', pady=2)
        tk.Label(row_mon, textvariable=_mkvar('lbl_monitor'), font=("Segoe UI", 9),
                 bg=BG, fg=SUB, width=7, anchor='w').pack(side='left')
        self.mon_var = tk.StringVar(value=default_str(out_names, False))
        ttk.Combobox(row_mon, textvariable=self.mon_var, values=mon_names,
                     state='readonly', width=44).pack(side='left')
        self.mon_var.trace_add('write', self._on_dev_change)

        row_mvol = tk.Frame(f, bg=BG); row_mvol.pack(fill='x', pady=(0, 2))
        tk.Label(row_mvol, text="", bg=BG, fg=SUB, width=7).pack(side='left')
        tk.Label(row_mvol, textvariable=_mkvar('lbl_monitor_vol'), font=("Segoe UI", 9),
                 bg=BG, fg=SUB).pack(side='left')
        self._mon_vol_var = tk.DoubleVar(value=80.0)
        self._mon_vol_var.trace_add('write', self._mon_vol_chg)
        ttk.Scale(row_mvol, from_=0, to=400, variable=self._mon_vol_var,
                  orient='horizontal', length=180).pack(side='left', padx=(4, 4))
        self._mon_vol_lbl = tk.Label(row_mvol, text=" 80 %",
                                     font=("Consolas", 9), bg=BG, fg=BLUE, width=7)
        self._mon_vol_lbl.pack(side='left')

        # ── App Audio Loopback ────────────────────────────────────────────────
        sep = tk.Frame(f, bg=SUB, height=1); sep.pack(fill='x', pady=(6, 4))
        lb_hdr = tk.Frame(f, bg=BG); lb_hdr.pack(fill='x')
        tk.Label(lb_hdr, textvariable=_mkvar('lb_header'), font=("Segoe UI", 9, "bold"),
                 bg=BG, fg=FG).pack(side='left')
        tk.Label(lb_hdr, textvariable=_mkvar('lb_subtitle'),
                 font=("Segoe UI", 8), bg=BG, fg=MUTE).pack(side='left')

        # Source selector — per-app (DLL) + device loopback (soundcard)
        self._lb_sources: list[tuple[str, object, str]] = []  # (kind, key, label)

        row_lb = tk.Frame(f, bg=BG); row_lb.pack(fill='x', pady=2)
        tk.Label(row_lb, textvariable=_mkvar('lbl_source'), font=("Segoe UI", 9),
                 bg=BG, fg=SUB, width=7, anchor='w').pack(side='left')
        self._lb_var = tk.StringVar(value="Off")
        self._lb_cb  = ttk.Combobox(row_lb, textvariable=self._lb_var,
                                    values=["Off"], state='readonly', width=44)
        self._lb_cb.pack(side='left')
        self._lb_var.trace_add('write', self._on_lb_change)

        # Refresh button — re-enumerate running apps
        tk.Button(row_lb, text="↺", font=("Segoe UI", 9),
                  bg=BG2, fg=FG, bd=0, padx=4,
                  command=self._refresh_lb_sources).pack(side='left', padx=(4, 0))
        self._refresh_lb_sources()   # populate on startup

        # Loopback gain slider
        row_lbg = tk.Frame(f, bg=BG); row_lbg.pack(fill='x', pady=(0, 4))
        tk.Label(row_lbg, text="", bg=BG, fg=SUB, width=7).pack(side='left')
        tk.Label(row_lbg, textvariable=_mkvar('lbl_app_vol'), font=("Segoe UI", 9),
                 bg=BG, fg=SUB).pack(side='left')
        self._lb_gain_var = tk.DoubleVar(value=80.0)
        self._lb_gain_var.trace_add('write', self._on_lb_gain)
        ttk.Scale(row_lbg, from_=0, to=200, variable=self._lb_gain_var,
                  orient='horizontal', length=180).pack(side='left', padx=(4, 4))
        self._lb_gain_lbl = tk.Label(row_lbg, text=" 80 %",
                                     font=("Consolas", 9), bg=BG, fg=BLUE, width=7)
        self._lb_gain_lbl.pack(side='left')

        # VB-Audio Virtual Cable detection indicator
        vb_found = any('cable input' in n.lower() or 'vb-audio' in n.lower()
                       for n in out_names)
        if vb_found:
            vb_key, vb_color, vb_tip_key = 'vb_ok', GRN, 'vb_tip_ready'
        else:
            vb_key, vb_color, vb_tip_key = 'vb_missing', YEL, 'vb_tip_missing'
        self._vb_lbl_var = tk.StringVar(value=t(vb_key))
        _I18N_VARS.append((self._vb_lbl_var, vb_key))
        self._vb_lbl = tk.Label(row2, textvariable=self._vb_lbl_var,
                                font=("Segoe UI", 8), bg=BG, fg=vb_color)
        self._vb_lbl.pack(side='left', padx=6)
        self._vb_lbl.bind("<Button-1>", lambda e: messagebox.showinfo(
            t('vb_route_title'),
            tf('vb_route_steps', tip=t(vb_tip_key))))

        row3 = tk.Frame(f, bg=BG); row3.pack(fill='x', pady=(6, 2))
        self._btn_start = tk.Button(row3, text=t('btn_start'),
                                    font=("Segoe UI", 9, "bold"),
                                    bg=GRN, fg=BG, activebackground=GRN,
                                    bd=0, padx=12, pady=5,
                                    command=self._start)
        self._btn_start.pack(side='left', padx=(0, 6))
        self._i18n_buttons.append((self._btn_start, 'btn_start'))

        self._btn_stop  = tk.Button(row3, text=t('btn_stop'),
                                    font=("Segoe UI", 9, "bold"),
                                    bg=RED, fg=BG, activebackground=RED,
                                    bd=0, padx=12, pady=5,
                                    command=self._stop, state='disabled')
        self._btn_stop.pack(side='left', padx=(0, 14))
        self._i18n_buttons.append((self._btn_stop, 'btn_stop'))

        # Save / Load settings buttons
        _btn_save = tk.Button(row3, text=t('btn_save'),
                  font=("Segoe UI", 9), bg=BG3, fg=BLUE, activebackground=BG3,
                  bd=0, padx=10, pady=4,
                  command=self._save_settings)
        _btn_save.pack(side='left', padx=(0, 4))
        self._i18n_buttons.append((_btn_save, 'btn_save'))

        _btn_load = tk.Button(row3, text=t('btn_load'),
                  font=("Segoe UI", 9), bg=BG3, fg=BLUE, activebackground=BG3,
                  bd=0, padx=10, pady=4,
                  command=self._load_settings)
        _btn_load.pack(side='left', padx=(0, 10))
        self._i18n_buttons.append((_btn_load, 'btn_load'))
        self._status_lbl = tk.Label(row3, text="", font=("Segoe UI", 8),
                                    bg=BG, fg=SUB)
        self._status_lbl.pack(side='left')

    def _build_vu(self):
        f = tk.Frame(self, bg=BG)
        f.pack(fill='x', padx=14, pady=(2, 4))
        tk.Label(f, textvariable=_mkvar('lbl_level'), font=("Segoe UI", 9),
                 bg=BG, fg=SUB).pack(side='left')
        self._vu = tk.Canvas(f, width=320, height=14, bg=BG3,
                              bd=0, highlightthickness=0)
        self._vu.pack(side='left', padx=6)
        self._vu_bar = self._vu.create_rectangle(0, 0, 0, 14,
                                                  fill=GRN, outline='')
        self._vu_lbl = tk.Label(f, text="  -∞ dB",
                                 font=("Consolas", 9), bg=BG, fg=SUB, width=10)
        self._vu_lbl.pack(side='left')

    def _build_mode_bar(self):
        f = tk.Frame(self, bg=BG)
        f.pack(pady=6)
        tk.Label(f, textvariable=_mkvar('lbl_mode'), font=("Segoe UI", 10, "bold"),
                 bg=BG, fg=FG).pack(side='left', padx=(0, 10))
        specs = [
            (AudioEngine.BYPASS, 'btn_bypass',   MUTE),
            (AudioEngine.SPEAK,  'btn_speaking',  BLUE),
            (AudioEngine.SING,   'btn_singing',   YEL),
        ]
        self._mode_btns: dict[int, tk.Button] = {}
        for mode, label_key, color in specs:
            b = tk.Button(f, text=t(label_key),
                          font=("Segoe UI", 10, "bold"),
                          bg=BG3, fg=color, activebackground=BG3,
                          bd=0, padx=14, pady=6,
                          command=lambda m=mode: self._set_mode(m))
            b.pack(side='left', padx=4)
            self._mode_btns[mode] = b
            self._i18n_buttons.append((b, label_key))
        self._refresh_mode_btns()

    # ── Help panel ────────────────────────────────────────────────────────────

    def _build_help_panel(self, parent: tk.Frame):
        p = tk.Frame(parent, bg=BG, padx=12, pady=8)
        p.pack(fill='x')

        # ── Section 1: First-time Setup ───────────────────────────────────────
        s1 = self._section(p, 'help_setup_title')
        s1.pack(fill='x', pady=(0, 6))

        tk.Label(s1, textvariable=_mkvar('help_setup_body'),
                 font=("Segoe UI", 9), bg=BG2, fg=FG,
                 justify='left', anchor='w', wraplength=480).pack(
                     fill='x', padx=4, pady=(4, 2))

        url_lbl = tk.Label(s1,
                           text="🔗  https://vb-audio.com/Cable/",
                           font=("Segoe UI", 9, "underline"),
                           bg=BG2, fg=BLUE, cursor='hand2', anchor='w')
        url_lbl.pack(fill='x', padx=4, pady=(0, 6))
        url_lbl.bind("<Button-1>",
                     lambda e: webbrowser.open("https://vb-audio.com/Cable/"))

        # ── Section 2: Parameter Guide ─────────────────────────────────────────
        s2 = self._section(p, 'help_param_title')
        s2.pack(fill='x', pady=(0, 6))

        def _param_row(parent_frame, name: str, desc_key: str):
            """Render one 2-column row: bold parameter name | description."""
            row = tk.Frame(parent_frame, bg=BG2)
            row.pack(fill='x', pady=1)
            tk.Label(row, text=name, font=("Segoe UI", 9, "bold"),
                     bg=BG2, fg=BLUE, width=24, anchor='w').pack(side='left', padx=(4, 6))
            tk.Label(row, textvariable=_mkvar(desc_key), font=("Segoe UI", 9),
                     bg=BG2, fg=FG, anchor='w', wraplength=360,
                     justify='left').pack(side='left', fill='x', expand=True)

        params = [
            ("Noise Gate / Threshold", 'help_gate_thr'),
            ("Noise Gate / Attack",    'help_gate_att'),
            ("Noise Gate / Hold",      'help_gate_hld'),
            ("Noise Gate / Release",   'help_gate_rel'),
            ("High-Pass Filter / Cutoff", 'help_hp_cutoff'),
            ("Low Shelf EQ / Freq+Gain",  'help_ls_freq_gain'),
            ("Mid Peaking EQ / Freq+Gain+Q", 'help_mid_freq_gain_q'),
            ("High Shelf EQ / Freq+Gain",    'help_hs_freq_gain'),
            ("De-Esser / Freq",       'help_des_freq'),
            ("De-Esser / Threshold",  'help_des_thr'),
            ("De-Esser / Reduction",  'help_des_red'),
            ("Compressor / Threshold", 'help_cmp_thr'),
            ("Compressor / Ratio",     'help_cmp_ratio'),
            ("Compressor / Attack",    'help_cmp_att'),
            ("Compressor / Release",   'help_cmp_rel'),
            ("Compressor / Makeup",    'help_cmp_makeup'),
            ("Reverb / Wet Mix",    'help_rv_wet'),
            ("Reverb / Pre-delay",  'help_rv_pre'),
            ("Reverb / Decay",      'help_rv_decay'),
            ("App Loopback / Source",  'help_lb_source'),
            ("App Loopback / App Vol", 'help_lb_vol'),
        ]
        for name, desc in params:
            _param_row(s2, name, desc)

        # Divider before Voice Changer section
        tk.Frame(s2, bg=MUTE, height=1).pack(fill='x', padx=4, pady=(6, 4))

        tk.Label(s2, textvariable=_mkvar('help_vc_title'),
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=YEL,
                 anchor='w').pack(fill='x', padx=4, pady=(0, 2))

        vc_modes = [
            ("Off",       'help_vc_off'),
            ("Robot",     'help_vc_robot'),
            ("Chipmunk",  'help_vc_chipmunk'),
            ("Deep",      'help_vc_deep'),
            ("Female",    'help_vc_female'),
            ("Male",      'help_vc_male'),
            ("Custom",    'help_vc_custom'),
        ]
        for name, desc in vc_modes:
            _param_row(s2, f"  Voice / {name}", desc)

    # ── About panel ───────────────────────────────────────────────────────────

    def _build_about_panel(self, parent: tk.Frame):
        p = tk.Frame(parent, bg=BG, padx=20, pady=20)
        p.pack(fill='both', expand=True)

        # ── App name & tagline ────────────────────────────────────────────────
        tk.Label(p, text="MicTool",
                 font=("Segoe UI", 18, "bold"), bg=BG, fg=BLUE).pack(pady=(20, 2))
        tk.Label(p, textvariable=_mkvar('about_tagline'),
                 font=("Segoe UI", 10), bg=BG, fg=SUB).pack()

        tk.Frame(p, bg=MUTE, height=1).pack(fill='x', pady=(16, 12))

        # ── Author block ──────────────────────────────────────────────────────
        info_f = tk.Frame(p, bg=BG)
        info_f.pack()

        def _info_row(label_text, value_text: str,
                      value_fg=FG, bold=False, clickable_url: str = ''):
            row = tk.Frame(info_f, bg=BG)
            row.pack(pady=2)
            if isinstance(label_text, tk.StringVar):
                tk.Label(row, textvariable=label_text,
                         font=("Segoe UI", 9), bg=BG, fg=SUB,
                         width=12, anchor='e').pack(side='left', padx=(0, 6))
            else:
                tk.Label(row, text=label_text,
                         font=("Segoe UI", 9), bg=BG, fg=SUB,
                         width=12, anchor='e').pack(side='left', padx=(0, 6))
            font_spec = ("Segoe UI", 9, "bold") if bold else ("Segoe UI", 9)
            val_lbl = tk.Label(row, text=value_text,
                               font=font_spec, bg=BG, fg=value_fg)
            if clickable_url:
                val_lbl.config(cursor='hand2',
                               font=("Segoe UI", 9, "underline"))
                val_lbl.bind("<Button-1>", lambda e: webbrowser.open(clickable_url))
            val_lbl.pack(side='left')

        _info_row(_mkvar('about_author_label'), "結小語 Voidyuu", value_fg=FG, bold=True)
        _info_row(_mkvar('about_email_label'), "voidyuu0113@gmail.com",
                  value_fg=BLUE,
                  clickable_url="mailto:voidyuu0113@gmail.com")

        # X (Twitter) button
        x_f = tk.Frame(info_f, bg=BG)
        x_f.pack(pady=(6, 2))
        tk.Label(x_f, textvariable=_mkvar('about_twitter_label'),
                 font=("Segoe UI", 9), bg=BG, fg=SUB,
                 width=12, anchor='e').pack(side='left', padx=(0, 6))
        x_btn = tk.Button(
            x_f, text="𝕏  @void_yuu",
            font=("Segoe UI", 10, "bold"),
            bg="#000000", fg="#ffffff",
            activebackground="#222222", activeforeground="#ffffff",
            padx=16, pady=6, relief='flat', bd=0, cursor='hand2',
            command=lambda: webbrowser.open("https://x.com/void_yuu"),
        )
        x_btn.pack(side='left')

        tk.Frame(p, bg=MUTE, height=1).pack(fill='x', pady=(16, 12))

        # ── License / Terms block ─────────────────────────────────────────────
        lic_box = tk.Text(p,
                          font=("Segoe UI", 9),
                          bg=BG2, fg=FG, relief='flat',
                          padx=8, pady=8,
                          wrap='word', height=12,
                          state='normal',
                          bd=0, highlightthickness=0)
        lic_box.insert('1.0', t('about_license'))
        lic_box.config(state='disabled')
        lic_box.pack(fill='x', padx=4)
        self._i18n_textboxes.append((lic_box, 'about_license'))

        tk.Label(p, text="v1.0.0",
                 font=("Segoe UI", 8), bg=BG, fg=MUTE).pack(pady=(12, 4))

    # ── Speaking panel ────────────────────────────────────────────────────────

    def _build_speak_panel(self, parent: tk.Frame):
        sp = self.engine.speak
        p  = tk.Frame(parent, bg=BG, padx=10, pady=4)
        p.pack(fill='x')

        # Noise Gate
        s = self._section(p, 'sec_noise_gate'); s.pack(fill='x', pady=3)
        g = sp.gate
        self._sp_gate_thr = LabeledSlider(s, _mkvar('lbl_threshold'), -80,  0, g.threshold,
                                          "{:.1f}", " dB", self._sp_gate_chg)
        self._sp_gate_thr.pack(fill='x')
        self._sp_gate_att = LabeledSlider(s, _mkvar('lbl_attack'),   0.1, 20, g.attack,
                                          "{:.1f}", " ms", self._sp_gate_chg)
        self._sp_gate_att.pack(fill='x')
        self._sp_gate_hld = LabeledSlider(s, _mkvar('lbl_hold'),      10, 500, g.hold,
                                          "{:.0f}", " ms", self._sp_gate_chg)
        self._sp_gate_hld.pack(fill='x')
        self._sp_gate_rel = LabeledSlider(s, _mkvar('lbl_release'),   10, 500, g.release,
                                          "{:.0f}", " ms", self._sp_gate_chg)
        self._sp_gate_rel.pack(fill='x')

        # High-Pass
        s = self._section(p, 'sec_hp_filter'); s.pack(fill='x', pady=3)
        self._sp_hp = LabeledSlider(s, _mkvar('lbl_cutoff'), 20, 400, sp.hp_fc,
                                    "{:.0f}", " Hz", self._sp_hp_chg)
        self._sp_hp.pack(fill='x')

        # Low Shelf
        s = self._section(p, 'sec_low_shelf'); s.pack(fill='x', pady=3)
        self._sp_ls_fc   = LabeledSlider(s, _mkvar('lbl_freq'), 60, 600, sp.ls_fc,
                                         "{:.0f}", " Hz", self._sp_ls_chg)
        self._sp_ls_fc.pack(fill='x')
        self._sp_ls_gain = LabeledSlider(s, _mkvar('lbl_gain'), -12, 12, sp.ls_gain,
                                         "{:.1f}", " dB", self._sp_ls_chg)
        self._sp_ls_gain.pack(fill='x')

        # Mid Peak
        s = self._section(p, 'sec_mid_peak'); s.pack(fill='x', pady=3)
        self._sp_mid_fc   = LabeledSlider(s, _mkvar('lbl_freq'), 300, 8000, sp.mid_fc,
                                          "{:.0f}", " Hz", self._sp_mid_chg)
        self._sp_mid_fc.pack(fill='x')
        self._sp_mid_gain = LabeledSlider(s, _mkvar('lbl_gain'), -12, 12, sp.mid_gain,
                                          "{:.1f}", " dB", self._sp_mid_chg)
        self._sp_mid_gain.pack(fill='x')
        self._sp_mid_q    = LabeledSlider(s, _mkvar('lbl_q'), 0.3, 8, sp.mid_q,
                                          "{:.2f}", "", self._sp_mid_chg)
        self._sp_mid_q.pack(fill='x')

        # High Shelf
        s = self._section(p, 'sec_high_shelf'); s.pack(fill='x', pady=3)
        self._sp_hs_fc   = LabeledSlider(s, _mkvar('lbl_freq'), 2000, 18000, sp.hs_fc,
                                         "{:.0f}", " Hz", self._sp_hs_chg)
        self._sp_hs_fc.pack(fill='x')
        self._sp_hs_gain = LabeledSlider(s, _mkvar('lbl_gain'), -12, 12, sp.hs_gain,
                                         "{:.1f}", " dB", self._sp_hs_chg)
        self._sp_hs_gain.pack(fill='x')

        # De-esser
        s = self._section(p, 'sec_de_esser'); s.pack(fill='x', pady=3)
        d = sp.des
        self._sp_des_freq = LabeledSlider(s, _mkvar('lbl_freq'),      4000, 12000, d.freq,
                                          "{:.0f}", " Hz", self._sp_des_chg)
        self._sp_des_freq.pack(fill='x')
        self._sp_des_thr  = LabeledSlider(s, _mkvar('lbl_threshold'),  -60,     0, d.threshold,
                                          "{:.1f}", " dB", self._sp_des_chg)
        self._sp_des_thr.pack(fill='x')
        self._sp_des_red  = LabeledSlider(s, _mkvar('lbl_reduction'),    0,    24, d.reduction,
                                          "{:.1f}", " dB", self._sp_des_chg)
        self._sp_des_red.pack(fill='x')
        self._sp_des_att  = LabeledSlider(s, _mkvar('lbl_attack'),     0.1,    20, d.attack,
                                          "{:.1f}", " ms", self._sp_des_chg)
        self._sp_des_att.pack(fill='x')
        self._sp_des_rel  = LabeledSlider(s, _mkvar('lbl_release'),      5,   200, d.release,
                                          "{:.0f}", " ms", self._sp_des_chg)
        self._sp_des_rel.pack(fill='x')

        # Compressor
        s = self._section(p, 'sec_compressor'); s.pack(fill='x', pady=3)
        c = sp.cmp
        self._sp_thr = LabeledSlider(s, _mkvar('lbl_threshold'), -60,  0, c.threshold,
                                     "{:.1f}", " dB", self._sp_cmp_chg)
        self._sp_thr.pack(fill='x')
        self._sp_rat = LabeledSlider(s, _mkvar('lbl_ratio'),      1, 20, c.ratio,
                                     "{:.1f}", ":1",  self._sp_cmp_chg)
        self._sp_rat.pack(fill='x')
        self._sp_att = LabeledSlider(s, _mkvar('lbl_attack'),   0.1, 100, c.attack,
                                     "{:.1f}", " ms", self._sp_cmp_chg)
        self._sp_att.pack(fill='x')
        self._sp_rel = LabeledSlider(s, _mkvar('lbl_release'),    5, 500, c.release,
                                     "{:.0f}", " ms", self._sp_cmp_chg)
        self._sp_rel.pack(fill='x')
        self._sp_mkp = LabeledSlider(s, _mkvar('lbl_makeup'),   -6,  24, c.makeup,
                                     "{:.1f}", " dB", self._sp_cmp_chg)
        self._sp_mkp.pack(fill='x')

        # Output Gain
        s = self._section(p, 'sec_output_gain'); s.pack(fill='x', pady=3)
        self._sp_gain = LabeledSlider(s, _mkvar('lbl_gain'), -24, 24, sp.gain_db,
                                      "{:.1f}", " dB",
                                      lambda v: setattr(self.engine.speak, 'gain_db', v))
        self._sp_gain.pack(fill='x')

    # ── Singing panel ─────────────────────────────────────────────────────────

    def _build_sing_panel(self, parent: tk.Frame):
        sg = self.engine.sing
        p  = tk.Frame(parent, bg=BG, padx=10, pady=4)
        p.pack(fill='x')

        # High-Pass
        s = self._section(p, 'sec_hp_filter'); s.pack(fill='x', pady=3)
        self._sg_hp = LabeledSlider(s, _mkvar('lbl_cutoff'), 20, 300, sg.hp_fc,
                                    "{:.0f}", " Hz", self._sg_hp_chg)
        self._sg_hp.pack(fill='x')

        # Warmth
        s = self._section(p, 'sec_warmth'); s.pack(fill='x', pady=3)
        self._sg_wm_fc   = LabeledSlider(s, _mkvar('lbl_freq'), 80, 800, sg.wm_fc,
                                         "{:.0f}", " Hz", self._sg_wm_chg)
        self._sg_wm_fc.pack(fill='x')
        self._sg_wm_gain = LabeledSlider(s, _mkvar('lbl_gain'), -12, 12, sg.wm_gain,
                                         "{:.1f}", " dB", self._sg_wm_chg)
        self._sg_wm_gain.pack(fill='x')
        self._sg_wm_q    = LabeledSlider(s, _mkvar('lbl_q'), 0.3, 4, sg.wm_q,
                                         "{:.2f}", "", self._sg_wm_chg)
        self._sg_wm_q.pack(fill='x')

        # Presence
        s = self._section(p, 'sec_presence'); s.pack(fill='x', pady=3)
        self._sg_pr_fc   = LabeledSlider(s, _mkvar('lbl_freq'), 1000, 10000, sg.pr_fc,
                                         "{:.0f}", " Hz", self._sg_pr_chg)
        self._sg_pr_fc.pack(fill='x')
        self._sg_pr_gain = LabeledSlider(s, _mkvar('lbl_gain'), -12, 12, sg.pr_gain,
                                         "{:.1f}", " dB", self._sg_pr_chg)
        self._sg_pr_gain.pack(fill='x')
        self._sg_pr_q    = LabeledSlider(s, _mkvar('lbl_q'), 0.3, 4, sg.pr_q,
                                         "{:.2f}", "", self._sg_pr_chg)
        self._sg_pr_q.pack(fill='x')

        # Air
        s = self._section(p, 'sec_air'); s.pack(fill='x', pady=3)
        self._sg_air_fc   = LabeledSlider(s, _mkvar('lbl_freq'), 5000, 20000, sg.air_fc,
                                          "{:.0f}", " Hz", self._sg_air_chg)
        self._sg_air_fc.pack(fill='x')
        self._sg_air_gain = LabeledSlider(s, _mkvar('lbl_gain'), -12, 12, sg.air_gain,
                                          "{:.1f}", " dB", self._sg_air_chg)
        self._sg_air_gain.pack(fill='x')

        # De-esser
        s = self._section(p, 'sec_de_esser'); s.pack(fill='x', pady=3)
        d = sg.des
        self._sg_des_freq = LabeledSlider(s, _mkvar('lbl_freq'),      4000, 12000, d.freq,
                                          "{:.0f}", " Hz", self._sg_des_chg)
        self._sg_des_freq.pack(fill='x')
        self._sg_des_thr  = LabeledSlider(s, _mkvar('lbl_threshold'),  -60,     0, d.threshold,
                                          "{:.1f}", " dB", self._sg_des_chg)
        self._sg_des_thr.pack(fill='x')
        self._sg_des_red  = LabeledSlider(s, _mkvar('lbl_reduction'),    0,    24, d.reduction,
                                          "{:.1f}", " dB", self._sg_des_chg)
        self._sg_des_red.pack(fill='x')
        self._sg_des_att  = LabeledSlider(s, _mkvar('lbl_attack'),     0.1,    20, d.attack,
                                          "{:.1f}", " ms", self._sg_des_chg)
        self._sg_des_att.pack(fill='x')
        self._sg_des_rel  = LabeledSlider(s, _mkvar('lbl_release'),      5,   200, d.release,
                                          "{:.0f}", " ms", self._sg_des_chg)
        self._sg_des_rel.pack(fill='x')

        # Compressor
        s = self._section(p, 'sec_compressor'); s.pack(fill='x', pady=3)
        c = sg.cmp
        self._sg_thr = LabeledSlider(s, _mkvar('lbl_threshold'), -60,  0, c.threshold,
                                     "{:.1f}", " dB", self._sg_cmp_chg)
        self._sg_thr.pack(fill='x')
        self._sg_rat = LabeledSlider(s, _mkvar('lbl_ratio'),      1, 10, c.ratio,
                                     "{:.1f}", ":1",  self._sg_cmp_chg)
        self._sg_rat.pack(fill='x')
        self._sg_att = LabeledSlider(s, _mkvar('lbl_attack'),     1, 200, c.attack,
                                     "{:.1f}", " ms", self._sg_cmp_chg)
        self._sg_att.pack(fill='x')
        self._sg_rel = LabeledSlider(s, _mkvar('lbl_release'),   10, 1000, c.release,
                                     "{:.0f}", " ms", self._sg_cmp_chg)
        self._sg_rel.pack(fill='x')
        self._sg_mkp = LabeledSlider(s, _mkvar('lbl_makeup'),    -6,  24, c.makeup,
                                     "{:.1f}", " dB", self._sg_cmp_chg)
        self._sg_mkp.pack(fill='x')

        # Reverb  (Dattorro plate)
        s = self._section(p, 'sec_reverb'); s.pack(fill='x', pady=3)
        rv = sg.rvb
        self._sg_rv_wet   = LabeledSlider(s, _mkvar('lbl_wet_mix'),    0,    1,  rv.wet,
                                          "{:.2f}", "", self._sg_rv_simple_chg)
        self._sg_rv_wet.pack(fill='x')
        self._sg_rv_pre   = LabeledSlider(s, _mkvar('lbl_pre_delay'),  0,   80,  rv.pre_delay,
                                          "{:.0f}", " ms", self._sg_rv_rebuild_chg)
        self._sg_rv_pre.pack(fill='x')
        self._sg_rv_decay = LabeledSlider(s, _mkvar('lbl_decay'),      0, 0.95,  rv.decay,
                                          "{:.2f}", "", self._sg_rv_simple_chg)
        self._sg_rv_decay.pack(fill='x')
        self._sg_rv_bw    = LabeledSlider(s, _mkvar('lbl_brightness'), 0.5,  1,  rv.bandwidth,
                                          "{:.3f}", "", self._sg_rv_simple_chg)
        self._sg_rv_bw.pack(fill='x')
        self._sg_rv_damp  = LabeledSlider(s, _mkvar('lbl_damping'),    0,    1,  rv.damping,
                                          "{:.2f}", "", self._sg_rv_simple_chg)
        self._sg_rv_damp.pack(fill='x')
        self._sg_rv_mrate = LabeledSlider(s, _mkvar('lbl_mod_rate'), 0.1,    4,  rv.mod_rate,
                                          "{:.2f}", " Hz", self._sg_rv_mod_chg)
        self._sg_rv_mrate.pack(fill='x')
        self._sg_rv_mdep  = LabeledSlider(s, _mkvar('lbl_mod_depth'),  0,   32,  rv.mod_depth,
                                          "{:.1f}", " smp", self._sg_rv_mod_chg)
        self._sg_rv_mdep.pack(fill='x')

        # Output Gain
        s = self._section(p, 'sec_output_gain'); s.pack(fill='x', pady=3)
        self._sg_gain = LabeledSlider(s, _mkvar('lbl_gain'), -24, 24, sg.gain_db,
                                      "{:.1f}", " dB",
                                      lambda v: setattr(self.engine.sing, 'gain_db', v))
        self._sg_gain.pack(fill='x')

    # ── Voice changer panel ───────────────────────────────────────────────────

    def _build_voice_panel(self, parent: tk.Frame):
        p = tk.Frame(parent, bg=BG, padx=10, pady=8)
        p.pack(fill='x')

        # ── Mode buttons ──────────────────────────────────────────────────────
        s = self._section(p, 'sec_voice_mode'); s.pack(fill='x', pady=3)

        PINK = "#f5c2e7"
        mode_specs = [
            (PitchShifter.MODE_OFF,      'voice_btn_off',      MUTE),
            (PitchShifter.MODE_ROBOT,    'voice_btn_robot',    "#cba6f7"),
            (PitchShifter.MODE_CHIPMUNK, 'voice_btn_chipmunk', YEL),
            (PitchShifter.MODE_DEEP,     'voice_btn_deep',     RED),
            (PitchShifter.MODE_FEMALE,   'voice_btn_female',   PINK),
            (PitchShifter.MODE_MALE,     'voice_btn_male',     BLUE),
            (PitchShifter.MODE_CUSTOM,   'voice_btn_custom',   GRN),
        ]
        self._voice_btns: dict[int, tk.Button] = {}
        self._voice_btn_meta: dict[int, tuple[tk.Button, str, str]] = {}
        btn_frame = tk.Frame(s, bg=BG2); btn_frame.pack(fill='x', pady=(4, 2))
        for i, (mode, label_key, color) in enumerate(mode_specs):
            b = tk.Button(btn_frame, text=t(label_key),
                          font=("Segoe UI", 9, "bold"),
                          bg=BG3, fg=color, activebackground=BG3,
                          bd=0, padx=10, pady=5,
                          command=lambda m=mode: self._set_voice_mode(m))
            b.grid(row=i // 4, column=i % 4, padx=3, pady=3, sticky='ew')
            self._voice_btns[mode] = b
            self._voice_btn_meta[mode] = (b, label_key, color)
        for col in range(4):
            btn_frame.columnconfigure(col, weight=1)

        # Pitch hint label
        self._voice_hint = tk.Label(s, text="", font=("Segoe UI", 8),
                                    bg=BG2, fg=SUB)
        self._voice_hint.pack(anchor='w', padx=4, pady=(0, 4))

        # ── Robot settings ────────────────────────────────────────────────────
        s2 = self._section(p, 'sec_robot'); s2.pack(fill='x', pady=3)
        self._vc_robot_hz = LabeledSlider(s2, _mkvar('lbl_carrier'), 30, 300,
                                          self.engine.pitch.robot_hz,
                                          "{:.0f}", " Hz",
                                          self._vc_robot_chg)
        self._vc_robot_hz.pack(fill='x')

        # ── Custom pitch ──────────────────────────────────────────────────────
        s3 = self._section(p, 'sec_custom_pitch'); s3.pack(fill='x', pady=3)
        self._vc_custom_st = LabeledSlider(s3, _mkvar('lbl_semitones'), -12, 12,
                                           self.engine.pitch.custom_st,
                                           "{:+.1f}", " st",
                                           self._vc_custom_chg)
        self._vc_custom_st.pack(fill='x')

        # ── Gender fine-tune (Female / Male modes only) ───────────────────────
        s4 = self._section(p, 'sec_gender_tune'); s4.pack(fill='x', pady=3)
        self._vc_formant = LabeledSlider(s4, _mkvar('lbl_formant'), 0.60, 1.60,
                                         1.0, "{:.2f}", "×",
                                         self._vc_gender_chg)
        self._vc_formant.pack(fill='x')
        self._vc_gender_pitch = LabeledSlider(s4, _mkvar('lbl_pitch'), -6.0, 6.0,
                                              0.0, "{:+.1f}", " st",
                                              self._vc_gender_chg)
        self._vc_gender_pitch.pack(fill='x')
        tk.Label(s4, textvariable=_mkvar('vc_formant_hint'),
                 font=("Segoe UI", 8), bg=BG2, fg=MUTE).pack(anchor='w', padx=4, pady=(0, 4))

        self._refresh_voice_btns()

    def _build_soundboard_panel(self, parent: tk.Frame):
        p = tk.Frame(parent, bg=BG, padx=12, pady=8)
        p.pack(fill='x')

        tk.Label(p, textvariable=_mkvar('soundboard_intro'),
                 font=("Segoe UI", 9), bg=BG, fg=FG,
                 justify='left', anchor='w', wraplength=500).pack(fill='x', pady=(0, 2))
        tk.Label(p, textvariable=_mkvar('soundboard_intro2'),
                 font=("Segoe UI", 9), bg=BG, fg=SUB,
                 justify='left', anchor='w', wraplength=500).pack(fill='x', pady=(0, 8))

        row = tk.Frame(p, bg=BG)
        row.pack(fill='x', pady=(0, 8))
        btn_import = tk.Button(row, text=t('soundboard_import'),
                               font=("Segoe UI", 9, "bold"),
                               bg=BLUE, fg=BG, activebackground=BLUE,
                               bd=0, padx=12, pady=5,
                               command=self._import_soundboard_files)
        btn_import.pack(side='left', padx=(0, 6))
        self._i18n_buttons.append((btn_import, 'soundboard_import'))
        btn_clear = tk.Button(row, text=t('soundboard_clear'),
                              font=("Segoe UI", 9),
                              bg=BG3, fg=FG, activebackground=BG3,
                              bd=0, padx=10, pady=5,
                              command=self._clear_soundboard)
        btn_clear.pack(side='left')
        self._i18n_buttons.append((btn_clear, 'soundboard_clear'))

        s = self._section(p, 'soundboard_list_title')
        s.pack(fill='x', pady=(0, 6))
        self._soundboard_list_frame = tk.Frame(s, bg=BG2)
        self._soundboard_list_frame.pack(fill='x', padx=4, pady=(4, 6))
        self._soundboard_empty_lbl = tk.Label(
            self._soundboard_list_frame,
            text=t('soundboard_empty'),
            font=("Segoe UI", 9),
            bg=BG2, fg=SUB, anchor='w', justify='left',
        )
        self._soundboard_empty_lbl.pack(fill='x', pady=2)
        self._soundboard_rows.append((self._soundboard_empty_lbl, 'soundboard_empty'))

    def _refresh_soundboard_ui(self):
        if self._soundboard_list_frame is None:
            return
        for child in list(self._soundboard_list_frame.winfo_children()):
            child.destroy()
        self._soundboard_rows = []
        if not self._soundboard_items:
            self._soundboard_empty_lbl = tk.Label(
                self._soundboard_list_frame,
                text=t('soundboard_empty'),
                font=("Segoe UI", 9),
                bg=BG2, fg=SUB, anchor='w', justify='left',
            )
            self._soundboard_empty_lbl.pack(fill='x', pady=2)
            self._soundboard_rows.append((self._soundboard_empty_lbl, 'soundboard_empty'))
            return
        for item in self._soundboard_items:
            row = tk.Frame(self._soundboard_list_frame, bg=BG2)
            row.pack(fill='x', pady=2)
            top = tk.Frame(row, bg=BG2)
            top.pack(fill='x')
            text = f"{item['name']}  ({Path(item['path']).suffix.lower() or '.wav'})"
            tk.Label(top, text=text, font=("Segoe UI", 9),
                     bg=BG2, fg=FG, anchor='w').pack(side='left', fill='x', expand=True)
            btn_play = tk.Button(
                top, text=t('soundboard_pause') if self.engine.soundboard.is_playing(item['path']) else t('soundboard_play'),
                font=("Segoe UI", 8), bg=BG3, fg=BLUE, bd=0, padx=8, pady=4,
                command=lambda key=item['path']: self._toggle_soundboard_item(key),
            )
            btn_play.pack(side='left', padx=(6, 4))
            item['play_button'] = btn_play
            btn_remove = tk.Button(
                top, text=t('soundboard_remove'),
                font=("Segoe UI", 8), bg=BG3, fg=SUB, bd=0, padx=8, pady=4,
                command=lambda key=item['path']: self._remove_soundboard_item(key),
            )
            btn_remove.pack(side='left')

            volume_row = tk.Frame(row, bg=BG2)
            volume_row.pack(fill='x', pady=(4, 0))
            tk.Label(volume_row, text=t('soundboard_volume'),
                     font=("Segoe UI", 8), bg=BG2, fg=SUB, width=7, anchor='w').pack(side='left')
            var = tk.DoubleVar(value=float(item.get('volume', 100.0)))
            item['volume_var'] = var
            ttk.Scale(
                volume_row, from_=0, to=200, variable=var,
                orient='horizontal', length=220,
                command=lambda _value, key=item['path'], v=var: self._set_soundboard_volume(key, v.get()),
            ).pack(side='left', padx=(0, 6))
            lbl = tk.Label(volume_row, text=f"{var.get():.0f}%",
                           font=("Consolas", 8), bg=BG2, fg=BLUE, width=6)
            lbl.pack(side='left')
            item['volume_label'] = lbl

    def _add_soundboard_file(self, path: str, *, volume: float = 100.0, quiet: bool = False) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        if any(item['path'] == str(p) for item in self._soundboard_items):
            return False
        samples = SoundboardMixer.load_file(str(p))
        item = {
            'path': str(p),
            'name': p.stem,
            'samples': samples,
            'volume': max(0.0, min(200.0, float(volume))),
        }
        self._soundboard_items.append(item)
        self.engine.soundboard.add_clip(str(p), samples, item['volume'] / 100.0)
        self._refresh_soundboard_ui()
        if not quiet:
            self._status(t('status_sound_added'), BLUE)
        return True

    def _import_soundboard_files(self):
        if sf is None:
            messagebox.showerror(t('err_sound_load_title'), t('soundboard_missing_backend'))
            return
        paths = filedialog.askopenfilenames(
            title=t('soundboard_import_title'),
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.flac *.ogg *.aiff *.aif"),
                ("All Files", "*.*"),
            ],
        )
        added = 0
        for path in paths:
            try:
                if self._add_soundboard_file(path, quiet=True):
                    added += 1
            except Exception as exc:
                messagebox.showerror(t('err_sound_load_title'), f"{Path(path).name}\n\n{exc}")
                break
        if added:
            self._status(t('status_sound_added'), BLUE)

    def _toggle_soundboard_item(self, path: str):
        for item in self._soundboard_items:
            if item['path'] == path:
                playing = self.engine.soundboard.toggle(path)
                self._refresh_soundboard_ui()
                self._status(t('status_sound_played') if playing else t('status_sound_paused'), BLUE if playing else SUB)
                break

    def _set_soundboard_volume(self, path: str, volume: float):
        clamped = max(0.0, min(200.0, float(volume)))
        for item in self._soundboard_items:
            if item['path'] == path:
                item['volume'] = clamped
                label = item.get('volume_label')
                if label is not None:
                    label.config(text=f"{clamped:.0f}%")
                self.engine.soundboard.set_gain(path, clamped / 100.0)
                break

    def _soundboard_loop(self):
        if self._is_quitting:
            return
        for item in self._soundboard_items:
            btn = item.get('play_button')
            if btn is not None:
                try:
                    btn.config(text=t('soundboard_pause') if self.engine.soundboard.is_playing(item['path']) else t('soundboard_play'))
                except Exception:
                    pass
        self.after(200, self._soundboard_loop)

    def _remove_soundboard_item(self, path: str):
        self._soundboard_items = [item for item in self._soundboard_items if item['path'] != path]
        self.engine.soundboard.remove_clip(path)
        self._refresh_soundboard_ui()
        self._status(t('status_sound_removed'), SUB)

    def _clear_soundboard(self):
        self._soundboard_items.clear()
        self.engine.soundboard.clear()
        self._refresh_soundboard_ui()
        self._status(t('status_sound_cleared'), SUB)

    def _build_hotkeys_panel(self, parent: tk.Frame):
        p = tk.Frame(parent, bg=BG, padx=12, pady=8)
        p.pack(fill='x')

        tk.Label(p, textvariable=_mkvar('hotkeys_intro'),
                 font=("Segoe UI", 9), bg=BG, fg=FG,
                 justify='left', anchor='w', wraplength=500).pack(fill='x', pady=(0, 2))
        tk.Label(p, textvariable=_mkvar('hotkeys_intro2'),
                 font=("Segoe UI", 9), bg=BG, fg=SUB,
                 justify='left', anchor='w', wraplength=500).pack(fill='x', pady=(0, 8))

        if not self._hotkeys.available:
            tk.Label(p, textvariable=_mkvar('hotkeys_unavailable'),
                     font=("Segoe UI", 9, "bold"), bg=BG, fg=YEL,
                     justify='left', anchor='w', wraplength=500).pack(fill='x', pady=(0, 8))
            return

        s = self._section(p, 'hotkeys_bindings_title')
        s.pack(fill='x', pady=(0, 6))

        hdr = tk.Frame(s, bg=BG2)
        hdr.pack(fill='x', padx=4, pady=(2, 4))
        tk.Label(hdr, textvariable=_mkvar('hotkeys_col_action'),
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=BLUE,
                 width=22, anchor='w').pack(side='left')
        tk.Label(hdr, textvariable=_mkvar('hotkeys_col_binding'),
                 font=("Segoe UI", 9, "bold"), bg=BG2, fg=BLUE,
                 width=24, anchor='w').pack(side='left')

        for section_key, actions in HOTKEY_ACTIONS:
            tk.Label(s, textvariable=_mkvar(section_key),
                     font=("Segoe UI", 9, "bold"), bg=BG2, fg=YEL,
                     anchor='w').pack(fill='x', padx=4, pady=(6, 2))
            for action_id, label_key in actions:
                row = tk.Frame(s, bg=BG2)
                row.pack(fill='x', padx=4, pady=2)
                tk.Label(row, textvariable=_mkvar(label_key),
                         font=("Segoe UI", 9), bg=BG2, fg=FG,
                         width=22, anchor='w').pack(side='left')
                var = tk.StringVar(value=t('hotkeys_empty'))
                self._hotkey_vars[action_id] = var
                tk.Label(row, textvariable=var,
                         font=("Consolas", 9), bg=BG3, fg=FG,
                         width=24, anchor='w', padx=8, pady=4).pack(side='left', padx=(0, 6))
                btn_rec = tk.Button(row, text=t('hotkeys_record'),
                                    font=("Segoe UI", 8), bg=BG3, fg=BLUE,
                                    bd=0, padx=8, pady=4,
                                    command=lambda a=action_id: self._begin_hotkey_capture(a))
                btn_rec.pack(side='left', padx=(0, 4))
                self._i18n_buttons.append((btn_rec, 'hotkeys_record'))
                btn_clear = tk.Button(row, text=t('hotkeys_clear'),
                                      font=("Segoe UI", 8), bg=BG3, fg=SUB,
                                      bd=0, padx=8, pady=4,
                                      command=lambda a=action_id: self._clear_hotkey_binding(a))
                btn_clear.pack(side='left')
                self._i18n_buttons.append((btn_clear, 'hotkeys_clear'))

        self._refresh_hotkey_labels()

    def _set_voice_mode(self, mode: int):
        self.engine.pitch.mode = mode
        # Auto-load physiologically-based presets when switching to gender modes
        if hasattr(self, '_vc_formant'):
            if mode == PitchShifter.MODE_FEMALE:
                self._vc_formant.set(1.20)       # female vocal tract ~20% shorter
                self._vc_gender_pitch.set(3.0)   # female F0 typically higher
            elif mode == PitchShifter.MODE_MALE:
                self._vc_formant.set(0.83)       # male vocal tract ~20% longer
                self._vc_gender_pitch.set(-3.0)
            # Always sync engine state
            self._vc_gender_chg()
        self._refresh_voice_btns()

    def _refresh_voice_btns(self):
        cur = self.engine.pitch.mode
        hints = {
            PitchShifter.MODE_OFF:      t('voice_hint_off'),
            PitchShifter.MODE_ROBOT:    t('voice_hint_robot'),
            PitchShifter.MODE_CHIPMUNK: t('voice_hint_chipmunk'),
            PitchShifter.MODE_DEEP:     t('voice_hint_deep'),
            PitchShifter.MODE_FEMALE:   t('voice_hint_female'),
            PitchShifter.MODE_MALE:     t('voice_hint_male'),
            PitchShifter.MODE_CUSTOM:   tf('voice_hint_custom', value=self.engine.pitch.custom_st),
        }
        PINK = "#f5c2e7"
        colors = {
            PitchShifter.MODE_OFF: MUTE, PitchShifter.MODE_ROBOT: "#cba6f7",
            PitchShifter.MODE_CHIPMUNK: YEL, PitchShifter.MODE_DEEP: RED,
            PitchShifter.MODE_FEMALE: PINK, PitchShifter.MODE_MALE: BLUE,
            PitchShifter.MODE_CUSTOM: GRN,
        }
        for mode, btn in self._voice_btns.items():
            label_key = self._voice_btn_meta[mode][1]
            if mode == cur:
                btn.config(text=t(label_key), bg=colors[mode], fg=BG, relief='sunken')
            else:
                btn.config(text=t(label_key), bg=BG3, fg=colors[mode], relief='flat')
        if hasattr(self, '_voice_hint'):
            self._voice_hint.config(text=hints.get(cur, ""))

    def _vc_robot_chg(self, v=None):
        self.engine.pitch.robot_hz = self._vc_robot_hz.get()

    def _vc_custom_chg(self, v=None):
        self.engine.pitch.custom_st = self._vc_custom_st.get()
        if self.engine.pitch.mode == PitchShifter.MODE_CUSTOM:
            self._refresh_voice_btns()

    def _vc_gender_chg(self, v=None):
        fs = self.engine.pitch._fs
        fs.formant  = self._vc_formant.get()
        fs.pitch_st = self._vc_gender_pitch.get()

    def _refresh_hotkey_labels(self):
        for action_id, var in self._hotkey_vars.items():
            combo = self._hotkey_bindings.get(action_id, '')
            var.set(format_hotkey_combo(combo) if combo else t('hotkeys_empty'))

    def _begin_hotkey_capture(self, action_id: str):
        if not self._hotkeys.available:
            return
        self._cancel_hotkey_capture()
        self._hotkey_capture_action = action_id
        self._hotkeys.begin_capture()
        dlg = tk.Toplevel(self)
        dlg.title(t('hotkeys_record_title'))
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.grab_set()
        tk.Label(dlg, text=t('hotkeys_record_prompt'),
                 font=("Segoe UI", 9), bg=BG, fg=FG,
                 wraplength=340, justify='left').pack(padx=16, pady=(14, 10))
        btn = tk.Button(dlg, text=t('hotkeys_record_cancel'),
                        font=("Segoe UI", 9), bg=BG3, fg=FG,
                        bd=0, padx=14, pady=5,
                        command=self._cancel_hotkey_capture)
        btn.pack(pady=(0, 14))
        self._i18n_buttons.append((btn, 'hotkeys_record_cancel'))
        dlg.protocol("WM_DELETE_WINDOW", self._cancel_hotkey_capture)
        self._hotkey_capture_dialog = dlg

    def _cancel_hotkey_capture(self):
        self._hotkeys.cancel_capture()
        if self._hotkey_capture_dialog is not None:
            try:
                self._hotkey_capture_dialog.destroy()
            except Exception:
                pass
        self._hotkey_capture_dialog = None
        self._hotkey_capture_action = None

    def _finish_hotkey_capture(self, combo: str):
        action_id = self._hotkey_capture_action
        self._cancel_hotkey_capture()
        if not action_id:
            return
        self._set_hotkey_binding(action_id, combo)
        self._status(t('status_hotkey_saved'), BLUE)

    def _set_hotkey_binding(self, action_id: str, combo: str):
        normalized = '+'.join(_parse_hotkey_combo(combo))
        if normalized:
            self._hotkey_bindings[action_id] = normalized
        else:
            self._hotkey_bindings.pop(action_id, None)
        self._hotkeys.set_binding(action_id, normalized)
        self._refresh_hotkey_labels()

    def _clear_hotkey_binding(self, action_id: str):
        self._set_hotkey_binding(action_id, '')
        self._status(t('status_hotkey_saved'), BLUE)

    def _hotkey_loop(self):
        try:
            while True:
                kind, payload = self._hotkey_event_q.get_nowait()
                if kind == 'action':
                    self._run_hotkey_action(payload)
                elif kind == 'capture_done':
                    self._finish_hotkey_capture(payload)
        except queue.Empty:
            pass
        self.after(30, self._hotkey_loop)

    def _run_hotkey_action(self, action_id: str):
        actions = {
            'toggle_output': self._toggle_output_hotkey,
            'mode_speaking': lambda: self._set_mode(AudioEngine.SPEAK),
            'mode_singing': lambda: self._set_mode(AudioEngine.SING),
            'voice_off': lambda: self._set_voice_mode(PitchShifter.MODE_OFF),
            'voice_robot': lambda: self._set_voice_mode(PitchShifter.MODE_ROBOT),
            'voice_chipmunk': lambda: self._set_voice_mode(PitchShifter.MODE_CHIPMUNK),
            'voice_deep': lambda: self._set_voice_mode(PitchShifter.MODE_DEEP),
            'voice_female': lambda: self._set_voice_mode(PitchShifter.MODE_FEMALE),
            'voice_male': lambda: self._set_voice_mode(PitchShifter.MODE_MALE),
            'voice_custom': lambda: self._set_voice_mode(PitchShifter.MODE_CUSTOM),
        }
        fn = actions.get(action_id)
        if fn:
            self.after(0, fn)

    def _toggle_output_hotkey(self):
        if self.engine.running:
            self._stop()
        else:
            self._start()

    # ── Parameter callbacks — Speaking ────────────────────────────────────────

    def _sp_gate_chg(self, _=None):
        g = self.engine.speak.gate
        g.threshold = self._sp_gate_thr.get()
        g.attack    = self._sp_gate_att.get()
        g.hold      = self._sp_gate_hld.get()
        g.release   = self._sp_gate_rel.get()

    def _sp_hp_chg(self, _=None):
        sp = self.engine.speak
        sp.hp_fc = self._sp_hp.get()
        sp.hp.highpass(sp.hp_fc)

    def _sp_ls_chg(self, _=None):
        sp = self.engine.speak
        sp.ls_fc   = self._sp_ls_fc.get()
        sp.ls_gain = self._sp_ls_gain.get()
        sp.ls.lowshelf(sp.ls_fc, sp.ls_gain)

    def _sp_mid_chg(self, _=None):
        sp = self.engine.speak
        sp.mid_fc   = self._sp_mid_fc.get()
        sp.mid_gain = self._sp_mid_gain.get()
        sp.mid_q    = self._sp_mid_q.get()
        sp.mid.peaking(sp.mid_fc, sp.mid_gain, sp.mid_q)

    def _sp_hs_chg(self, _=None):
        sp = self.engine.speak
        sp.hs_fc   = self._sp_hs_fc.get()
        sp.hs_gain = self._sp_hs_gain.get()
        sp.hs.highshelf(sp.hs_fc, sp.hs_gain)

    def _sp_cmp_chg(self, _=None):
        c = self.engine.speak.cmp
        c.threshold = self._sp_thr.get()
        c.ratio     = self._sp_rat.get()
        c.attack    = self._sp_att.get()
        c.release   = self._sp_rel.get()
        c.makeup    = self._sp_mkp.get()

    def _sp_des_chg(self, _=None):
        d = self.engine.speak.des
        d.freq      = self._sp_des_freq.get()
        d.threshold = self._sp_des_thr.get()
        d.reduction = self._sp_des_red.get()
        d.attack    = self._sp_des_att.get()
        d.release   = self._sp_des_rel.get()
        d._rebuild()

    # ── Parameter callbacks — Singing ─────────────────────────────────────────

    def _sg_hp_chg(self, _=None):
        sg = self.engine.sing
        sg.hp_fc = self._sg_hp.get()
        sg.hp.highpass(sg.hp_fc)

    def _sg_wm_chg(self, _=None):
        sg = self.engine.sing
        sg.wm_fc   = self._sg_wm_fc.get()
        sg.wm_gain = self._sg_wm_gain.get()
        sg.wm_q    = self._sg_wm_q.get()
        sg.wm.peaking(sg.wm_fc, sg.wm_gain, sg.wm_q)

    def _sg_pr_chg(self, _=None):
        sg = self.engine.sing
        sg.pr_fc   = self._sg_pr_fc.get()
        sg.pr_gain = self._sg_pr_gain.get()
        sg.pr_q    = self._sg_pr_q.get()
        sg.pr.peaking(sg.pr_fc, sg.pr_gain, sg.pr_q)

    def _sg_air_chg(self, _=None):
        sg = self.engine.sing
        sg.air_fc   = self._sg_air_fc.get()
        sg.air_gain = self._sg_air_gain.get()
        sg.air.highshelf(sg.air_fc, sg.air_gain)

    def _sg_cmp_chg(self, _=None):
        c = self.engine.sing.cmp
        c.threshold = self._sg_thr.get()
        c.ratio     = self._sg_rat.get()
        c.attack    = self._sg_att.get()
        c.release   = self._sg_rel.get()
        c.makeup    = self._sg_mkp.get()

    def _sg_des_chg(self, _=None):
        d = self.engine.sing.des
        d.freq      = self._sg_des_freq.get()
        d.threshold = self._sg_des_thr.get()
        d.reduction = self._sg_des_red.get()
        d.attack    = self._sg_des_att.get()
        d.release   = self._sg_des_rel.get()
        d._rebuild()

    def _sg_rv_simple_chg(self, _=None):
        """Update params that take effect immediately (no buffer rebuild needed)."""
        rv          = self.engine.sing.rvb
        rv.wet      = self._sg_rv_wet.get()
        rv.decay    = self._sg_rv_decay.get()
        rv.bandwidth = self._sg_rv_bw.get()
        rv.damping  = self._sg_rv_damp.get()

    def _sg_rv_mod_chg(self, _=None):
        rv           = self.engine.sing.rvb
        rv.mod_rate  = self._sg_rv_mrate.get()
        rv.mod_depth = self._sg_rv_mdep.get()

    def _sg_rv_rebuild_chg(self, _=None):
        """Pre-delay change requires buffer resize — rebuild."""
        rv           = self.engine.sing.rvb
        rv.pre_delay = self._sg_rv_pre.get()
        rv.rebuild()

    # ── Transport ─────────────────────────────────────────────────────────────

    @staticmethod
    def _dev_idx(combo_str: str) -> int:
        return int(combo_str.split(':')[0])

    def _mon_vol_chg(self, *_):
        v = self._mon_vol_var.get()
        self._mon_vol_lbl.config(text=f"{v:.0f} %")
        self.engine.monitor_vol = v / 100.0

    def _start(self):
        try:
            in_dev  = self._dev_idx(self.in_var.get())
            out_dev = self._dev_idx(self.out_var.get())
            mon_str = self.mon_var.get()
            mon_dev = None if mon_str == "Off" else self._dev_idx(mon_str)
            self.engine.start(in_dev, out_dev, mon_dev)
            self._btn_start.config(state='disabled')
            self._btn_stop.config(state='normal')
        except Exception as exc:
            messagebox.showerror(t('err_start_title'), str(exc))

    def _stop(self):
        self.engine.stop()
        self._btn_start.config(state='normal')
        self._btn_stop.config(state='disabled')

    def _on_dev_change(self, *_):
        """Auto-restart stream when device selection changes while running."""
        if self.engine.stream is not None:
            self.after(50, self._start)   # defer 50ms so StringVar finishes writing

    def _refresh_lb_sources(self):
        """Re-enumerate running apps and devices, update the combobox."""
        self._lb_sources = LoopbackCapture.list_sources()
        labels = ["Off"] + [lbl for _, _, lbl in self._lb_sources]
        cur = self._lb_var.get()
        self._lb_cb.config(values=labels)
        if cur not in labels:
            self._lb_var.set("Off")

    def _on_lb_change(self, *_):
        label = self._lb_var.get()
        if label == "Off":
            self.engine.loopback.enabled = False
            self.engine.loopback.stop()
            return
        # Find matching source
        for kind, key, lbl in self._lb_sources:
            if lbl == label:
                self.engine.loopback.gain    = self._lb_gain_var.get() / 100.0
                self.engine.loopback.enabled = True
                self.engine.loopback.start(kind, key)
                return
        self.engine.loopback.enabled = False

    def _on_lb_gain(self, *_):
        v = self._lb_gain_var.get()
        self._lb_gain_lbl.config(text=f"{v:.0f} %")
        self.engine.loopback.gain = v / 100.0

    # ── Mode switching ────────────────────────────────────────────────────────

    def _set_mode(self, mode: int):
        self.engine.mode = mode
        self._refresh_mode_btns()

    def _refresh_mode_btns(self):
        hi = {AudioEngine.BYPASS: (MUTE, FG),
              AudioEngine.SPEAK:  (BLUE, BG),
              AudioEngine.SING:   (YEL,  BG)}
        for mode, btn in self._mode_btns.items():
            if mode == self.engine.mode:
                bg, fg = hi[mode]
                btn.config(bg=bg, fg=fg, relief='sunken')
            else:
                btn.config(bg=BG3, fg=hi[mode][0], relief='flat')

    # ── VU meter (50 ms refresh) ──────────────────────────────────────────────

    def _vu_loop(self):
        peak = self.engine.peak
        db   = 20.0 * np.log10(max(peak, 1e-9))
        w    = max(0, min(320, int((db + 60) / 60 * 320)))
        color = RED if db > -1 else YEL if db > -6 else GRN
        self._vu.coords(self._vu_bar, 0, 0, w, 14)
        self._vu.itemconfig(self._vu_bar, fill=color)
        self._vu_lbl.config(text=("  -∞ dB" if peak < 1e-4
                                  else f"  {db:+.1f} dB"))
        self.after(50, self._vu_loop)

    # ── Settings save / load ──────────────────────────────────────────────────

    def _collect_slider_values(self) -> dict:
        """Return {attr_name: value} for every LabeledSlider in this window."""
        return {
            name: obj.get()
            for name, obj in vars(self).items()
            if isinstance(obj, LabeledSlider)
        }

    def _save_settings(self):
        data = {
            "in_dev":      self.in_var.get(),
            "out_dev":     self.out_var.get(),
            "mon_dev":     self.mon_var.get(),
            "mon_vol":     self._mon_vol_var.get(),
            "mode":        self.engine.mode,
            "voice_mode":  self.engine.pitch.mode,
            "hotkeys":     self._hotkey_bindings,
            "soundboard_files": [
                {"path": item['path'], "volume": item.get('volume', 100.0)}
                for item in self._soundboard_items
            ],
            "sliders":     self._collect_slider_values(),
        }
        try:
            SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding='utf-8')
            self._status(t('status_saved'), GRN)
        except Exception as e:
            messagebox.showerror(t('err_save_title'), str(e))

    def _load_settings(self):
        if not SETTINGS_FILE.exists():
            messagebox.showinfo(t('load_title'), t('load_none_body'))
            return
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
            self._apply_settings(data)
            self._status(t('status_loaded'), BLUE)
        except Exception as e:
            messagebox.showerror(t('err_load_title'), str(e))

    def _auto_load(self):
        """Silent load on startup — no popup on failure."""
        if not SETTINGS_FILE.exists():
            return
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
            self._apply_settings(data)
        except Exception:
            pass

    def _apply_settings(self, data: dict):
        # Device dropdowns
        if data.get("in_dev") in self._in_names:
            self.in_var.set(data["in_dev"])
        if data.get("out_dev") in self._out_names:
            self.out_var.set(data["out_dev"])
        mon_choices = ["Off"] + self._out_names
        if data.get("mon_dev") in mon_choices:
            self.mon_var.set(data["mon_dev"])
        if "mon_vol" in data:
            self._mon_vol_var.set(float(data["mon_vol"]))
        # Mode buttons
        if "mode" in data:
            self._set_mode(int(data["mode"]))
        if "voice_mode" in data:
            self._set_voice_mode(int(data["voice_mode"]))
        for action_id, combo in data.get("hotkeys", {}).items():
            if action_id in self._hotkey_vars:
                self._set_hotkey_binding(action_id, combo)
        self._soundboard_items.clear()
        self.engine.soundboard.clear()
        for entry in data.get("soundboard_files", []):
            try:
                if isinstance(entry, str):
                    self._add_soundboard_file(entry, quiet=True)
                elif isinstance(entry, dict) and entry.get("path"):
                    self._add_soundboard_file(entry["path"], volume=entry.get("volume", 100.0), quiet=True)
            except Exception:
                pass
        self._refresh_soundboard_ui()
        # Sliders — setting each var fires the trace → updates the engine
        for name, val in data.get("sliders", {}).items():
            obj = getattr(self, name, None)
            if isinstance(obj, LabeledSlider):
                try:
                    obj.set(float(val))
                except Exception:
                    pass

    def _init_native_tray(self):
        if self._tray_supported is False:
            return
        user32 = ctypes.windll.user32
        if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_longlong):
            set_wndproc = user32.SetWindowLongPtrW
            get_wndproc = user32.GetWindowLongPtrW
        else:
            set_wndproc = user32.SetWindowLongW
            get_wndproc = user32.GetWindowLongW
        set_wndproc.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
        set_wndproc.restype = LONG_PTR
        get_wndproc.argtypes = [wintypes.HWND, ctypes.c_int]
        get_wndproc.restype = LONG_PTR
        call_wndproc = user32.CallWindowProcW
        call_wndproc.argtypes = [LONG_PTR, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        call_wndproc.restype = LRESULT
        hwnd = wintypes.HWND(self.winfo_id())
        self._tray_hwnd = hwnd
        user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_wchar_p]
        user32.LoadIconW.restype = wintypes.HICON
        self._tray_icon_handle = user32.LoadIconW(None, IDI_APPLICATION)
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

        def _window_proc(hWnd, msg, wParam, lParam):
            try:
                if msg == TRAY_CALLBACK_MSG:
                    if lParam == WM_LBUTTONUP:
                        self.after(0, self._restore_from_tray)
                        return 0
                    if lParam == WM_RBUTTONUP:
                        self.after(0, self._show_tray_menu)
                        return 0
                if self._tray_old_wndproc:
                    return call_wndproc(self._tray_old_wndproc, hWnd, msg, wParam, lParam)
            except Exception:
                return 0
            return 0

        try:
            self._tray_wndproc = WNDPROC(_window_proc)
            self._tray_old_wndproc = LONG_PTR(get_wndproc(hwnd, GWL_WNDPROC))
            set_wndproc(hwnd, GWL_WNDPROC, ctypes.cast(self._tray_wndproc, ctypes.c_void_p).value)
            self._tray_supported = True
        except Exception:
            self._tray_supported = False
            self._tray_wndproc = None
            self._tray_old_wndproc = None

    def _build_notify_icon_data(self) -> NOTIFYICONDATAW:
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self._tray_hwnd
        data.uID = 1
        data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        data.uCallbackMessage = TRAY_CALLBACK_MSG
        data.hIcon = self._tray_icon_handle
        data.szTip = "MicTool"
        return data

    def _show_tray_icon(self):
        if self._tray_supported is not True or self._tray_hwnd is None:
            return False
        if self._tray_icon_added:
            return True
        try:
            data = self._build_notify_icon_data()
            ok = ctypes.windll.shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(data))
            self._tray_icon_added = bool(ok)
            return self._tray_icon_added
        except Exception:
            self._tray_supported = False
            self._tray_icon_added = False
            return False

    def _stop_tray_icon(self):
        if self._tray_icon_added and self._tray_hwnd is not None:
            try:
                data = self._build_notify_icon_data()
                ctypes.windll.shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(data))
            except Exception:
                pass
        self._tray_icon_added = False

    def _show_tray_menu(self):
        if self._tray_hwnd is None:
            return
        menu = ctypes.windll.user32.CreatePopupMenu()
        if not menu:
            return
        try:
            ctypes.windll.user32.AppendMenuW(menu, MF_STRING, TRAY_CMD_RESTORE, t('tray_restore'))
            ctypes.windll.user32.AppendMenuW(menu, MF_STRING, TRAY_CMD_QUIT, t('tray_quit'))
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            ctypes.windll.user32.SetForegroundWindow(self._tray_hwnd)
            cmd = ctypes.windll.user32.TrackPopupMenu(
                menu,
                TPM_RETURNCMD | TPM_NONOTIFY,
                pt.x,
                pt.y,
                0,
                self._tray_hwnd,
                None,
            )
            if cmd == TRAY_CMD_RESTORE:
                self._restore_from_tray()
            elif cmd == TRAY_CMD_QUIT:
                self._quit_from_tray()
        finally:
            ctypes.windll.user32.DestroyMenu(menu)

    def _cleanup_native_tray(self):
        self._stop_tray_icon()
        if self._tray_hwnd is None or self._tray_old_wndproc is None:
            return
        try:
            user32 = ctypes.windll.user32
            if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_longlong):
                user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
                user32.SetWindowLongPtrW.restype = LONG_PTR
                user32.SetWindowLongPtrW(self._tray_hwnd, GWL_WNDPROC, self._tray_old_wndproc)
            else:
                user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, LONG_PTR]
                user32.SetWindowLongW.restype = LONG_PTR
                user32.SetWindowLongW(self._tray_hwnd, GWL_WNDPROC, self._tray_old_wndproc)
        except Exception:
            pass
        self._tray_old_wndproc = None
        self._tray_wndproc = None

    def _hide_to_tray(self):
        if self._is_quitting:
            return
        if not self._show_tray_icon():
            return
        self.withdraw()
        self._status(t('status_sent_to_tray'), BLUE)

    def _restore_from_tray(self):
        self.deiconify()
        self.state('normal')
        self.lift()
        self.focus_force()
        self._stop_tray_icon()

    def _quit_from_tray(self):
        self._on_close()

    def _on_window_unmap(self, _event=None):
        if self._is_quitting:
            return
        if self._tray_supported is False:
            return
        try:
            if self.state() == 'iconic':
                self.after(0, self._hide_to_tray)
        except Exception:
            pass

    def _status(self, msg: str, color: str = SUB):
        """Show a brief status message next to the Save button."""
        self._status_lbl.config(text=msg, fg=color)
        self.after(3000, lambda: self._status_lbl.config(text="", fg=SUB))

    def _on_close(self):
        if self._is_quitting:
            return
        self._is_quitting = True
        self._cancel_hotkey_capture()
        self._save_settings()   # auto-save on exit
        self._cleanup_native_tray()
        self._hotkeys.stop()
        self.engine.stop()
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys, traceback
    try:
        app = MicToolApp()
        app.mainloop()
    except Exception:
        log = Path(__file__).parent / "error.log"
        with open(log, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        try:
            import tkinter as _tk, tkinter.messagebox as _mb
            _r = _tk.Tk(); _r.withdraw()
            _mb.showerror("MicTool 啟動失敗",
                          f"錯誤已寫入：\n{log}\n\n{traceback.format_exc()[-600:]}")
            _r.destroy()
        except Exception:
            pass
        sys.exit(1)
