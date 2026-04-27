---
name: Project Context
description: XAUUSD 分析工具箱的目標、模組架構與最新績效
type: project
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
| S1 AweWithBB V3.4 | 53.2% | 1.525 | +$6,137 | immediate_loss 31% |
| S2 Hybrid V2.0 | 42.2% | 1.679 | +$6,212 | time_bleed 52% |
| S3 Pullback V1.9 | 44.0% | 1.681 | +$7,722 | time_bleed 54% |

## 實驗策略排名（3 個月 30m，2026-01-21 至 2026-04-27）
多單 Top3：E03 MACD Signal（PF 1.643）、E12 BB Squeeze Break（PF 1.337）、E16 ATR Vol Break（PF 1.124）
空單 Top3：S19 Bearish Engulf（PF 1.507）、S13 BB Basis Reject（PF 1.450）、S12 BB Squeeze Break（PF 1.252）

## DXY 關鍵發現
DXY RSI < 30（超賣）時三個策略勝率均顯著提升；S2 系列在 DXY RSI 30–50 時表現最差。

## Why
**How to apply:** 建議新策略時優先考慮 time_bleed 問題（S2/S3）和 immediate_loss 問題（S1）；空單此期間表現優於多單。
