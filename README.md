# MicTool

[繁體中文](#繁體中文) | [English](#english) | [日本語](#日本語)

---

## 繁體中文

MicTool 是一款給 Windows 使用的即時麥克風音訊處理工具，適合直播、OBS、Discord、聊天台、歌回與日常語音用途。

如果你是第一次接觸這類工具，可以把它理解成一個把「麥克風處理、變聲、音效板、程式聲音混音、快捷鍵控制」集中在同一個介面裡的桌面工具。你可以先選麥克風和輸出裝置，再依照講話、唱歌或互動需求去套用模式與調整參數。

### 軟體特色

- 即時麥克風處理，可把處理後的聲音輸出到 OBS、Discord 或其他支援虛擬音訊裝置的軟體
- `Talk` 與 `Sing` 兩種主要處理用途，可依情境切換不同人聲鏈
- `Voice` 頁提供多種變聲模式，例如 `Robot`、`Chipmunk`、`Deep`、`Female`、`Male`、`Custom`
- 可選擇特定 Windows 程式做 `App Loopback`，把指定程式的聲音單獨混入輸出鏈
- `App Loopback` 在 Windows 桌面音訊工具裡相當少見，適合把伴奏、遊戲、播放器或瀏覽器音訊精準送進同一條處理與監聽流程
- `Soundboard` 音效板支援一次匯入多個音效檔、每個音效獨立音量、播放/暫停切換
- `Hotkeys` 頁支援全域快捷鍵，背景執行時也能用鍵盤或滑鼠按鍵觸發
- 支援最小化到 Windows 系統匣
- 支援多語系介面
- 內建 `Talk Auto Setup`，可分析幾秒講話內容後，自動給出較安全的 Talk 初始設定

### 功能頁面

#### 1. Live

- 上方固定全域控制列，可選擇 `Input / Output / Monitor`、啟動或停止處理、切換目前輸出模式
- `Talk Studio` 適合一般講話、直播聊天、語音會議
- `Sing Studio` 適合唱歌、歌回或需要較多空間感的使用情境
- 每個模式都有 preset 可快速套用，再往下微調細部參數
- `Talk Auto Setup` 可先按 `Analyze`，正常講幾句話後再按 `Apply Setup`

#### 2. Voice

- 快速切換不同變聲風格
- 提供 `Custom` 模式供自行微調

#### 3. Soundboard

- 支援一次匯入多個音效檔
- 每個音效都能獨立調整音量
- 播放鍵為播放/暫停切換，不會一直重疊播放
- 音效可混入主輸出，也可綁定快捷鍵

#### 4. Hotkeys

- 支援鍵盤與滑鼠按鍵綁定
- 支援組合鍵，例如 `Ctrl+M`
- 支援背景執行時觸發
- 可綁定音訊開關、說話/唱歌模式、變聲模式與音效板功能

#### 5. Settings

- 語言切換
- 說明與關於
- 路由與使用提示
- 系統相關設定

### 適合的使用情境

- OBS 直播
- Discord / 遊戲語音
- 線上會議
- Podcast / 語音錄製前級處理
- VTuber / 歌回 / 角色音互動

### 系統需求

- Windows
- Python 3.11 以上
- 音訊輸入與輸出裝置
- 若要把處理後聲音送進 OBS，建議搭配 VB-CABLE 或其他虛擬音訊裝置

### 直接下載

如果你只是想直接使用，不需要先安裝 Python。建議先從 GitHub Release 下載已打包版本：

1. 從 GitHub Release 下載 zip
2. 解壓縮整個 `MicTool-NoAI` 資料夾
3. 執行 `MicTool-NoAI.exe`
4. 請保留整個資料夾內容，不要只單獨拿出 `.exe`

### 安裝方式

安裝依賴：

```bash
pip install -r requirements.txt
```

執行程式：

```bash
python mictool.py
```

### 快速開始

#### 一般講話

1. 選擇麥克風 `Input`
2. 選擇主輸出 `Output`
3. 視需要選擇 `Monitor`
4. 切到 `Talk` 模式
5. 套用一組 Talk preset，或先做一次 `Auto Setup`
6. 按下 `Start`

#### 送進 OBS

1. 將 `Output` 設成虛擬音訊裝置，例如 VB-CABLE
2. 在 OBS 裡把麥克風來源設成同一個虛擬音訊裝置
3. 若需要自己監聽，可額外設定 `Monitor`

#### 使用 App Loopback

1. 到 `Settings` 頁面開啟 App Loopback 或相關設定區
2. 選擇你要混入的 Windows 程式
3. 確認該程式正在播放聲音
4. 啟動後，該程式音訊會和麥克風一起送進目前輸出鏈
5. 適合拿來混入伴奏、遊戲音效、播放器或瀏覽器聲音，而且不用把整個系統聲音全部一起送進去

#### 使用 Auto Setup

1. 到 `Live` 頁，切到 `Talk Studio`
2. 按 `Analyze`
3. 用平常講話的方式說幾秒
4. 看摘要結果
5. 按 `Apply Setup`
6. 若想回到分析前設定，可按 `Reset`

### 打包

這個專案目前主要使用資料夾版 `onedir` 發佈。

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

### 注意事項

- 第一次使用時，建議先確認 Windows 音訊裝置名稱與預設裝置狀態
- 如果 `Output` 和 `Monitor` 使用同一個實體裝置，仍建議實際測試你的裝置驅動表現
- `Hotkeys` 需要 `pynput`
- `Soundboard` 需要 `soundfile`
- 若系統匣無法建立，程式會退回一般最小化

### 作者

作者名稱保留原樣：`結小語 Voidyuu`

---

## English

MicTool is a real-time microphone processing tool for Windows, designed for live streaming, OBS, Discord, karaoke streams, and everyday voice use.

If this is your first time using a tool like this, think of MicTool as one desktop app that brings together microphone processing, voice modes, soundboard playback, per-app loopback mixing, hotkeys, and tray control. You start by choosing your input and output devices, then switch into the workflow that fits what you want to do.

### Highlights

- Real-time microphone processing for OBS, Discord, and other apps that can receive audio from a virtual device
- Two main vocal workflows: `Talk` and `Sing`
- `Voice` page with multiple voice styles such as `Robot`, `Chipmunk`, `Deep`, `Female`, `Male`, and `Custom`
- Select a specific Windows app for `App Loopback` and mix only that app's audio into your output chain
- Per-app loopback selection is still rare in Windows desktop audio tools, which makes it especially useful for routing backing tracks, game audio, players, or browser audio with more control
- `Soundboard` page with multi-file import, per-sound volume, and play/pause toggle
- `Hotkeys` page with global keyboard and mouse bindings that still work in the background
- Minimize-to-tray support on Windows
- Multilingual UI
- Built-in `Talk Auto Setup` to suggest safer starting values after a few seconds of speech

### Pages

#### 1. Live

- Fixed global control row for `Input / Output / Monitor`, start/stop, and output mode switching
- `Talk Studio` for regular speaking, livestreaming, and voice chat
- `Sing Studio` for singing and more spacious vocal processing
- Presets for quick setup, followed by manual fine tuning
- `Talk Auto Setup` with `Analyze` and `Apply Setup`

#### 2. Voice

- Quick switching between voice styles
- A `Custom` mode for manual adjustment

#### 3. Soundboard

- Import multiple sound files at once
- Independent volume control for each sound
- Play button works as play/pause toggle instead of endlessly stacking playback
- Sounds can be mixed into the main output and assigned to hotkeys

#### 4. Hotkeys

- Keyboard and mouse button bindings
- Multi-key combinations such as `Ctrl+M`
- Global hotkeys that work while the app is in the background
- Can be assigned to audio toggles, talk/sing modes, voice modes, and soundboard actions

#### 5. Settings

- Language switching
- Help and About
- Routing tips
- System-related options

### Common Use Cases

- OBS streaming
- Discord and in-game voice chat
- Online meetings
- Podcast or voice recording front-end processing
- VTuber, karaoke streams, and character voice interaction

### Requirements

- Windows
- Python 3.11+
- Audio input and output devices
- A virtual audio device such as VB-CABLE is recommended if you want to route the processed signal into OBS

### Download Ready-to-Use Build

If you just want to use MicTool right away, you do not need to install Python first. Start with the packaged release:

1. Download the zip from GitHub Releases
2. Extract the whole `MicTool-NoAI` folder
3. Run `MicTool-NoAI.exe`
4. Keep the full folder contents together instead of copying out only the `.exe`

### Installation

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python mictool.py
```

### Quick Start

#### Basic Talk Setup

1. Select your microphone in `Input`
2. Select your main destination in `Output`
3. Choose `Monitor` if needed
4. Switch to `Talk`
5. Apply a Talk preset or run `Auto Setup`
6. Press `Start`

#### Routing to OBS

1. Set `Output` to a virtual audio device such as VB-CABLE
2. In OBS, set the microphone source to that same virtual device
3. Optionally set `Monitor` if you want to hear yourself

#### Using App Loopback

1. Open the App Loopback or related routing area in `Settings`
2. Select the Windows app you want to mix in
3. Make sure that app is currently producing audio
4. Start processing and the selected app audio will be mixed into the active output chain
5. This is useful when you want to add backing tracks, game audio, media players, or browser audio without sending the entire system mix

#### Using Auto Setup

1. Open `Live` and switch to `Talk Studio`
2. Press `Analyze`
3. Speak naturally for a few seconds
4. Review the summary
5. Press `Apply Setup`
6. Press `Reset` if you want to return to the previous Talk settings

### Build

This project currently ships mainly as an `onedir` build.

```bash
build_no_ai_exe.bat
```

Output:

```text
dist/MicTool-NoAI/
```

Main executable:

```text
dist/MicTool-NoAI/MicTool-NoAI.exe
```

### Notes

- Check your Windows audio device names and default device state before first use
- If `Output` and `Monitor` use the same physical device, you should still test how your driver behaves
- `Hotkeys` requires `pynput`
- `Soundboard` requires `soundfile`
- If the tray icon cannot be created, the app falls back to normal minimization

### Author

Author name is intentionally kept as-is: `結小語 Voidyuu`

---

## 日本語

MicTool は、Windows 向けのリアルタイムマイク音声処理ツールです。配信、OBS、Discord、歌枠、日常の音声用途に向いています。

この種のツールを初めて使う場合は、MicTool を「マイク処理、ボイス切り替え、サウンドボード、アプリ単位のループバック、ホットキー、トレイ操作をひとつにまとめたデスクトップツール」と考えると分かりやすいです。最初に入力と出力を選び、その後で目的に合ったワークフローに切り替えて使います。

### 特徴

- OBS、Discord、仮想音声デバイス対応アプリ向けのリアルタイムマイク処理
- 主なボーカル用途として `Talk` と `Sing` を用意
- `Voice` ページで `Robot`、`Chipmunk`、`Deep`、`Female`、`Male`、`Custom` などの音声スタイルを切り替え可能
- 特定の Windows アプリを `App Loopback` として選び、そのアプリの音だけを出力チェーンにミックス可能
- アプリ単位で選べる loopback は Windows のデスクトップ音声ツールではかなり珍しく、伴奏、ゲーム音、プレイヤー、ブラウザ音声を細かく扱いたいときに便利
- `Soundboard` ページで複数ファイルの一括取り込み、音ごとの音量調整、再生/一時停止切り替えに対応
- `Hotkeys` ページで、バックグラウンドでも使えるグローバルなキーボード・マウス割り当てに対応
- Windows のトレイ最小化に対応
- 多言語 UI を搭載
- 数秒話すだけで Talk 用の安全な初期値を提案する `Talk Auto Setup` を搭載

### ページ構成

#### 1. Live

- `Input / Output / Monitor`、開始/停止、出力モード切り替えをまとめた固定コントロール列
- `Talk Studio` は通常会話、配信、ボイスチャット向け
- `Sing Studio` は歌唱や広がりのあるボーカル処理向け
- プリセットを先に適用し、その後で細かく調整可能
- `Talk Auto Setup` で `Analyze` と `Apply Setup` を使った初期設定が可能

#### 2. Voice

- ボイススタイルをすばやく切り替え
- `Custom` モードで手動微調整

#### 3. Soundboard

- 複数の音声ファイルをまとめて読み込み
- 各音ごとに独立した音量調整
- 再生ボタンは再生/一時停止の切り替え式で、重ねがけし続けない
- メイン出力へのミックスとホットキー割り当てに対応

#### 4. Hotkeys

- キーボードとマウスボタンの割り当て
- `Ctrl+M` のような複合キーに対応
- バックグラウンドでも動作するグローバルホットキー
- 音声オン/オフ、Talk/Sing 切り替え、ボイスモード、サウンドボード操作に割り当て可能

#### 5. Settings

- 言語切り替え
- Help / About
- ルーティングのヒント
- システム関連設定

### 主な用途

- OBS 配信
- Discord やゲーム音声チャット
- オンライン会議
- Podcast や音声収録前のフロント処理
- VTuber、歌枠、キャラクターボイス用途

### 動作要件

- Windows
- Python 3.11 以上
- 音声入力・出力デバイス
- 処理後の音声を OBS に送る場合は、VB-CABLE などの仮想音声デバイスを推奨

### すぐに使うには

すぐに使いたい場合は、最初に Python を入れる必要はありません。まずは GitHub Release のパッケージ版を使うのがおすすめです。

1. GitHub Releases から zip をダウンロード
2. `MicTool-NoAI` フォルダ全体を展開
3. `MicTool-NoAI.exe` を実行
4. `.exe` だけを取り出さず、フォルダごと保持する

### インストール

依存関係のインストール:

```bash
pip install -r requirements.txt
```

起動:

```bash
python mictool.py
```

### クイックスタート

#### 通常の話し声

1. `Input` でマイクを選択
2. `Output` で出力先を選択
3. 必要なら `Monitor` を設定
4. `Talk` モードに切り替え
5. Talk プリセットを適用するか `Auto Setup` を実行
6. `Start` を押す

#### OBS に送る場合

1. `Output` を VB-CABLE などの仮想音声デバイスに設定
2. OBS 側でその同じ仮想音声デバイスをマイク入力として設定
3. 自分で聞きたい場合は `Monitor` も設定

#### App Loopback の使い方

1. `Settings` 内の App Loopback または関連するルーティング設定を開く
2. ミックスしたい Windows アプリを選ぶ
3. そのアプリが実際に音を出していることを確認する
4. 開始すると、そのアプリの音声が現在の出力チェーンに加わる
5. システム全体の音ではなく、伴奏、ゲーム音、メディアプレイヤー、ブラウザ音声だけを送りたいときに便利

#### Auto Setup の使い方

1. `Live` を開き、`Talk Studio` に切り替える
2. `Analyze` を押す
3. 普段通りに数秒話す
4. 要約結果を確認する
5. `Apply Setup` を押す
6. 元の Talk 設定に戻したい場合は `Reset` を押す

### ビルド

現在は主に `onedir` 形式で配布しています。

```bash
build_no_ai_exe.bat
```

出力先:

```text
dist/MicTool-NoAI/
```

実行ファイル:

```text
dist/MicTool-NoAI/MicTool-NoAI.exe
```

### 注意

- 初回利用前に Windows の音声デバイス名と既定デバイス状態を確認してください
- `Output` と `Monitor` に同じ物理デバイスを使う場合は、ドライバの挙動を実機で確認してください
- `Hotkeys` には `pynput` が必要です
- `Soundboard` には `soundfile` が必要です
- トレイアイコンが作成できない環境では通常の最小化に戻ります

### 作者

作者名はそのまま維持しています: `結小語 Voidyuu`
