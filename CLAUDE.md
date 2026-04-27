# XAUUSD Trading Strategy Analysis Toolkit — CLAUDE.md

## 專案目的

分析 XAUUSD（黃金/美元）Long-Only 交易策略的失敗模式，並系統性地測試新策略（多單 + 空單）。
包含三大模組：

1. **Fail-Pattern Analysis** — 分析現有策略的虧損交易，找出失敗根因（含 DXY 相關性）
2. **Long Experiment Engine** — 回測 20 個多單策略，自動生成 TradingView Pine Script
3. **Short Experiment Engine** — 回測 20 個空單策略，自動生成 TradingView Pine Script

---

## 執行方式

```bash
# Windows 環境（Python 3.11）
py -3.11 main.py                    # 分析所有 3 個既有策略
py -3.11 main.py S1-AweWithBB       # 只分析單一策略
py -3.11 main.py S2-Hybrid
py -3.11 main.py S2-Pullback

py -3.11 run_experiments.py         # 執行 20 多單策略實驗
py -3.11 run_short_experiments.py   # 執行 20 空單策略實驗
```

---

## 目錄結構

```
xauusd/
├── analysis/               # Fail-pattern 分析套件
│   ├── config.py           # 3 個策略設定 + 失敗分類門檻 + CSV 路徑
│   ├── loader.py           # TradingView CSV → 正規化 DataFrame（load_price / load_dxy）
│   ├── metrics.py          # 統計指標（win_rate, profit_factor, drawdown）
│   ├── fail_patterns.py    # 虧損分類邏輯（核心）
│   ├── pre_entry.py        # 進場前情境分析（交易資料 + K 棒 RSI 特徵）
│   ├── dxy_analysis.py     # DXY 相關性分析
│   ├── charts.py           # matplotlib 圖表（含 DXY 圖）
│   └── report.py           # 自含式 HTML 報告生成器（含 DXY 段落）
│
├── experiments/            # 策略回測引擎（多單 + 空單共用）
│   ├── engine.py           # run_backtest()（多單）+ run_backtest_short()（空單）
│   ├── indicators.py       # 11 個技術指標（含 donchian_low）
│   ├── strategies.py       # 20 個多單策略信號（E01–E20）
│   ├── strategies_short.py # 20 個空單策略信號（S01–S20）
│   ├── runner.py           # 執行所有策略 + 複合評分
│   ├── pine_generator.py   # 自動生成 20 個多單 Pine Script v6
│   ├── pine_generator_short.py # 自動生成 20 個空單 Pine Script v6
│   └── report.py           # HTML 實驗結果儀表板（多空共用）
│
├── csv/                    # 所有 TradingView 匯出資料（統一放這裡）
│   ├── FX_IDC_XAUUSD, 30.csv    # 30m K 棒 2026-01-21 起（3058 根）
│   ├── FX_IDC_XAUUSD, 60.csv    # 60m K 棒 2025-10-15 起
│   ├── FX_IDC_XAUUSD, 240.csv   # 4H K 棒 2024-05-01 起
│   ├── FX_IDC_XAUUSD, 1D.csv    # 日線 2014-03-03 起（3058 根）
│   ├── FX_IDC_XAUUSD, 1W.csv    # 週線
│   ├── TVC_DXY, 30.csv          # DXY 30m 2026-01-22 起
│   ├── TVC_DXY, 60.csv          # DXY 60m
│   ├── TVC_DXY, 240.csv         # DXY 4H
│   ├── TVC_DXY, 1D.csv          # DXY 日線 2014-03-10 起（3078 根）
│   └── TVC_DXY, 1W.csv          # DXY 週線
│
├── main.py                 # Fail-pattern 分析入口
├── run_experiments.py      # 多單 20 策略實驗入口
├── run_short_experiments.py # 空單 20 策略實驗入口
├── index.html              # 整合報告（多空 + DXY + Next Action）
│
├── XAUUSD-Long-S1-AweWithBB/    # S1 策略：交易 CSV + report.html + Pine script
├── XAUUSD-Long-S2-Hybrid/       # S2 策略
├── XAUUSD-Long-S2-Pullback/     # S3 策略（資料夾名帶 Pullback）
├── XAUUSD-Long-Experiments/     # 多單實驗：report.html + pine/（20 files）
└── XAUUSD-Short-Experiments/    # 空單實驗：report.html + pine/（20 files）
```

---

## CSV 欄位格式（TradingView 匯出）

所有 csv/ 下的 K 棒檔案格式相同：
```
time, open, high, low, close, RSI, RSI-based MA,
Regular Bullish, Regular Bullish Label, Regular Bearish, Regular Bearish Label
```
- `time`：帶時區的 ISO 字串（`+08:00`），loader 自動轉為 Asia/Taipei 無時區
- `RSI`：RSI(14)
- `RSI-based MA`：RSI 的移動平均線（趨勢確認）
- `Regular Bullish/Bearish`：RSI 背離信號

**更新資料方式**：從 TradingView 匯出同樣格式的 CSV，直接覆蓋 `csv/` 下的對應檔案即可。

---

## 核心設計決策

### 失敗分類邏輯（analysis/fail_patterns.py）

