"""
Long-only backtesting engine for 30-min XAUUSD bar data.

Rules:
    - Signal generated on bar[i] close (no look-ahead into the same bar)
    - Entry at bar[i+1] open price
    - SL  : fixed % below entry
    - TP  : fixed % above entry  (R:R = TP_PCT / SL_PCT)
    - TIME: exit at close of bar[i + MAX_HOLD_BARS] if neither SL nor TP hit
    - One trade at a time (no pyramiding)

Data requirement: price DataFrame with columns [time, open, high, low, close].
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

SL_PCT       = 0.005   # 0.5 %
TP_PCT       = 0.010   # 1.0 %  →  2:1 reward-to-risk
MAX_HOLD_BARS = 48     # 24 hours on 30-min bars


# ---------------------------------------------------------------------------
# Trade record
# ---------------------------------------------------------------------------

@dataclass
class Trade:
    entry_bar:    int
    entry_time:   pd.Timestamp
    entry_price:  float
    sl_price:     float
    tp_price:     float
    exit_bar:     int              = -1
    exit_time:    pd.Timestamp     = None
    exit_price:   float            = 0.0
    exit_reason:  str              = ""
    pnl_pct:      float            = 0.0
    hold_bars:    int              = 0
    mfe_pct:      float            = 0.0
    mae_pct:      float            = 0.0
    result:       str              = ""


def _finalise(t: Trade) -> None:
    t.pnl_pct   = (t.exit_price - t.entry_price) / t.entry_price * 100
    t.hold_bars = t.exit_bar - t.entry_bar
    t.result    = "win" if t.pnl_pct > 0 else "loss"


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_backtest(
    price: pd.DataFrame,
    signal_fn: Callable[[pd.DataFrame, int], bool],
) -> list[Trade]:
    """
    Runs a single strategy on price data.

    signal_fn(price, bar_idx) must return True when a long entry signal fires.
    It receives the full price DataFrame and the current bar index so it can
    look back as far as needed, but must NOT read bar_idx+1 or later.
    """
    trades: list[Trade] = []
    in_trade = False
    current: Trade | None = None

    highs  = price["high"].to_numpy()
    lows   = price["low"].to_numpy()
    closes = price["close"].to_numpy()
    opens  = price["open"].to_numpy()
    times  = price["time"].to_numpy()

    n = len(price)

    for i in range(1, n):
        # ── Manage open trade ──────────────────────────────────────
        if in_trade and current is not None:
            mfe_price = highs[i]
            mae_price = lows[i]
            current.mfe_pct = max(current.mfe_pct,
                                  (mfe_price - current.entry_price) / current.entry_price * 100)
            current.mae_pct = min(current.mae_pct,
                                  (mae_price - current.entry_price) / current.entry_price * 100)

            hit_sl = lows[i]   <= current.sl_price
            hit_tp = highs[i]  >= current.tp_price
            timed  = (i - current.entry_bar) >= MAX_HOLD_BARS

            if hit_sl and hit_tp:
                # Assume SL hit first (conservative)
                reason, px = "SL", current.sl_price
            elif hit_sl:
                reason, px = "SL", current.sl_price
            elif hit_tp:
                reason, px = "TP", current.tp_price
            elif timed:
                reason, px = "TIME", closes[i]
            else:
                continue  # still in trade, move to next bar

            current.exit_bar   = i
            current.exit_time  = pd.Timestamp(times[i])
            current.exit_price = px
            current.exit_reason = reason
            _finalise(current)
            trades.append(current)
            in_trade = False
            current  = None

        # ── Check for new signal ───────────────────────────────────
        if (not in_trade) and (i < n - 1):
            if signal_fn(price, i):
                ep = opens[i + 1]
                current = Trade(
                    entry_bar   = i + 1,
                    entry_time  = pd.Timestamp(times[i + 1]),
                    entry_price = ep,
                    sl_price    = ep * (1 - SL_PCT),
                    tp_price    = ep * (1 + TP_PCT),
                    mfe_pct     = 0.0,
                    mae_pct     = 0.0,
                )
                in_trade = True

    return trades


# ---------------------------------------------------------------------------
# Metrics from a list of trades
# ---------------------------------------------------------------------------

def summary(trades: list[Trade]) -> dict:
    if not trades:
        return {k: 0 for k in [
            "total", "wins", "losses", "win_rate", "profit_factor",
            "net_pnl_pct", "avg_win_pct", "avg_loss_pct",
            "avg_mfe_pct", "avg_mae_pct", "avg_hold_bars", "max_consec_loss",
        ]}

    wins   = [t for t in trades if t.result == "win"]
    losses = [t for t in trades if t.result == "loss"]
    total  = len(trades)

    gp = sum(t.pnl_pct for t in wins)
    gl = abs(sum(t.pnl_pct for t in losses))

    # Max consecutive losses
    max_cl, cl = 0, 0
    for t in trades:
        cl = cl + 1 if t.result == "loss" else 0
        max_cl = max(max_cl, cl)

    return {
        "total":           total,
        "wins":            len(wins),
        "losses":          len(losses),
        "win_rate":        len(wins) / total,
        "profit_factor":   gp / gl if gl else float("inf"),
        "net_pnl_pct":     sum(t.pnl_pct for t in trades),
        "avg_win_pct":     gp / len(wins)  if wins   else 0.0,
        "avg_loss_pct":    -gl / len(losses) if losses else 0.0,
        "avg_mfe_pct":     np.mean([t.mfe_pct for t in trades]),
        "avg_mae_pct":     np.mean([t.mae_pct for t in trades]),
        "avg_hold_bars":   np.mean([t.hold_bars for t in trades]),
        "max_consec_loss": max_cl,
    }
