---
name: Project Context
description: XAUUSD 分析工具箱的目標、模組架構與最新績效
type: project
originSessionId: 50c1ae8c-8816-4a68-a11d-86ce07776023
---
## 目標
分析 XAUUSD 多單失敗模式，並系統測試多空策略。

## 三大模組
1. **Fail-Pattern Analysis** — 虧損交易分 4 類：immediate_loss / false_breakout / time_bleed / normal_sl
2. **Long Experiment Engine** — 20 個多單策略回測，自動產 Pine Script（E01–E20）
3. **Short Experiment Engine** — 20 個空單策略回測，自動產 Pine Script（S01–S20）

## 回測規則（experiments/engine.py）
- 止損：0.5%，止盈：1.0%，R:R = 2:1
- 時間止損：48 bars（30m K = 24 小時）
- 進場：信號 bar 的下一根 open

## 現有策略績效（截至 2026-04-27）
| 策略 | 勝率 | 獲利因子 | 淨盈虧 | 主要問題 |
|------|------|---------|--------|---------|
| S1-AweWithBB V3.6.2 | 49.0% | 1.23 | +$6,386 | immediate_loss 30%（7年1097筆） |
| S2A-RSI V2.3 | 38.2% | 1.38 | +$10,450 | time_bleed 65%（7年450筆） |
| S2B-Hammer V2.2 | 38.9% | 1.38 | +$12,908 | time_bleed 66%（7年560筆） |

## 實驗策略排名（3 個月 30m，2026-01-21 至 2026-04-27）
多單 Top3：E03 MACD Signal（PF 1.643）、E12 BB Squeeze Break（PF 1.337）、E16 ATR Vol Break（PF 1.124）
空單 Top3：S19 Bearish Engulf（PF 1.507）、S13 BB Basis Reject（PF 1.450）、S12 BB Squeeze Break（PF 1.252）

## DXY 關鍵發現
DXY RSI < 30（超賣）時三個策略勝率均顯著提升；S2 系列在 DXY RSI 30–50 時表現最差。

## index.html 四大主 Tab
1. **現有策略優化** — S1/S2A/S2B 績效、Pine Script 版本、分析紀錄
2. **實驗策略測試** — E01–E20 多單、S01–S20 空單排名
3. **當沖讀圖指南** — TPO 概念 / Footprint 概念 / 三層確認系統 / 決策速查表
4. **深度分析（2026-05-06 新增）** — S2B 垂頭陷阱、三策略進場清單、Time-Bleed 特徵

## 深度分析關鍵發現（2026-05-06）

**S1 最高信心組合：BB%B ≥ 0.8 + 4H bullish = 90.9% 勝率**（歷史最高條件組合）

**S2B 垂頭陷阱（做空）：**
- BB%B ≥ 0.8 時多單勝率 14.3%（7 筆，樣本小）
- 失敗全為 time_bleed/normal_sl，0 筆 false_breakout → 做空不會被反彈先掃止損
- 用戶實戰正向回饋，繼續觀察累積樣本

**Time-Bleed 條件：**
- S2A：4H neutral 時 61.5% 敗筆是 time_bleed（最危險條件）→ 超 12h 考慮手動平
- S2B：time_bleed 與 4H 狀態無關（53–55%）→ 需研究時段因素
- S1：time_bleed 僅 20.8%，各 4H 狀態差異小

## Why
**How to apply:** 
- S1 進場前確認 BB%B + 4H 狀態，兩者都符合才是最高信心
- S2A 進場後設心理時間停損（12h），4H neutral/bearish 尤其注意
- S2B 看到高位槌頭優先考慮空而非多，樣本持續累積中
