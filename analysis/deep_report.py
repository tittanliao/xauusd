"""
HTML report generator for deep analysis results.
Produces a self-contained HTML file styled to match index.html.
"""
from __future__ import annotations

from datetime import datetime
import numpy as np
import pandas as pd


# ── CSS (reuses index.html variables) ───────────────────────────────────────

_CSS = """
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f0f4f8;--surface:#fff;--surface2:#f8fafc;--border:#e2e8f0;
  --nav-bg:#1e3a5f;--primary:#2563eb;--primary-light:#dbeafe;
  --green:#059669;--green-light:#d1fae5;
  --red:#dc2626;--red-light:#fee2e2;
  --yellow:#d97706;--yellow-light:#fef3c7;
  --purple:#7c3aed;--purple-light:#ede9fe;
  --text:#0f172a;--text2:#334155;--muted:#64748b;
  --radius:10px;--shadow:0 1px 4px rgba(0,0,0,.08),0 4px 16px rgba(0,0,0,.06);
}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);
     color:var(--text);font-size:14px;line-height:1.6}
.topnav{background:var(--nav-bg);padding:0 24px;display:flex;align-items:center;
        gap:12px;box-shadow:0 2px 8px rgba(0,0,0,.2)}
.nav-brand{color:white;font-weight:700;font-size:1.05em;padding:14px 0;letter-spacing:.5px}
.nav-brand span{color:#93c5fd;font-size:.8em;font-weight:400;margin-left:6px}
.nav-meta{color:rgba(255,255,255,.45);font-size:.78em;margin-left:auto}
.wrap{max-width:1200px;margin:0 auto;padding:28px 24px}
h2{font-size:1.1em;font-weight:700;color:var(--nav-bg);border-bottom:2px solid var(--primary);
   padding-bottom:6px;margin:28px 0 16px}
h3{font-size:.95em;font-weight:700;color:var(--text2);margin:20px 0 10px}
.card{background:white;border-radius:var(--radius);border:1px solid var(--border);
      padding:20px 24px;box-shadow:var(--shadow);margin-bottom:16px}
.card-title{font-size:.95em;font-weight:700;color:var(--text2);margin-bottom:14px}
.kpi-row{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:16px}
.kpi{background:var(--surface2);border:1px solid var(--border);border-radius:8px;
     padding:12px 16px;min-width:130px;flex:1}
.kpi-label{font-size:.72em;color:var(--muted);text-transform:uppercase;letter-spacing:.8px;margin-bottom:3px}
.kpi-val{font-size:1.4em;font-weight:700}
.kpi-val.green{color:var(--green)}.kpi-val.red{color:var(--red)}.kpi-val.yellow{color:var(--yellow)}
.insight{border-radius:8px;padding:12px 16px;font-size:.87em;border-left:4px solid;
         line-height:1.5;margin-bottom:10px}
.insight.good{background:var(--green-light);border-color:var(--green)}
.insight.warn{background:var(--yellow-light);border-color:var(--yellow)}
.insight.bad{background:var(--red-light);border-color:var(--red)}
.insight.info{background:var(--primary-light);border-color:var(--primary)}
.insight strong{display:block;font-weight:700;margin-bottom:3px}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
@media(max-width:900px){.grid-2,.grid-3{grid-template-columns:1fr}}
.tbl-wrap{overflow-x:auto;border-radius:8px;border:1px solid var(--border);margin-bottom:12px}
table{border-collapse:collapse;width:100%;font-size:.83em}
thead th{background:var(--nav-bg);color:white;padding:8px 12px;text-align:left;
         font-weight:600;white-space:nowrap}
tbody td{padding:7px 12px;border-bottom:1px solid #f1f5f9}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:#f8fafc}
.wr-high{background:#d1fae5;color:#065f46;font-weight:700}
.wr-mid{background:#fef3c7;color:#92400e;font-weight:700}
.wr-low{background:#fee2e2;color:#7f1d1d;font-weight:700}
.wr-na{color:var(--muted);font-size:.8em}
.part-label{display:flex;align-items:center;gap:10px;margin:28px 0 14px;
            font-size:.78em;font-weight:700;letter-spacing:1.5px;
            text-transform:uppercase;color:var(--muted)}
.part-label::after{content:'';flex:1;height:1px;background:var(--border)}
.part-badge{background:var(--primary);color:white;padding:2px 10px;
            border-radius:20px;font-size:.9em;letter-spacing:.5px}
.strategy-label{display:inline-block;padding:2px 10px;border-radius:12px;
                font-size:.78em;font-weight:700;margin-right:6px}
.lbl-s1{background:#dbeafe;color:#1e40af}
.lbl-s2a{background:#d1fae5;color:#065f46}
.lbl-s2b{background:#ede9fe;color:#5b21b6}
.footer{text-align:center;color:var(--muted);font-size:.78em;padding:32px 16px;
        margin-top:16px;border-top:1px solid var(--border)}
</style>
"""


