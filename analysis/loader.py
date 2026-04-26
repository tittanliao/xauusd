"""
Loads and normalizes CSV files exported from TradingView.

TradingView backtest CSV format (each trade = 2 rows: Entry + Exit):
    Trade #, Type, Date and time, Signal, Price USD, Size (qty),
    Size (value), Net P&L USD, Net P&L %, Favorable excursion USD,
    Favorable excursion %, Adverse excursion USD, Adverse excursion %,
    Cumulative P&L USD, Cumulative P&L %

load_trades() merges entry/exit pairs into one row per trade.
load_price()  reads the 30-min OHLCV candle file.
"""
from pathlib import Path

import pandas as pd


def load_trades(csv_path: Path) -> pd.DataFrame:
    """
    Returns one row per completed trade with both entry and exit fields.

    Output columns:
        trade_id        int    — TradingView trade number
        entry_time      datetime64[ns]
        exit_time       datetime64[ns]
        entry_signal    str    — e.g. S1_LE, S2_Rev
        exit_signal     str    — e.g. S1_SL, S1_LX_TP1
        entry_price     float
        exit_price      float
        size_qty        float
        size_value      float
        net_pnl_usd     float
        net_pnl_pct     float
        mfe_usd         float  — Maximum Favorable Excursion
        mfe_pct         float
        mae_usd         float  — Maximum Adverse Excursion
        mae_pct         float
        cum_pnl_usd     float
        cum_pnl_pct     float
        hold_bars       int    — number of 30-min bars held
        result          str    — "win" | "loss" | "breakeven"
    """
    raw = pd.read_csv(csv_path, encoding="utf-8-sig")
    raw.columns = raw.columns.str.strip()

    entries = raw[raw["Type"] == "Entry long"].rename(columns={
        "Date and time": "entry_time",
        "Signal": "entry_signal",
        "Price USD": "entry_price",
    })[["Trade #", "entry_time", "entry_signal", "entry_price"]]

    exits = raw[raw["Type"] == "Exit long"].rename(columns={
        "Date and time": "exit_time",
        "Signal": "exit_signal",
        "Price USD": "exit_price",
    })

    trades = entries.merge(
        exits[[
            "Trade #", "exit_time", "exit_signal", "exit_price",
            "Size (qty)", "Size (value)",
            "Net P&L USD", "Net P&L %",
            "Favorable excursion USD", "Favorable excursion %",
            "Adverse excursion USD", "Adverse excursion %",
            "Cumulative P&L USD", "Cumulative P&L %",
        ]],
        on="Trade #",
        how="inner",
    ).rename(columns={
        "Trade #": "trade_id",
        "Size (qty)": "size_qty",
        "Size (value)": "size_value",
        "Net P&L USD": "net_pnl_usd",
        "Net P&L %": "net_pnl_pct",
        "Favorable excursion USD": "mfe_usd",
        "Favorable excursion %": "mfe_pct",
        "Adverse excursion USD": "mae_usd",
        "Adverse excursion %": "mae_pct",
        "Cumulative P&L USD": "cum_pnl_usd",
        "Cumulative P&L %": "cum_pnl_pct",
    })

    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["exit_time"] = pd.to_datetime(trades["exit_time"])

    # 30-min bars held (1 bar = 1800 seconds)
    trades["hold_bars"] = (
        (trades["exit_time"] - trades["entry_time"]).dt.total_seconds() / 1800
    ).astype(int)

    trades["result"] = trades["net_pnl_usd"].apply(
        lambda x: "win" if x > 0 else ("loss" if x < 0 else "breakeven")
    )

    return trades.sort_values("entry_time").reset_index(drop=True)


def load_price(csv_path: Path) -> pd.DataFrame:
    """
    Reads the 30-min OHLCV file exported from TradingView.

    Preserves BB and Fast EMA columns when present (exported with indicators).
    Returned column names are normalised:
        time, open, high, low, close, bb_basis, bb_upper, bb_lower, bb_ema
    Any duplicate Basis/Upper/Lower columns (TradingView exports them twice)
    are deduplicated — only the first occurrence is kept.
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df["time"] = (
        pd.to_datetime(df["time"], utc=True)
        .dt.tz_convert("Asia/Taipei")
        .dt.tz_localize(None)
    )

    # Rename indicator columns when present, ignoring duplicate suffixes (.1)
    rename_map = {
        "Basis": "bb_basis", "Upper": "bb_upper", "Lower": "bb_lower",
        "Fast EMA": "bb_ema",
    }
    df = df.rename(columns=rename_map)

    keep = ["time", "open", "high", "low", "close"]
    for col in ["bb_basis", "bb_upper", "bb_lower", "bb_ema"]:
        if col in df.columns:
            keep.append(col)

    return df[keep].sort_values("time").reset_index(drop=True)
