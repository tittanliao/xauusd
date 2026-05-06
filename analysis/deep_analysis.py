"""
Deep analysis: three focused analyses for actionable trading insights.

Step 1 — s2b_trap_analysis:
    S2B signal at BB%B >= 0.8: decompose fail types to validate 垂頭陷阱 short setup.
    Key question: when the long fails at high BB, is the loss immediate (good for short)
    or does price spike up first before reversing (bad for short if SL too tight)?

Step 2 — entry_checklist:
    For each strategy, cross-table of 4H state × BB flag and DXY × 4H state → win rates.
    Gives a mental checklist before pressing the button.

Step 3 — time_bleed_features:
    For each strategy, what conditions predict time_bleed losses?
    Output: per-condition time_bleed rate among losses, with win_rate context.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from analysis.bb_analysis import compute_bb, enrich_trades_with_bb
from analysis.dxy_analysis import enrich_trades_with_dxy
from analysis.fail_patterns import classify_fail, tag_session
from analysis.mtf_analysis import enrich_trades_with_htf


# ── Shared helpers ────────────────────────────────────────────────────────────

def _enrich_full(
    trades: pd.DataFrame,
    price_30m: pd.DataFrame,
    price_4h: pd.DataFrame | None,
    price_1d: pd.DataFrame | None,
    dxy_1d: pd.DataFrame | None,
) -> pd.DataFrame:
    """Enrich trades with fail_type, session, BB, 4H state, DXY."""
    classified = classify_fail(trades)
    out = trades.merge(
        classified[["trade_id", "fail_type"]], on="trade_id", how="left"
    )
    out["fail_type"] = out["fail_type"].fillna("win")
    out["session"] = tag_session(out["entry_time"])

    price_bb = compute_bb(price_30m)
    out = enrich_trades_with_bb(out, price_bb)

    if price_4h is not None and not price_4h.empty:
        out = enrich_trades_with_htf(out, price_4h=price_4h, price_1d=price_1d)

    if dxy_1d is not None:
        out = enrich_trades_with_dxy(out, dxy_1d)

    return out


def _win_rate_table(df: pd.DataFrame, col: str, min_n: int = 1) -> pd.DataFrame:
    if col not in df.columns or df.empty:
        return pd.DataFrame()
    rows = []
    for val, grp in df.groupby(col):
        total = len(grp)
        wins = int((grp["result"] == "win").sum())
        rows.append({
            col: val,
            "total": total,
            "wins": wins,
            "win_rate": round(wins / total, 3) if total >= min_n else np.nan,
        })
    return pd.DataFrame(rows).set_index(col)


def _cross_table(
    df: pd.DataFrame, row_col: str, col_col: str, min_n: int = 5
) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Win rate matrix: rows=row_col, columns=col_col. Cells with n<min_n set to NaN."""
    if df.empty or row_col not in df.columns or col_col not in df.columns:
        return None
    rows = []
    for r in sorted(df[row_col].dropna().unique()):
        for c in sorted(df[col_col].dropna().unique()):
            sub = df[(df[row_col] == r) & (df[col_col] == c)]
            total = len(sub)
            wins = int((sub["result"] == "win").sum())
            rows.append({
                row_col: r, col_col: c, "n": total,
                "win_rate": round(wins / total, 3) if total >= min_n else np.nan,
            })
    if not rows:
        return None
    frame = pd.DataFrame(rows)
    pivot_wr = frame.pivot(index=row_col, columns=col_col, values="win_rate")
    pivot_n  = frame.pivot(index=row_col, columns=col_col, values="n")
    return pivot_wr, pivot_n


# ── Step 1: S2B 垂頭陷阱 ─────────────────────────────────────────────────────

