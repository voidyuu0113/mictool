# MicTool

MicTool 是一款給 Windows 使用的即時麥克風音訊處理工具，適合直播、OBS、Discord、聊天台、歌回與日常語音用途。

這個分支目前提供的是 `no-AI` 版本，主打低延遲的即時 DSP 處理流程，不包含 RVC、模型下載或 `torch` 類型的 AI 變聲依賴。你可以把它當成一個專注在「即時麥克風美化、變聲切換、音效板、快捷鍵、系統匣控制」的桌面工具。

## 軟體特色

- 即時麥克風處理，可把處理後的聲音輸出到 OBS、Discord 或其他支援虛擬音訊裝置的軟體
- `Talk` 與 `Sing` 兩種主要處理用途，可依情境切換不同人聲鏈
- `Voice` 頁提供多種變聲模式，例如 `Robot`、`Chipmunk`、`Deep`、`Female`、`Male`、`Custom`
- `Soundboard` 音效板支援一次匯入多個音效檔、每個音效獨立音量、播放/暫停切換
- `Hotkeys` 頁支援全域快捷鍵，背景執行時也能用鍵盤或滑鼠按鍵觸發
- 支援最小化到 Windows 系統匣
- 支援多語系介面
- 內建 `Talk Auto Setup`，可分析幾秒講話內容後，自動給出較安全的 Talk 初始設定

## 功能簡介

### 1. Live

`Live` 是主要工作區，整合了平常最常用的聲音調整功能。

- 上方固定全域控制列，可選擇 `Input / Output / Monitor`、啟動或停止處理、切換目前輸出模式
- `Talk Studio` 適合一般講話、直播聊天、語音會議
- `Sing Studio` 適合唱歌、歌回或需要較多空間感的使用情境
- 每個模式都有 preset 可快速套用，再往下微調細部參數
- `Talk Auto Setup` 可先按 `Analyze`，正常講幾句話後再按 `Apply Setup`，快速建立一組安全起始值

### 2. Voice

`Voice` 頁負責變聲功能。

- 可快速切換不同變聲風格
- 保留一組 `Custom` 模式供你自己微調
- 適合角色音、效果音或直播互動用途

### 3. Soundboard

`Soundboard` 頁提供音效板功能。

- 支援一次匯入多個音效檔
- 每個音效都能獨立調整音量
- 按下播放後再次按同一顆會切成暫停，不會一直重疊播放
- 音效會混入目前主輸出
- 音效也能綁定全域快捷鍵

### 4. Hotkeys

`Hotkeys` 頁用來設定全域快捷鍵。

- 支援鍵盤與滑鼠按鍵綁定
- 支援組合鍵，例如 `Ctrl+M`
- 支援背景執行時觸發
- 可綁定音訊開關、說話/唱歌模式切換、變聲模式切換，以及音效板按鍵

### 5. Settings

`Settings` 頁集中放置系統相關功能。

- 語言切換
- 說明與關於
- 路由與使用提示
- 其他不需要常駐在主頁的系統設定

## 適合的使用情境

- OBS 直播
- Discord / 遊戲語音
- 線上會議
- Podcast / 語音錄製前級處理
- VTuber / 歌回 / 角色音互動

## 系統需求

- Windows
- Python 3.11 以上
- 音訊輸入與輸出裝置
- 如果要把處理後的聲音送進 OBS，建議搭配 VB-CABLE 或其他虛擬音訊裝置

## 安裝方式

安裝依賴：

```bash
pip install -r requirements.txt
```

執行程式：

```bash
python mictool.py
```

## 快速開始

### 一般講話

1. 選擇麥克風 `Input`
2. 選擇主輸出 `Output`
3. 視需要選擇 `Monitor`
4. 切到 `Talk` 模式
5. 套用一組 Talk preset，或先做一次 `Auto Setup`
6. 按下 `Start`

### 送進 OBS

1. 將 `Output` 設成虛擬音訊裝置，例如 VB-CABLE
2. 在 OBS 裡把麥克風來源設成同一個虛擬音訊裝置
3. 若你需要自己監聽，可額外設定 `Monitor`

### 使用 Auto Setup

1. 到 `Live` 頁，切到 `Talk Studio`
2. 按 `Analyze`
3. 用平常講話的方式說幾秒
4. 看摘要結果
5. 按 `Apply Setup`
6. 如果想回到分析前設定，可按 `Reset`

## 打包

這個專案目前主要使用資料夾版 `onedir` 發佈。

執行：

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

## Release 使用方式

如果你是從 GitHub Release 下載：

1. 下載 zip
2. 解壓縮整個 `MicTool-NoAI` 資料夾
3. 執行 `MicTool-NoAI.exe`
4. 不要只單獨拿出 `.exe`，請保留整個資料夾內容

## 注意事項

- 第一次使用時，建議先確認 Windows 音訊裝置名稱與預設裝置狀態
- 如果 `Output` 和 `Monitor` 使用同一個實體裝置，程式會盡量用較穩定的方式處理，但仍建議實際測試你的裝置驅動表現
- `Hotkeys` 需要 `pynput`
- `Soundboard` 需要 `soundfile`
- 若系統匣無法建立，程式會退回一般最小化

## 授權與作者

作者名稱保留原樣：`結小語 Voidyuu`
