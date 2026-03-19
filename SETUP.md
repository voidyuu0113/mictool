# MicTool — 安裝與使用說明

## 安裝環境

```bash
pip install sounddevice numpy scipy
```

## 啟動

```bash
python mictool.py
```

## OBS 輸出設定（Windows）

1. 下載並安裝 **VB-Audio Virtual Cable**（免費）
   https://vb-audio.com/Cable/
2. 在 MicTool 的 **Output** 下拉選單選 `CABLE Input (VB-Audio Virtual Cable)`
3. 在 OBS → 音效來源 → 加入 **音訊輸入擷取** → 選 `CABLE Output (VB-Audio Virtual Cable)`
4. 按下 **▶ Start** 即開始即時處理

## 使用說明

| 按鈕 | 說明 |
|------|------|
| ⊘ Bypass | 直通原始麥克風，用於效果對比 |
| 🎤 Speaking | 說話模式：高通 + EQ + 壓縮，無殘響，清晰明亮 |
| 🎵 Singing | 唱歌模式：音色優化 EQ + 動態壓縮 + Reverb |

## 參數說明

### 說話模式
| 區塊 | 參數 | 說明 |
|------|------|------|
| High-Pass Filter | Cutoff | 截掉低頻雜音（建議 80–120 Hz） |
| Low Shelf EQ | Freq / Gain | 調整低頻豐滿度 |
| Mid Peaking EQ | Freq / Gain / Q | 強化語音清晰感（中頻 2–4kHz） |
| High Shelf EQ | Freq / Gain | 調整亮度與空氣感 |
| Compressor | Threshold / Ratio / Attack / Release / Makeup | 動態控制，讓音量穩定 |

### 唱歌模式
| 區塊 | 參數 | 說明 |
|------|------|------|
| High-Pass Filter | Cutoff | 截掉低頻噪音 |
| Warmth | Freq / Gain / Q | 低中頻溫暖感（200–400 Hz） |
| Presence | Freq / Gain / Q | 中高頻存在感（4–6 kHz） |
| Air | Freq / Gain | 高頻空氣感（12k+ Hz） |
| Compressor | 同上 | 輕度壓縮，保留動態 |
| Reverb | Wet Mix / Room Size / Damping / Pre-delay | 自然殘響效果 |

## 音頻延遲

預設 BLOCK=512，約 **12ms** 延遲（需戴耳機監聽）。
如出現雜音/爆音，可把 `mictool.py` 第一行常數改為：
```python
BLOCK = 1024   # 約 23ms，更穩定
```
