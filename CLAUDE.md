# XAUUSD Trading Strategy Analysis Toolkit — CLAUDE.md

## 專案目的

分析 XAUUSD（黃金/美元）Long-Only 交易策略的失敗模式，並系統性地測試新策略。
包含兩大模組：

1. **Fail-Pattern Analysis** — 分析現有策略的虧損交易，找出失敗根因
2. **20-Strategy Experiment Engine** — 回測 20 個新策略，自動生成 TradingView Pine Script

---

## 執行方式

```bash
# 分析所有 3 個既有策略（生成 HTML report）
python main.py

# 只分析單一策略
python main.py S1-AweWithBB
python main.py S2-Hybrid
python main.py S2-Pullback

# 執行 20 策略實驗（生成 report + 20 個 Pine Scripts）
python run_experiments.py
```

---

## 目錄結構

```
xauusd/
├── analysis/           # Fail-pattern 分析套件（1,142 行）
│   ├── config.py       # 3 個策略設定 + 失敗分類門檻
│   ├── loader.py       # TradingView CSV → 正規化 DataFrame
│   ├── metrics.py      # 統計指標（win_rate, profit_factor, drawdown）
│   ├── fail_patterns.py# 虧損分類邏輯（核心）
│   ├── pre_entry.py    # 進場前情境分析（交易資料 + K 棒特徵）
│   ├── charts.py       # 13 種 matplotlib 圖表
│   └── report.py       # 自含式 HTML 報告生成器
│
├── experiments/        # 20 策略回測引擎（1,575 行）
│   ├── engine.py       # 核心回測邏輯（進場/SL/TP/時間出場）
│   ├── indicators.py   # 11 個技術指標
│   ├── strategies.py   # 20 個策略信號（E01–E20）
│   ├── runner.py       # 執行所有策略 + 複合評分
│   ├── pine_generator.py # 自動生成 20 個 Pine Script v6
│   └── report.py       # HTML 實驗結果儀表板
│
├── main.py             # Fail-pattern 分析入口
├── run_experiments.py  # 20 策略實驗入口
│
├── XAUUSD-Long-S1-AweWithBB/   # S1 策略：交易 CSV + report.html + Pine script
├── XAUUSD-Long-S2-Hybrid/      # S2 策略
├── XAUUSD-Long-S2-Pullback/    # S3 策略（資料夾名稱帶 Pullback）
├── XAUUSD-Long-Experiments/    # 20 策略輸出：report.html + pine/ 目錄
│
└── FX_IDC_XAUUSD, 30.csv       # 30 分鐘 OHLCV + BB + EMA（414 根 K 棒，2026-04-14 起）
```

---

## 核心設計決策

### 失敗分類邏輯（analysis/fail_patterns.py）

虧損交易分為 4 類（依序判斷）：
- `immediate_loss`：MFE% < 0.1%（進場就錯）
- `false_breakout`：MFE% ≥ 0.1% 且 MAE/MFE > 2.0（曾有利潤但完全逆轉）
- `time_bleed`：持倉 ≥ 24 bars（≥12 小時，30 分鐘 K 棒）
- `normal_sl`：其他（正常止損）

門檻定義在 `analysis/config.py`：
```python
IMMEDIATE_LOSS_MFE_PCT = 0.10
TIME_BLEED_MIN_BARS = 24
FALSE_BREAKOUT_MAE_MFE_RATIO = 2.0
```

### 回測引擎規則（experiments/engine.py）

- **進場**：信號在 bar[i] 收盤觸發，下一根 bar[i+1] 開盤執行
- **止損**：進場價 × (1 - 0.5%) = 0.5% 以下
- **止盈**：進場價 × (1 + 1.0%) = 1.0% 以上（2:1 R:R）
- **時間出場**：最多持倉 48 根 K 棒（24 小時）

### 交易時段定義（UTC+8）

- Asia（亞盤）：07:00–15:59
- Europe（歐盤）：16:00–21:59
- US（美盤）：22:00–06:59

### 複合評分公式（experiments/runner.py）

```
score = (win_rate × 0.25) + (profit_factor × 0.25) + (trade_count_norm × 0.20)
      + (net_pnl_pct × 0.20) - (max_consec_loss × 0.10)
```

---

## 現有策略概況

| ID | 策略名稱 | 版本 | 交易筆數 | 資料夾 |
|----|---------|------|---------|--------|
| S1 | AweWithBB | V3.4 | 600+ | XAUUSD-Long-S1-AweWithBB |
| S2 | Hybrid | V2.0 | — | XAUUSD-Long-S2-Hybrid |
| S3 | Pullback | V1.9 | — | XAUUSD-Long-S2-Pullback |

---

## 20 個實驗策略分組（experiments/strategies.py）

| 組別 | 策略 | 說明 |
|------|------|------|
| Trend/Momentum | E01–E05 | EMA Cross, Triple EMA, MACD, Supertrend, ADX+EMA Dip |
| Oscillator Bounces | E06–E10 | RSI Oversold, Stochastic Cross, CCI Bounce, Williams %R, RSI Divergence |
| Bollinger Bands | E11–E13 | Lower Touch, Squeeze Break, Basis Walk |
| Breakout | E14–E16 | Donchian Break, Inside Bar Break, ATR Vol Break |
| Pattern/Confluence | E17–E20 | AO Saucer, Hammer, Bullish Engulfing, Multi-indicator Confluence |

---

## 輸出產物

- **`{策略資料夾}/report.html`** — 自含式 HTML（內嵌 base64 圖片），包含 13 種圖表
- **`XAUUSD-Long-Experiments/report.html`** — 20 策略排名儀表板
- **`XAUUSD-Long-Experiments/pine/E01_*.pine` … `E20_*.pine`** — 可直接貼入 TradingView 的 Pine Script v6

---

## 資料限制與待改進方向

1. **K 棒資料僅 3 天**（414 根 K 棒，2026-04-14 至 2026-04-16）
   - `pre_entry.py` 的 Layer 2（BB%B, momentum 等 K 棒特徵）需要更長的歷史資料才能覆蓋到所有交易
   - 可從 TradingView 匯出更長區間的 `FX_IDC_XAUUSD, 30.csv` 來改善覆蓋率

2. **20 策略回測時間窗口與策略 CSV 不一致**
   - 目前 20 策略回測用的是 FX_IDC_XAUUSD, 30.csv（僅 3 天）
   - 建議匯出與策略 CSV 同樣時間範圍的 K 棒資料

3. **可考慮加入的下一步**
   - 在 20 策略中挑出 top-3，深入做 fail-pattern analysis
   - 加入跨時間段的走向過濾（只在趨勢方向做多）
   - 把 Pine Script 結果貼回 TradingView 驗證後，更新 report

---

## 技術環境

- Python 3.12
- 套件：pandas, numpy, matplotlib, jupyter（見 requirements.txt）
- Pine Script v6（TradingView 使用）
- 無外部 API、無環境變數需求

---

## Git 歷史

| Commit | 日期 | 說明 |
|--------|------|------|
| b1c4278 | 2026-04-27 | Initial commit：fail-pattern 分析框架 + 3 個策略 |
| ebb74f7 | 2026-04-27 | 加入 20 策略實驗引擎 + HTML report + Pine Scripts |
