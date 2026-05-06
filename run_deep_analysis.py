"""
Deep analysis runner: Step 1 (S2B 垂頭陷阱), Step 2 (進場清單), Step 3 (Time-bleed).

Usage:
    py -3.11 run_deep_analysis.py               # long dataset (7 years, default)
    py -3.11 run_deep_analysis.py --mode short  # short dataset (3.5 months)

Output:
    XAUUSD-Deep-Analysis/report.html
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

from analysis.config import (
    get_strategies, DATASET_MODES,
    PRICE_CSV, PRICE_CSV_4H,
    XAUUSD_CSV_1D, DXY_CSV_1D,
)
from analysis import loader
from analysis.deep_analysis import s2b_trap_analysis, entry_checklist, time_bleed_features
from analysis.deep_report import generate

OUT_DIR = Path(__file__).parent / "XAUUSD-Deep-Analysis"
OUT_DIR.mkdir(exist_ok=True)


def _load_data():
    return {
        "price_30m": loader.load_price(PRICE_CSV),
        "price_4h":  loader.load_price(PRICE_CSV_4H) if PRICE_CSV_4H.exists() else None,
        "price_1d":  loader.load_price(XAUUSD_CSV_1D) if XAUUSD_CSV_1D.exists() else None,
        "dxy_1d":    loader.load_dxy(DXY_CSV_1D) if DXY_CSV_1D.exists() else None,
    }


def _load_trades(cfg: dict):
    return loader.load_trades(cfg["folder"] / cfg["trades_csv"])


def main():
    parser = argparse.ArgumentParser(description="XAUUSD deep analysis")
    parser.add_argument(
        "--mode", choices=["short", "long"], default="long",
        help="Dataset mode: 'short' (3.5 months) or 'long' (7 years, default)",
    )
    args = parser.parse_args()

    strategies = get_strategies(args.mode)
    print(f"[Dataset: {DATASET_MODES[args.mode]['label']}]")
    print("Loading price / DXY data...")
    data = _load_data()
    for k, v in data.items():
        if v is not None:
            print(f"  [{k}] {len(v)} bars")

    # Load all three strategy trade sets
    s_map = {c["id"]: c for c in strategies}
    trades = {sid: _load_trades(cfg) for sid, cfg in s_map.items()}
    for sid, df in trades.items():
        print(f"  [{sid}] {len(df)} trades")

    price_30m = data["price_30m"]
    price_4h  = data["price_4h"]
    price_1d  = data["price_1d"]
    dxy_1d    = data["dxy_1d"]

    # ── Step 1: S2B 垂頭陷阱 ────────────────────────────────────────────────
    print("\n[Step 1] S2B 垂頭陷阱 失敗模式分解...")
    trap = s2b_trap_analysis(trades["S2B-Hammer"], price_30m)

    hs = trap["high_bb_summary"]
    ls = trap["low_bb_summary"]
    print(f"  BB%B >= 0.8 : {hs['total']} trades, win_rate={hs['win_rate']:.1%}, losses={hs['losses']}")
    print(f"  BB%B <  0.8 : {ls['total']} trades, win_rate={ls['win_rate']:.1%}")
    if trap["fail_dist"]:
        print(f"  High-BB fail dist: {trap['fail_dist']}")
        print(f"  immediate_loss={trap['immediate_loss_count']}, false_breakout={trap['false_breakout_count']}")
    if trap["false_breakout_stats"]:
        fb = trap["false_breakout_stats"]
        print(f"  FB avg MFE={fb['mean_mfe_pct']:.3f}%, survivable(MFE<0.5%)={fb['survivable_pct']:.1f}%")

    # ── Step 2: Entry checklists ─────────────────────────────────────────────
    print("\n[Step 2] 進場清單（三策略）...")
    checklists: dict = {}
    for sid in ["S1-AweWithBB", "S2A-RSI", "S2B-Hammer"]:
        print(f"  {sid}...")
        checklists[sid] = entry_checklist(
            trades[sid], price_30m, price_4h, price_1d, dxy_1d, sid
        )
        if "by_4h_state" in checklists[sid] and not checklists[sid]["by_4h_state"].empty:
            print(f"    4H state:\n{checklists[sid]['by_4h_state'][['total','win_rate']].to_string()}")
        if "cross_4h_x_bb" in checklists[sid]:
            print(f"    4H x BB matrix:\n{checklists[sid]['cross_4h_x_bb']['win_rate'].to_string()}")

    # ── Step 3: Time-bleed features ──────────────────────────────────────────
    print("\n[Step 3] Time-bleed 特徵（三策略）...")
    tb_results: dict = {}
    for sid in ["S1-AweWithBB", "S2A-RSI", "S2B-Hammer"]:
        print(f"  {sid}...")
        tb_results[sid] = time_bleed_features(
            trades[sid], price_30m, price_4h, price_1d, dxy_1d, sid
        )
        r = tb_results[sid]
        print(f"    time_bleed {r['time_bleed_count']}/{r['total_losses']} losses "
              f"= {r['time_bleed_pct_of_losses']:.1%}")
        if "by_4h_state" in r and not r["by_4h_state"].empty:
            print(f"    by 4H:\n{r['by_4h_state'][['total','losses','time_bleed','tb_rate','win_rate']].to_string()}")

    # ── Generate HTML report ─────────────────────────────────────────────────
    print("\nGenerating HTML report...")
    generate(trap, checklists, tb_results, OUT_DIR / "report.html")
    print(f"\nDone. Open: {OUT_DIR / 'report.html'}")


if __name__ == "__main__":
    main()