虧損交易分為 4 類（依序判斷）：
- `immediate_loss`：MFE% < 0.1%（進場就錯）
- `false_breakout`：MFE% ≥ 0.1% 且 MAE/MFE > 2.0（曾有利潤但完全逆轉）
- `time_bleed`：持倉 ≥ 24 bars（≥12 小時，30 分鐘 K 棒）
- `normal_sl`：其他（正常止損）

### Pre-Entry K 棒特徵（analysis/pre_entry.py）

使用 RSI 相關特徵：
- `rsi`、`rsi_vs_ma`、`rsi_slope_3`
- `prev_1_dir`、`prev_3_green`、`prev_3_range`、`momentum_3`

### DXY 分析（analysis/dxy_analysis.py）

每筆交易新增 DXY 情境欄位（用 1D DXY，覆蓋全部 2 年歷史）：
- `dxy_rsi_1d`、`dxy_trend_1d`、`dxy_rsi_vs_ma`、`dxy_rsi_bucket`

### 回測引擎規則（experiments/engine.py）

| 參數 | 多單 | 空單 |
|------|------|------|
| 進場 | bar[i+1] open | bar[i+1] open |
| 止損 | entry × (1 - 0.5%) | entry × (1 + 0.5%) |
| 止盈 | entry × (1 + 1.0%) | entry × (1 - 1.0%) |
| 時間止損 | 48 bars（24h） | 48 bars（24h） |
| R:R | 2:1 | 2:1 |

### 交易時段定義（UTC+8）

- Asia（亞盤）：07:00–15:59
- Europe（歐盤）：16:00–21:59
- US（美盤）：22:00–06:59

---

## 現有策略最新績效（2026-04-27）

| ID | 策略名稱 | 版本 | 交易筆數 | 勝率 | 獲利因子 | 淨盈虧 | 最大回撤 | 主要問題 |
|----|---------|------|---------|------|---------|--------|---------|---------|
| S1 | AweWithBB | V3.4 | 504 | 53.2% | 1.525 | +$6,137 | -$494 | immediate_loss 31% |
| S2 | Hybrid | V2.0 | 161 | 42.2% | 1.679 | +$6,212 | -$1,177 | time_bleed 52% |
| S3 | Pullback | V1.9 | 200 | 44.0% | 1.681 | +$7,722 | -$1,431 | time_bleed 54% |

---

## DXY 分析關鍵發現

**DXY × XAUUSD 30 日滾動相關係數平均：-0.467**（反向關係成立）

| DXY RSI 區間 | S1 勝率 | S2-Hybrid 勝率 | S2-Pullback 勝率 |
|---|---|---|---|
| 超賣 < 30（USD 弱，黃金有利） | **60.9%** | **75.0%** | **66.7%** |
| 中性 30–50 | 49.8% | 38.4% | 38.2% |
| 中性 50–70 | 56.0% | 42.1% | 48.8% |
| 超買 > 70（USD 強，黃金承壓） | 52.9% | 62.5%* | 44.4% |

**結論**：DXY RSI 超賣（< 30）時三個策略勝率均顯著提升。
S2 策略在 DXY RSI 30–50 時表現最差，可考慮此區間縮倉或暫停。

---

## 多單實驗最新排名（3 個月 30m 資料，2026-01-21 至 2026-04-27）

| 排名 | 策略 | 分組 | 交易筆 | 勝率 | 獲利因子 | 淨盈虧% |
|------|------|------|--------|------|---------|--------|
| 1 | E03 MACD Signal | Momentum | 51 | 45.1% | 1.643 | +9.0% |
| 2 | E12 BB Squeeze Break | BB | 88 | 39.8% | 1.337 | +8.8% |
| 3 | E16 ATR Vol Break | Breakout | 99 | 36.4% | 1.124 | +3.9% |

## 空單實驗最新排名（同期資料）

| 排名 | 策略 | 分組 | 交易筆 | 勝率 | 獲利因子 | 淨盈虧% |
|------|------|------|--------|------|---------|--------|
| 1 | S19 Bearish Engulf | Pattern | 87 | 42.5% | 1.507 | +12.4% |
| 2 | S13 BB Basis Reject | BB | 69 | 42.0% | 1.450 | +9.0% |
| 3 | S12 BB Squeeze Break | BB | 105 | 39.0% | 1.252 | +8.0% |

**觀察**：空單策略此期間表現優於多單；BB 類策略多空雙向均有效。

---

## 輸出產物

- **`{策略資料夾}/report.html`** — 自含式 HTML（base64 圖片），含 DXY 分析段落
- **`XAUUSD-Long-Experiments/report.html`** — 多單 20 策略排名儀表板
- **`XAUUSD-Long-Experiments/pine/*.pine`** — 20 個多單 Pine Script v6
- **`XAUUSD-Short-Experiments/report.html`** — 空單 20 策略排名儀表板
- **`XAUUSD-Short-Experiments/pine/*.pine`** — 20 個空單 Pine Script v6
- **`index.html`** — 根目錄整合報告（多空 + DXY + Next Action，含各子報告連結）

---

## 技術環境

- Python 3.11（Windows 使用 `py -3.11`）
- 套件：pandas, numpy, matplotlib（見 requirements.txt）
- Pine Script v6（TradingView 使用）
- 無外部 API、無環境變數需求