# ── Helpers ──────────────────────────────────────────────────────────────────

def _wr_class(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "wr-na"
    if val >= 0.58:
        return "wr-high"
    if val >= 0.45:
        return "wr-mid"
    return "wr-low"


def _fmt_wr(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:.1%}"


def _simple_table(df: pd.DataFrame, cols: list[str], wr_col: str | None = None) -> str:
    if df.empty:
        return "<p style='color:var(--muted);font-size:.85em'>資料不足</p>"
    html = "<div class='tbl-wrap'><table><thead><tr>"
    header_labels = {
        "total": "總筆數", "wins": "勝", "losses": "敗",
        "win_rate": "勝率", "tb_rate": "Time-Bleed率",
        "time_bleed": "Time-Bleed", "session": "時段",
        "htf_4h_rsi_state": "4H狀態", "dxy_rsi_bucket": "DXY RSI",
        "bb_zone": "BB區間", "bb_flag": "BB位置",
        "fail_type": "失敗類型", "count": "筆數", "pct": "佔比",
    }
    # Build column list including index name
    display_cols = [df.index.name or ""] + cols
    for c in display_cols:
        html += f"<th>{header_labels.get(c, c)}</th>"
    html += "</tr></thead><tbody>"
    for idx, row in df.iterrows():
        html += "<tr>"
        html += f"<td><strong>{idx}</strong></td>"
        for c in cols:
            val = row.get(c)
            if c == wr_col or c in ("win_rate", "tb_rate"):
                try:
                    fval = float(val)
                    html += f"<td class='{_wr_class(fval)}'>{_fmt_wr(fval)}</td>"
                except (TypeError, ValueError):
                    html += f"<td class='wr-na'>—</td>"
            else:
                html += f"<td>{val if pd.notna(val) else '—'}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html


def _cross_table_html(pivot_wr: pd.DataFrame, pivot_n: pd.DataFrame, title: str) -> str:
    if pivot_wr is None or pivot_wr.empty:
        return ""
    html = f"<h3>{title}</h3>"
    html += "<div class='tbl-wrap'><table><thead><tr><th></th>"
    for col in pivot_wr.columns:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    for idx in pivot_wr.index:
        html += f"<tr><td><strong>{idx}</strong></td>"
        for col in pivot_wr.columns:
            wr = pivot_wr.loc[idx, col]
            n  = pivot_n.loc[idx, col] if pivot_n is not None else 0
            cls = _wr_class(wr)
            txt = _fmt_wr(wr) if (isinstance(wr, float) and not np.isnan(wr)) else "—"
            html += f"<td class='{cls}'>{txt}<br><span style='font-size:.75em;color:var(--muted)'>n={int(n) if n else 0}</span></td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html


def _kpi(label: str, value: str, cls: str = "") -> str:
    return f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-val {cls}'>{value}</div></div>"


def _insight(cls: str, title: str, body: str) -> str:
    return f"<div class='insight {cls}'><strong>{title}</strong>{body}</div>"


# ── Section builders ─────────────────────────────────────────────────────────

def _step1_html(trap: dict) -> str:
    hs = trap["high_bb_summary"]
    ls = trap["low_bb_summary"]
    fd = trap["fail_dist"]
    fp = trap["fail_pct"]
    fb = trap["false_breakout_stats"]
    n_imm = trap["immediate_loss_count"]
    n_fb  = trap["false_breakout_count"]
    n_loss = hs["losses"]
    n_other = n_loss - n_imm - n_fb

    body = "<div class='card'>"
    body += "<div class='card-title'>S2B 高位進場（BB%B ≥ 0.8）vs 低位進場基準比較</div>"
    body += "<div class='kpi-row'>"
    body += _kpi("高位 總筆數", str(hs["total"]))
    wr_cls = "green" if hs["win_rate"] >= 0.55 else ("yellow" if hs["win_rate"] >= 0.40 else "red")
    body += _kpi("高位 勝率", _fmt_wr(hs["win_rate"]), wr_cls)
    body += _kpi("低位 勝率", _fmt_wr(ls["win_rate"]))
    body += _kpi("高位 敗筆數", str(n_loss), "red")
    body += "</div>"

    # Fail type breakdown table for high-BB losses
    body += "<h3>高位敗筆失敗類型分解</h3>"
    if fd:
        fail_order = ["immediate_loss", "false_breakout", "time_bleed", "normal_sl"]
        body += "<div class='tbl-wrap'><table><thead><tr><th>失敗類型</th><th>筆數</th><th>佔高位敗筆%</th><th>對空單的意義</th></tr></thead><tbody>"
        meaning = {
            "immediate_loss": "✅ 空單直接獲利（進場後立即下跌）",
            "false_breakout":  "⚠️ 空單先被壓縮再獲利（先漲後跌）",
            "time_bleed":      "❓ 空單持倉時間長（橫盤後慢慢跌）",
            "normal_sl":       "🔄 正常止損（漲幅超出空單SL範圍）",
        }
        for ft in fail_order:
            if ft in fd:
                cnt = fd[ft]
                pct_str = f"{fp.get(ft, 0):.1f}%"
                body += f"<tr><td>{ft}</td><td>{cnt}</td><td>{pct_str}</td><td style='font-size:.82em'>{meaning.get(ft,'')}</td></tr>"
        body += "</tbody></table></div>"

    # False breakout MFE analysis
    if fb:
        body += "<h3>False-Breakout 的漲幅分佈（空單的逆勢風險）</h3>"
        body += "<div class='kpi-row'>"
        body += _kpi("FB 筆數", str(fb["count"]))
        body += _kpi("平均 MFE%", f"{fb['mean_mfe_pct']:.3f}%")
        body += _kpi("中位數 MFE%", f"{fb['median_mfe_pct']:.3f}%")
        body += _kpi("75百分位 MFE%", f"{fb['p75_mfe_pct']:.3f}%")
        body += _kpi("最大 MFE%", f"{fb['max_mfe_pct']:.3f}%")
        body += "</div>"
        surv_pct = fb["survivable_pct"]
        surv_cls = "good" if surv_pct >= 60 else ("warn" if surv_pct >= 40 else "bad")
        body += _insight(
            surv_cls,
            f"空單存活率（MFE < 0.5%，即不觸及空單止損）：{surv_pct:.1f}%",
            f"共 {fb['survivable_count']} / {fb['count']} 筆 false-breakout 中，"
            f"多單進入獲利後的反彈幅度不超過 0.5%（空單止損線），空單不會被掃出。"
        )

    # Overall conclusion
    if n_loss > 0:
        imm_pct = n_imm / n_loss * 100
        fb_pct  = n_fb  / n_loss * 100
        if imm_pct >= 50:
            body += _insight("good", f"結論：{imm_pct:.0f}% 為 immediate_loss —— 空單直接勝率高",
                             "高位槌頭失敗主要是進場就錯，對做空非常有利，進場時序正確。")
        elif fb_pct >= 40:
            body += _insight("warn", f"注意：{fb_pct:.0f}% 為 false_breakout —— 需注意短暫漲幅",
                             "部分失敗案例價格曾短暫上漲後逆轉，做空止損需稍留餘裕，或等下一根確認K棒。")
        else:
            body += _insight("info", "失敗模式較分散，做空邏輯需配合 4H/DXY 輔助確認。", "")

    body += "</div>"
    return body


def _checklist_section(result: dict, label_cls: str) -> str:
    sid = result["strategy_id"]
    body = f"<span class='strategy-label {label_cls}'>{sid}</span>"

    # 1D tables in grid
    tables = []
    if "by_4h_state" in result and not result["by_4h_state"].empty:
        t = f"<h3>4H RSI 狀態</h3>" + _simple_table(result["by_4h_state"], ["total", "win_rate"])
        tables.append(t)
    if "by_dxy" in result and not result["by_dxy"].empty:
        t = f"<h3>DXY RSI Bucket</h3>" + _simple_table(result["by_dxy"], ["total", "win_rate"])
        tables.append(t)
    if "by_bb_zone" in result and not result["by_bb_zone"].empty:
        t = f"<h3>BB 位置</h3>" + _simple_table(result["by_bb_zone"], ["total", "win_rate"])
        tables.append(t)

    if tables:
        body += f"<div class='grid-{min(len(tables), 3)}'>"
        for t in tables:
            body += f"<div>{t}</div>"
        body += "</div>"

    # Cross tables
    if "cross_4h_x_bb" in result:
        ct = result["cross_4h_x_bb"]
        body += _cross_table_html(ct["win_rate"], ct["counts"], "4H 狀態 × BB 位置 勝率矩陣")

    if "cross_dxy_x_4h" in result:
        ct = result["cross_dxy_x_4h"]
        body += _cross_table_html(ct["win_rate"], ct["counts"], "DXY Bucket × 4H 狀態 勝率矩陣")

    return f"<div class='card' style='margin-bottom:20px'>{body}</div>"


def _step2_html(checklists: dict[str, dict]) -> str:
    cls_map = {"S1-AweWithBB": "lbl-s1", "S2A-RSI": "lbl-s2a", "S2B-Hammer": "lbl-s2b"}
    body = ""
    for sid, result in checklists.items():
        body += _checklist_section(result, cls_map.get(sid, "lbl-s1"))
    return body


def _tb_section(result: dict, label_cls: str) -> str:
    sid   = result["strategy_id"]
    n     = result["time_bleed_count"]
    pct   = result["time_bleed_pct_of_losses"]
    pct_cls = "red" if pct >= 0.50 else ("yellow" if pct >= 0.35 else "green")

    body  = f"<div class='card' style='margin-bottom:20px'>"
    body += f"<div class='card-title'><span class='strategy-label {label_cls}'>{sid}</span>"
    body += f" Time-Bleed 佔所有敗筆：<span class='kpi-val {pct_cls}'>{pct:.1%}</span>（{n} 筆）</div>"

    tables = []
    if "by_4h_state" in result and not result["by_4h_state"].empty:
        t = "<h3>4H 狀態</h3>" + _simple_table(result["by_4h_state"], ["total", "losses", "time_bleed", "tb_rate", "win_rate"])
        tables.append(t)
    if "by_dxy" in result and not result["by_dxy"].empty:
        t = "<h3>DXY RSI Bucket</h3>" + _simple_table(result["by_dxy"], ["total", "losses", "time_bleed", "tb_rate", "win_rate"])
        tables.append(t)
    if "by_session" in result and not result["by_session"].empty:
        t = "<h3>時段</h3>" + _simple_table(result["by_session"], ["total", "losses", "time_bleed", "tb_rate", "win_rate"])
        tables.append(t)

    if tables:
        body += f"<div class='grid-{min(len(tables), 3)}'>"
        for t in tables:
            body += f"<div>{t}</div>"
        body += "</div>"

    body += "</div>"
    return body


def _step3_html(tb_results: dict[str, dict]) -> str:
    cls_map = {"S1-AweWithBB": "lbl-s1", "S2A-RSI": "lbl-s2a", "S2B-Hammer": "lbl-s2b"}
    body = ""
    for sid, result in tb_results.items():
        body += _tb_section(result, cls_map.get(sid, "lbl-s1"))
    return body


# ── Main generator ────────────────────────────────────────────────────────────

def generate(
    trap_result: dict,
    checklist_results: dict[str, dict],
    tb_results: dict[str, dict],
    out_path,
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>XAUUSD 深度分析報告</title>
{_CSS}
</head>
<body>
<nav class="topnav">
  <div class="nav-brand">XAUUSD 深度分析報告<span>Deep Analysis</span></div>
  <div class="nav-meta">Generated {now} &nbsp;|&nbsp; <a href="../index.html" style="color:#93c5fd">← 返回主頁</a></div>
</nav>
<div class="wrap">

<div class="part-label"><span class="part-badge">STEP 1</span>S2B 垂頭陷阱 失敗模式分解</div>
{_step1_html(trap_result)}

<div class="part-label"><span class="part-badge">STEP 2</span>三策略進場清單（條件 × 勝率）</div>
{_step2_html(checklist_results)}

<div class="part-label"><span class="part-badge">STEP 3</span>三策略 Time-Bleed 特徵分析</div>
{_step3_html(tb_results)}

</div>
<div class="footer">XAUUSD Strategy Analysis · {now}</div>
</body>
</html>"""

    from pathlib import Path
    Path(out_path).write_text(html, encoding="utf-8")
    print(f"  Deep analysis report → {out_path}")
