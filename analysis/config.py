"""
Central configuration for all XAUUSD strategies.

Use get_strategies(mode) to switch between 'short' (3.5 months) and 'long' (7 years).
STRATEGIES defaults to the long dataset for backward compatibility.
"""
from pathlib import Path

ROOT    = Path(__file__).parent.parent
CSV_DIR = ROOT / "csv"

# --- Dual-dataset mode definitions ---
# Why: need to compare short-term performance (2026-01-21~04-27) vs long-term (2019~2026)
#      to distinguish if a strategy is in a favourable market phase or genuinely robust.
DATASET_MODES = {
    "short": {
        "label": "短期（2026-01-21 ~ 2026-04-27，3.5 個月）",
        "S1-AweWithBB": "S1-Awe-V3.4_FX_IDC_XAUUSD_2026-04-26.csv",
        "S2A-RSI":      "S2-Hybrid-V2.0_FX_IDC_XAUUSD_2026-04-26.csv",
        "S2B-Hammer":   "S2-Pullback-V1.9_FX_IDC_XAUUSD_2026-04-26.csv",
    },
    "long": {
        "label": "長期（2019 ~ 2026-05-06，7 年）",
        "S1-AweWithBB": "S1-Awe-V3.4_FX_IDC_XAUUSD_2026-05-06.csv",
        "S2A-RSI":      "S2-Hybrid-V2.0_FX_IDC_XAUUSD_2026-05-06.csv",
        "S2B-Hammer":   "S2-Pullback-V1.9_FX_IDC_XAUUSD_2026-05-06.csv",
    },
}

_STRATEGY_BASE = [
    {
        "id": "S1-AweWithBB",   # Right-side breakout: BB + AO momentum
        "version": "3.4",
        "folder": ROOT / "XAUUSD-Long-S1-AweWithBB",
    },
    {
        "id": "S2A-RSI",        # Left-side reversion: indicator-triggered (RSI crossover / divergence)
        "version": "2.0",
        "folder": ROOT / "XAUUSD-Long-S2A-RSI",
    },
    {
        "id": "S2B-Hammer",     # Left-side reversion: price-action triggered (hammer candle)
        "version": "1.9",
        "folder": ROOT / "XAUUSD-Long-S2B-Hammer",
    },
]


def get_strategies(mode: str = "long") -> list[dict]:
    """Return strategy configs with trade CSVs for the given dataset mode."""
    if mode not in DATASET_MODES:
        raise ValueError(f"Unknown mode '{mode}'. Choose from: {list(DATASET_MODES)}")
    files = DATASET_MODES[mode]
    return [{**s, "trades_csv": files[s["id"]]} for s in _STRATEGY_BASE]


# Default: long dataset (7-year history); kept for backward compatibility
STRATEGIES = get_strategies("long")

PRICE_CSV     = CSV_DIR / "FX_IDC_XAUUSD, 30.csv"
PRICE_CSV_60M = CSV_DIR / "FX_IDC_XAUUSD, 60.csv"
PRICE_CSV_4H  = CSV_DIR / "FX_IDC_XAUUSD, 240.csv"
DXY_CSV_30    = CSV_DIR / "TVC_DXY, 30.csv"
DXY_CSV_1D    = CSV_DIR / "TVC_DXY, 1D.csv"
XAUUSD_CSV_1D = CSV_DIR / "FX_IDC_XAUUSD, 1D.csv"

# --- Fail pattern classification thresholds ---
# A loss where MFE% never exceeded this value is "immediate_loss" (entry was wrong instantly)
IMMEDIATE_LOSS_MFE_PCT = 0.10

# A losing trade that held >= this many 30-min bars before stopping out = "time_bleed"
TIME_BLEED_MIN_BARS = 24  # 12 hours

# A loss where MFE was positive but MAE/MFE ratio is high = "false_breakout"
# i.e. it moved in our favour but then reversed fully to SL
FALSE_BREAKOUT_MAE_MFE_RATIO = 2.0