def s2b_trap_analysis(trades: pd.DataFrame, price_30m: pd.DataFrame) -> dict:
    """
    Decompose S2B trade outcomes at BB%B >= 0.8 to validate the short setup.

    Returns a dict with:
        high_bb_summary  — win/loss counts + win_rate for trades where BB%B >= 0.8
        low_bb_summary   — same for BB%B < 0.8 (baseline comparison)
        fail_dist_high   — fail-type breakdown among high-BB losses
        false_breakout   — stats on false-breakout trades: MFE distribution
                           (how much price went UP before reversing → short risk)
        short_survivable — proportion of false-breakout where mfe_pct < 0.5%
                           (short SL not hit before reversal)
    """
    price_bb = compute_bb(price_30m)
    enriched = enrich_trades_with_bb(trades, price_bb)

    high_bb = enriched[enriched["bb_pct_b"] >= 0.8].copy()
    low_bb  = enriched[enriched["bb_pct_b"] < 0.8].copy()

    def _summarize(df: pd.DataFrame) -> dict:
        if df.empty:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": np.nan}
        total = len(df)
        wins  = int((df["result"] == "win").sum())
        return {
            "total": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": round(wins / total, 3),
        }

    high_summary = _summarize(high_bb)
    low_summary  = _summarize(low_bb)

    # Classify high-BB losses by fail type
    high_losses = high_bb[high_bb["result"] == "loss"].copy()
    classified_high = classify_fail(high_losses) if len(high_losses) > 0 else pd.DataFrame()

    fail_dist: dict[str, int] = {}
    fail_pct: dict[str, float] = {}
    if len(classified_high) > 0:
        vc = classified_high["fail_type"].value_counts()
        fail_dist = vc.to_dict()
        fail_pct  = (vc / len(classified_high) * 100).round(1).to_dict()

    # false_breakout: MFE = how much price went UP before reversing
    fb = classified_high[classified_high["fail_type"] == "false_breakout"] if len(classified_high) > 0 else pd.DataFrame()
    imm = classified_high[classified_high["fail_type"] == "immediate_loss"] if len(classified_high) > 0 else pd.DataFrame()

    false_breakout_stats: dict | None = None
    if len(fb) > 0:
        # Proportion where price only went up < 0.5% before reversing
        # (short with 0.5% SL would survive and eventually win)
        survivable = int((fb["mfe_pct"] < 0.5).sum())
        false_breakout_stats = {
            "count": len(fb),
            "mean_mfe_pct":   round(fb["mfe_pct"].mean(), 3),
            "median_mfe_pct": round(fb["mfe_pct"].median(), 3),
            "p75_mfe_pct":    round(fb["mfe_pct"].quantile(0.75), 3),
            "max_mfe_pct":    round(fb["mfe_pct"].max(), 3),
            "survivable_count": survivable,
            "survivable_pct": round(survivable / len(fb) * 100, 1),
        }

    return {
        "enriched":          enriched,
        "high_bb":           high_bb,
        "low_bb":            low_bb,
        "high_bb_summary":   high_summary,
        "low_bb_summary":    low_summary,
        "fail_dist":         fail_dist,
        "fail_pct":          fail_pct,
        "classified_high":   classified_high,
        "immediate_loss_count": len(imm),
        "false_breakout_count": len(fb),
        "false_breakout_stats": false_breakout_stats,
    }


# ── Step 2: Entry checklist ──────────────────────────────────────────────────

