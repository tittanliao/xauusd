"""
Entry point: full fail-pattern analysis for all XAUUSD strategies.

Usage:
    python3.12 main.py                  # all strategies
    python3.12 main.py S1-AweWithBB     # single strategy by id

Output per strategy:
    reports/<id>/          PNG charts (reference copies)
    <strategy-folder>/report.html   self-contained HTML report
"""
import sys
from pathlib import Path

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("Agg")

from analysis.config import STRATEGIES, PRICE_CSV, DXY_CSV_1D, DXY_CSV_30, XAUUSD_CSV_1D
from analysis import loader, metrics, fail_patterns, pre_entry, charts, report, dxy_analysis

REPORTS = Path(__file__).parent / "reports"


def _load_dxy_data():
    """Load DXY 1D and 30m data; returns (dxy_1d, dxy_30, xauusd_1d)."""
    dxy_1d   = loader.load_dxy(DXY_CSV_1D)   if DXY_CSV_1D.exists()   else None
    dxy_30   = loader.load_dxy(DXY_CSV_30)   if DXY_CSV_30.exists()   else None
    xau_1d   = loader.load_price(XAUUSD_CSV_1D) if XAUUSD_CSV_1D.exists() else None
    return dxy_1d, dxy_30, xau_1d


def run_strategy(cfg: dict, dxy_1d=None, dxy_30=None, xauusd_1d=None) -> None:
    name    = cfg["id"]
    version = cfg["version"]
    csv_path = cfg["folder"] / cfg["trades_csv"]

    print(f"\n{'=' * 60}")
    print(f"  {name}  v{version}")
    print(f"{'=' * 60}")

    # ── Load & basic metrics ──────────────────────────────────────
    trades = loader.load_trades(csv_path)
    summ   = metrics.summary(trades)

    print(f"  Trades          : {summ['total_trades']}")
    print(f"  Win Rate        : {summ['win_rate']:.1%}")
    print(f"  Profit Factor   : {summ['profit_factor']:.2f}")
    print(f"  Net P&L         : ${summ['net_pnl']:,.2f}")
    print(f"  Max Drawdown    : ${metrics.max_drawdown(trades):,.2f}")
    print(f"  Avg Hold        : {summ['avg_hold_bars']:.1f} bars")
    print(f"  Max Consec Loss : {summ['max_consec_losses']}")

    # ── Fail pattern classification ───────────────────────────────
    classified = fail_patterns.classify_fail(trades)
    print(f"\n  --- Fail Patterns ({len(classified)} losses) ---")
    print(fail_patterns.fail_type_summary(classified).to_string())

    sess = fail_patterns.session_stats(trades)
    print(f"\n  --- Session Stats ---")
    print(sess[["total", "wins", "win_rate", "avg_pnl"]].to_string())

    print(f"\n  --- Fail by Session ---")
    print(fail_patterns.fail_by_session(classified).to_string())

    # ── Pre-entry analysis (immediate_loss) ───────────────────────
    imm_losses = classified[classified["fail_type"] == "immediate_loss"].copy()
    profile, enriched = {}, pd.DataFrame()

    if len(imm_losses):
        trades_ctx = pre_entry.add_trade_context(
            trades.merge(classified[["trade_id", "fail_type"]], on="trade_id", how="left")
        )
        profile = pre_entry.immediate_loss_profile(trades_ctx)

        print(f"\n  --- Immediate Loss: Entry Hour ---")
        print(profile["entry_hour"].to_string())

        price    = loader.load_price(PRICE_CSV)
        enriched = pre_entry.enrich_with_kbars(imm_losses, price)
        cov      = pre_entry.kbar_coverage(enriched)
        print(f"\n  --- K-Bar Coverage: {cov['with_kbar_data']}/{cov['total_losses']} "
              f"({cov['coverage_pct']}%) ---")
        if cov["with_kbar_data"] > 0:
            cols = ["trade_id", "entry_time", "rsi", "rsi_vs_ma",
                    "prev_1_dir", "prev_3_green", "momentum_3"]
            print(enriched.dropna(subset=["rsi"])[cols].to_string())

    # ── DXY analysis ──────────────────────────────────────────────
    dxy_stats_out, corr_df_out = None, None
    if dxy_1d is not None:
        enriched_dxy = dxy_analysis.enrich_trades_with_dxy(trades, dxy_1d, dxy_30)
        dxy_stats_out = dxy_analysis.dxy_regime_stats(enriched_dxy)
        print(f"\n  --- DXY Win Rate by RSI Bucket ---")
        print(dxy_stats_out["by_bucket"].to_string())
        print(f"\n  --- DXY Win Rate by Trend ---")
        print(dxy_stats_out["by_trend"].to_string())
        if xauusd_1d is not None:
            corr_df_out = dxy_analysis.dxy_correlation_stats(xauusd_1d, dxy_1d)
            avg_c = corr_df_out["rolling_corr"].dropna().mean()
            print(f"\n  --- DXY×XAUUSD Avg 30D Correlation: {avg_c:.3f} ---")

    # ── PNG charts (reference folder) ────────────────────────────
    out_dir = REPORTS / name
    out_dir.mkdir(parents=True, exist_ok=True)

    png_jobs = [
        ("equity_curve.png",    charts.equity_curve(trades, name)),
        ("fail_types.png",      charts.fail_type_breakdown(classified, name)),
        ("mfe_dist.png",        charts.mfe_distribution(classified, name)),
        ("mae_vs_mfe.png",      charts.mae_vs_mfe_scatter(classified, name)),
        ("session_heatmap.png", charts.session_heatmap(sess, name)),
        ("hourly_winrate.png",  charts.hourly_winrate(fail_patterns.hourly_stats(trades), name)),
        ("consec_losses.png",   charts.consecutive_loss_hist(metrics.consecutive_losses(trades), name)),
        ("hold_time_dist.png",  charts.hold_time_dist(trades, name)),
    ]
    if profile:
        png_jobs += [
            ("pre_entry_hour.png",  charts.pre_entry_hour(profile, name)),
            ("pre_entry_dow.png",   charts.pre_entry_dow(profile, name)),
            ("pre_entry_prev.png",  charts.pre_entry_prev_result(profile, name)),
            ("pre_entry_tsw.png",   charts.pre_entry_tsw(profile, name)),
            ("kbar_features.png",   charts.kbar_feature_summary(enriched, name)),
        ]

    for filename, fig in png_jobs:
        fig.savefig(out_dir / filename, dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"  PNG charts → {out_dir}/")

    # ── HTML report → strategy folder ────────────────────────────
    html_path = cfg["folder"] / "report.html"
    report.generate(
        strategy_id=name,
        version=version,
        trades=trades,
        classified=classified,
        sess_stats=sess,
        profile=profile,
        enriched=enriched,
        out_path=html_path,
        dxy_stats=dxy_stats_out,
        corr_df=corr_df_out,
    )


def main() -> None:
    target_ids = set(sys.argv[1:])
    strategies = [
        cfg for cfg in STRATEGIES
        if not target_ids or cfg["id"] in target_ids
    ]
    if not strategies:
        available = [c["id"] for c in STRATEGIES]
        print(f"No match. Available: {available}")
        sys.exit(1)

    dxy_1d, dxy_30, xauusd_1d = _load_dxy_data()
    if dxy_1d is not None:
        print(f"[DXY] 1D data: {len(dxy_1d)} bars "
              f"({dxy_1d['time'].min().date()} → {dxy_1d['time'].max().date()})")
    if dxy_30 is not None:
        print(f"[DXY] 30m data: {len(dxy_30)} bars "
              f"({dxy_30['time'].min().date()} → {dxy_30['time'].max().date()})")

    for cfg in strategies:
        try:
            run_strategy(cfg, dxy_1d=dxy_1d, dxy_30=dxy_30, xauusd_1d=xauusd_1d)
        except FileNotFoundError as exc:
            print(f"[SKIP] {cfg['id']}: {exc}", file=sys.stderr)

    print(f"\nDone. HTML reports in each strategy folder.")


if __name__ == "__main__":
    main()
