"""
Entry point for the 20-strategy SHORT-side experiment.

Steps:
    1. Load 30-min OHLCV price data
    2. Run all 20 short strategies via the short backtest engine
    3. Score and rank strategies
    4. Generate HTML report -> XAUUSD-Short-Experiments/report.html
    5. Generate Pine Script files -> XAUUSD-Short-Experiments/pine/

Usage:
    py -3.11 run_short_experiments.py
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

from analysis.config import PRICE_CSV
from analysis import loader
from experiments.engine import run_backtest_short, summary
from experiments.strategies_short import STRATEGIES
from experiments.runner import score as score_fn
from experiments.report import generate as generate_html
from experiments.pine_generator_short import generate_all as generate_pine

import pandas as pd

OUT_DIR  = Path(__file__).parent / "XAUUSD-Short-Experiments"
HTML_OUT = OUT_DIR / "report.html"


def run_all_short(price: pd.DataFrame):
    rows = []
    trades_map = {}
    for strat_id, (fn, group, description) in STRATEGIES.items():
        trades = run_backtest_short(price, fn)
        summ   = summary(trades)
        trades_map[strat_id] = trades
        rows.append({
            "id":          strat_id,
            "group":       group,
            "description": description,
            **summ,
        })
    df = pd.DataFrame(rows).set_index("id")
    return df, trades_map


def main() -> None:
    print("=" * 60)
    print("  XAUUSD 20-Strategy Short-Side Experiment")
    print("=" * 60)

    print(f"\n[1/4] Loading price data from: {PRICE_CSV.name}")
    price = loader.load_price(PRICE_CSV)
    print(f"      {len(price)} bars  |  "
          f"{price['time'].min().date()} -> {price['time'].max().date()}")

    if len(price) < 60:
        print("ERROR: Need at least 60 bars.")
        sys.exit(1)

    print("\n[2/4] Running 20 short strategy backtests...")
    results, trades_map = run_all_short(price)
    scored = score_fn(results)

    print("\n  --- Strategy Ranking ---")
    display_cols = ["group", "total", "win_rate", "profit_factor",
                    "net_pnl_pct", "max_consec_loss", "score"]
    print(scored[display_cols].to_string(float_format="{:.3f}".format))

    best = scored.index[0]
    print(f"\n  [BEST] {best}  (score={scored.loc[best,'score']:.3f})")
    print(f"     Trades: {scored.loc[best,'total']:.0f}  |  "
          f"Win rate: {scored.loc[best,'win_rate']:.1%}  |  "
          f"Net P&L: {scored.loc[best,'net_pnl_pct']:+.2f}%")

    print("\n[3/4] Generating HTML report...")
    OUT_DIR.mkdir(exist_ok=True)
    generate_html(scored, trades_map, price, HTML_OUT)

    print("\n[4/4] Generating Pine Script files...")
    generate_pine()

    print(f"\n{'=' * 60}")
    print(f"  Done.")
    print(f"  HTML report  : {HTML_OUT}")
    print(f"  Pine scripts : {OUT_DIR / 'pine'}/")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
