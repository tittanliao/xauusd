"""
Central configuration for all XAUUSD strategies.

To add a new strategy: append a dict to STRATEGIES following the same keys.
The analysis pipeline will automatically pick it up.
"""
from pathlib import Path

ROOT    = Path(__file__).parent.parent
CSV_DIR = ROOT / "csv"

STRATEGIES = [
    {
        "id": "S1-AweWithBB",       # Right-side breakout: BB + AO momentum
        "version": "3.4",
        "folder": ROOT / "XAUUSD-Long-S1-AweWithBB",
        "trades_csv": "S1-Awe-V3.4_FX_IDC_XAUUSD_2026-04-26.csv",
    },
    {
        "id": "S2A-RSI",            # Left-side reversion: indicator-triggered (RSI crossover / divergence)
        "version": "2.0",
        "folder": ROOT / "XAUUSD-Long-S2A-RSI",
        "trades_csv": "S2-Hybrid-V2.0_FX_IDC_XAUUSD_2026-04-26.csv",
    },
    {
        "id": "S2B-Hammer",         # Left-side reversion: price-action triggered (hammer candle)
        "version": "1.9",
        "folder": ROOT / "XAUUSD-Long-S2B-Hammer",
        "trades_csv": "S2-Pullback-V1.9_FX_IDC_XAUUSD_2026-04-26.csv",
    },
]

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