def entry_checklist(
    trades: pd.DataFrame,
    price_30m: pd.DataFrame,
    price_4h: pd.DataFrame | None,
    price_1d: pd.DataFrame | None,
    dxy_1d: pd.DataFrame | None,
    strategy_id: str,
) -> dict:
    """
    Build win-rate tables/cross-tables for entry decision making.

    Returns:
        by_bb_zone      — win rate by BB zone
        by_4h_state     — win rate by 4H RSI state (if available)
        by_dxy          — win rate by DXY RSI bucket (if available)
        cross_4h_x_bb   — win rate matrix: 4H state × BB flag (>=0.8 vs <0.8)
        cross_dxy_x_4h  — win rate matrix: DXY bucket × 4H state
    """
    enriched = _enrich_full(trades, price_30m, price_4h, price_1d, dxy_1d)
    out: dict = {"strategy_id": strategy_id, "enriched": enriched}

    # 1D: BB zone
    out["by_bb_zone"] = _win_rate_table(
        enriched[enriched.get("bb_zone", pd.Series(dtype=str)).ne("unknown") if "bb_zone" in enriched.columns else enriched.iloc[:0]],
        "bb_zone",
    )
    if "bb_zone" in enriched.columns:
        out["by_bb_zone"] = _win_rate_table(enriched[enriched["bb_zone"] != "unknown"], "bb_zone")

    # 1D: 4H state
    if "htf_4h_rsi_state" in enriched.columns:
        valid4h = enriched[~enriched["htf_4h_rsi_state"].isin(["unknown"])]
        out["by_4h_state"] = _win_rate_table(valid4h, "htf_4h_rsi_state")

    # 1D: DXY bucket
    if "dxy_rsi_bucket" in enriched.columns:
        valid_dxy = enriched[enriched["dxy_rsi_bucket"] != "unknown"]
        out["by_dxy"] = _win_rate_table(valid_dxy, "dxy_rsi_bucket")

    # 2D: 4H state × BB flag
    if "htf_4h_rsi_state" in enriched.columns and "bb_pct_b" in enriched.columns:
        enriched = enriched.copy()
        enriched["bb_flag"] = enriched["bb_pct_b"].apply(
            lambda x: "BB>=0.8" if (pd.notna(x) and x >= 0.8) else "BB<0.8"
        )
        valid = enriched[~enriched["htf_4h_rsi_state"].isin(["unknown"])]
        result = _cross_table(valid, "htf_4h_rsi_state", "bb_flag")
        if result:
            out["cross_4h_x_bb"] = {"win_rate": result[0], "counts": result[1]}
        out["enriched"] = enriched

    # 2D: DXY × 4H state
    if "dxy_rsi_bucket" in enriched.columns and "htf_4h_rsi_state" in enriched.columns:
        valid = enriched[
            (enriched["dxy_rsi_bucket"] != "unknown") &
            (~enriched["htf_4h_rsi_state"].isin(["unknown"]))
        ]
        result = _cross_table(valid, "dxy_rsi_bucket", "htf_4h_rsi_state")
        if result:
            out["cross_dxy_x_4h"] = {"win_rate": result[0], "counts": result[1]}

    return out


# ── Step 3: Time_bleed features ──────────────────────────────────────────────

def time_bleed_features(
    trades: pd.DataFrame,
    price_30m: pd.DataFrame,
    price_4h: pd.DataFrame | None,
    price_1d: pd.DataFrame | None,
    dxy_1d: pd.DataFrame | None,
    strategy_id: str,
) -> dict:
    """
    Identify conditions that predict time_bleed losses (held too long, then stopped).

    For each grouping variable, computes:
        total, wins, losses, time_bleed count, tb_rate (among losses), win_rate
    """
    enriched = _enrich_full(trades, price_30m, price_4h, price_1d, dxy_1d)

    losses = enriched[enriched["result"] == "loss"]
    total_losses  = len(losses)
    tb_total      = int((losses["fail_type"] == "time_bleed").sum())

    out: dict = {
        "strategy_id": strategy_id,
        "total_trades": len(trades),
        "total_losses": total_losses,
        "time_bleed_count": tb_total,
        "time_bleed_pct_of_losses": round(tb_total / total_losses, 3) if total_losses else 0.0,
        "enriched": enriched,
    }

    def _tb_rate_by(col: str, filter_unknown: bool = True) -> pd.DataFrame:
        if col not in enriched.columns:
            return pd.DataFrame()
        df = enriched.copy()
        if filter_unknown:
            df = df[~df[col].isin(["unknown"])]
        rows = []
        for val, grp in df.groupby(col):
            grp_losses = grp[grp["result"] == "loss"]
            n_loss = len(grp_losses)
            n_tb   = int((grp_losses["fail_type"] == "time_bleed").sum())
            rows.append({
                col:         val,
                "total":     len(grp),
                "wins":      int((grp["result"] == "win").sum()),
                "losses":    n_loss,
                "time_bleed": n_tb,
                "tb_rate":   round(n_tb / n_loss, 3) if n_loss >= 3 else np.nan,
                "win_rate":  round((grp["result"] == "win").sum() / len(grp), 3) if grp is not None else np.nan,
            })
        return pd.DataFrame(rows).set_index(col) if rows else pd.DataFrame()

    if "htf_4h_rsi_state" in enriched.columns:
        out["by_4h_state"] = _tb_rate_by("htf_4h_rsi_state")

    if "dxy_rsi_bucket" in enriched.columns:
        out["by_dxy"] = _tb_rate_by("dxy_rsi_bucket")

    if "session" in enriched.columns:
        out["by_session"] = _tb_rate_by("session", filter_unknown=False)

    if "bb_zone" in enriched.columns:
        out["by_bb_zone"] = _tb_rate_by("bb_zone")

    return out
