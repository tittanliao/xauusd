"""
Entry point for the 20-strategy experiment.

Steps:
    1. Load 30-min OHLCV price data
    2. Run all 20 strategies via Python backtesting engine
    3. Score and rank strategies
    4. Generate HTML report → XAUUSD-Long-Experiments/report.html
    5. Generate Pine Script files → XAUUSD-Long-Experiments/pine/

Usage:
    python3.12 run_experiments.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

from analysis.config import PRICE_CSV
from analysis import loader
from experiments import runner
from experiments.report import generate as generate_html
from experiments.pine_generator import generate_all as generate_pine

OUT_DIR  = Path(__file__).parent / "XAUUSD-Long-Experiments"
HTML_OUT = OUT_DIR / "report.html"


def main() -> None:
    print("=" * 60)
    print("  XAUUSD 20-Strategy Experiment")
    print("=" * 60)

    # ── Load price data ───────────────────────────────────────────
    print(f"\n[1/4] Loading price data from: {PRICE_CSV.name}")
    price = loader.load_price(PRICE_CSV)
    print(f"      {len(price)} bars  |  "
          f"{price['time'].min().date()} → {price['time'].max().date()}")

    if len(price) < 60:
        print("ERROR: Need at least 60 bars. Export more OHLCV data from TradingView.")
        sys.exit(1)

    # ── Run backtests ─────────────────────────────────────────────
    print("\n[2/4] Running 20 strategy backtests...")
    results, trades_map = runner.run_all(price)
    scored = runner.score(results)

    print("\n  --- Strategy Ranking ---")
    display_cols = ["group", "total", "win_rate", "profit_factor",
                    "net_pnl_pct", "max_consec_loss", "score"]
    print(scored[display_cols].to_string(float_format="{:.3f}".format))

    best = scored.index[0]
    print(f"\n  🏆 Best strategy: {best}  (score={scored.loc[best,'score']:.3f})")
    print(f"     Trades: {scored.loc[best,'total']:.0f}  |  "
          f"Win rate: {scored.loc[best,'win_rate']:.1%}  |  "
          f"Net P&L: {scored.loc[best,'net_pnl_pct']:+.2f}%")

    # ── HTML report ───────────────────────────────────────────────
    print("\n[3/4] Generating HTML report...")
    OUT_DIR.mkdir(exist_ok=True)
    generate_html(scored, trades_map, price, HTML_OUT)

    # ── Pine Script files ─────────────────────────────────────────
    print("\n[4/4] Generating Pine Script files...")
    generate_pine()

    print(f"\n{'=' * 60}")
    print(f"  Done.")
    print(f"  HTML report  : {HTML_OUT}")
    print(f"  Pine scripts : {OUT_DIR / 'pine'}/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
