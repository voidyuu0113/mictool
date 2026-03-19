# MicTool

MicTool 是一套以 Python 製作的即時麥克風音訊處理工具，適合直播、語音聊天、錄音與唱歌使用。

目前這個分支是「非 AI 版本」，保留低延遲的即時 DSP 功能，不包含 RVC、Torch 或模型載入流程，啟動與打包都更輕量。

## 主要功能

- 即時麥克風處理，可直接輸出到實體音效卡或虛擬音效裝置
- `Speaking` 模式：適合說話與直播，提供高通、EQ、De-Esser、Compressor
- `Singing` 模式：適合唱歌，額外提供 Reverb 與較適合人聲的音色調整
- `Voice` 變聲模式：提供 Robot、Chipmunk、Deep、Female、Male、Custom
- App Audio Loopback，可把指定應用程式聲音混入輸出
- 內建多語系介面，包含繁體中文、English、日本語、한국어
- 可儲存與載入目前設定

## 適合用途

- OBS 直播收音
- Discord / 遊戲語音
- Podcast / 配音
- 線上歌唱或即時監聽

## 安裝需求

- Windows
- Python 3.12 左右版本
- 套件需求見 `requirements.txt`

安裝：

```bash
pip install -r requirements.txt
```

執行：

```bash
python mictool.py
```

## 打包

此專案已提供較快啟動的 `onedir` 打包腳本：

```bash
build_no_ai_exe.bat
```

輸出位置：

```text
dist/MicTool-NoAI/
```

主程式：

```text
dist/MicTool-NoAI/MicTool-NoAI.exe
```
